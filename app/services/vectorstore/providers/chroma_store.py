import json
import logging
import math
import os
import warnings

os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

import chromadb
from chromadb import PersistentClient

logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

from chromadb.telemetry.product.posthog import Posthog

_sentinel = lambda *a, **kw: None
Posthog.capture = _sentinel
Posthog._direct_capture = _sentinel

from app.services.vectorstore.filters import ChromaFilterBuilder
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreDeleteResult,
    VectorStoreStats,
    VectorStoreUpsertResult,
)

logger = logging.getLogger(__name__)


class ChromaVectorStoreError(Exception):
    pass


class ChromaVectorStore(BaseVectorStore):
    def __init__(
        self,
        collection_name: str,
        persist_directory: str = "./data/chroma",
        embedding_dimension: int = 1024,
        distance_metric: str = "cosine",
    ) -> None:
        self._collection_name = collection_name
        self._embedding_dimension = embedding_dimension
        self._distance_metric = distance_metric
        self._client: PersistentClient = chromadb.PersistentClient(
            path=persist_directory,
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": distance_metric},
        )

    @property
    def collection_name(self) -> str:
        return self._collection_name

    def upsert(self, records: list[VectorRecord]) -> VectorStoreUpsertResult:
        if not records:
            return VectorStoreUpsertResult(
                total_input=0,
                skipped_excluded=0,
                upserted_count=0,
                failed_count=0,
                collection_name=self._collection_name,
            )

        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict] = []
        documents: list[str] = []

        for rec in records:
            ids.append(rec.chunk_id)
            embeddings.append(rec.vector)
            metadatas.append(self._build_metadata(rec))
            documents.append(rec.content)

        try:
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
        except Exception as e:
            msg = f"ChromaDB upsert failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return VectorStoreUpsertResult(
            total_input=len(records),
            skipped_excluded=0,
            upserted_count=len(records),
            failed_count=0,
            collection_name=self._collection_name,
        )

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        where = ChromaFilterBuilder.build(filters)

        try:
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as e:
            msg = f"ChromaDB query failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return self._parse_query_results(results)

    def delete_by_document_id(
        self, document_id: str
    ) -> VectorStoreDeleteResult:
        where = {"document_id": {"$eq": document_id}}
        try:
            matched = self._collection.get(where=where, include=[])
            ids = matched["ids"]
            if ids:
                self._collection.delete(ids=ids)
        except Exception as e:
            msg = f"ChromaDB delete failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return VectorStoreDeleteResult(deleted_count=len(ids))

    def delete_by_source_id(
        self, source_id: str
    ) -> VectorStoreDeleteResult:
        where = {"source_id": {"$eq": source_id}}
        try:
            matched = self._collection.get(where=where, include=[])
            ids = matched["ids"]
            if ids:
                self._collection.delete(ids=ids)
        except Exception as e:
            msg = f"ChromaDB delete by source_id failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return VectorStoreDeleteResult(deleted_count=len(ids))

    def delete_by_chunk_ids(
        self, chunk_ids: list[str]
    ) -> VectorStoreDeleteResult:
        try:
            self._collection.delete(ids=chunk_ids)
        except Exception as e:
            msg = f"ChromaDB delete failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return VectorStoreDeleteResult(deleted_count=len(chunk_ids))

    def get_by_chunk_id(self, chunk_id: str) -> VectorRecord | None:
        try:
            results = self._collection.get(
                ids=[chunk_id],
                include=["metadatas", "documents", "embeddings"],
            )
        except Exception as e:
            msg = f"ChromaDB get failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        if not results["ids"]:
            return None

        return self._parse_get_result(results, 0)

    def count(self, filters: dict | None = None) -> int:
        where = ChromaFilterBuilder.build(filters)
        try:
            results = self._collection.get(where=where)
        except Exception as e:
            msg = f"ChromaDB count failed: {e}"
            logger.error(msg)
            raise ChromaVectorStoreError(msg) from e

        return len(results["ids"])

    def stats(self) -> VectorStoreStats:
        total = self._collection.count()
        return VectorStoreStats(
            total_count=total,
            collection_name=self._collection_name,
            embedding_model="",
            embedding_dimension=self._embedding_dimension,
            distance_metric=self._distance_metric,
        )

    def _build_metadata(self, rec: VectorRecord) -> dict:
        meta: dict = {
            "document_id": rec.document_id,
            "source_id": rec.source_id,
            "source_name": rec.source_name,
            "source_type": rec.source_type,
            "content_type": rec.content_type,
            "chunk_level": rec.chunk_level,
            "header_path": json.dumps(rec.header_path),
            "header_path_text": rec.header_path_text,
            "embedding_provider": rec.embedding_provider,
            "embedding_model": rec.embedding_model,
            "embedding_dimension": rec.embedding_dimension,
            "embedding_version": rec.embedding_version,
            "embedding_text_hash": rec.embedding_text_hash,
        }

        if rec.parent_id is not None:
            meta["parent_id"] = rec.parent_id
        if rec.page_start is not None:
            meta["page_start"] = rec.page_start
        if rec.page_end is not None:
            meta["page_end"] = rec.page_end
        if rec.section_title is not None:
            meta["section_title"] = rec.section_title
        if rec.child_ids:
            meta["child_ids"] = json.dumps(rec.child_ids)

        return meta

    def _parse_query_results(self, results: dict) -> list[VectorSearchResult]:
        parsed: list[VectorSearchResult] = []
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for idx, chunk_id in enumerate(ids):
            meta = metadatas[idx] if metadatas else {}
            dist = distances[idx] if distances else 0.0
            score = self._distance_to_score(dist)

            parsed.append(self._meta_to_search_result(
                chunk_id=chunk_id,
                meta=meta,
                document=documents[idx] if documents else "",
                distance=dist,
                score=score,
            ))

        return parsed

    def _parse_get_result(
        self, results: dict, index: int
    ) -> VectorRecord:
        meta = results["metadatas"][index] if results.get("metadatas") else {}
        doc = results["documents"][index] if results.get("documents") else ""
        embeddings = results.get("embeddings")
        if embeddings is not None and len(embeddings) > index:
            vec = embeddings[index]
        else:
            vec = []

        hp_raw = meta.get("header_path", "[]")
        if isinstance(hp_raw, str):
            hp = json.loads(hp_raw)
        else:
            hp = hp_raw or []

        child_ids_raw = meta.get("child_ids", "[]")
        if isinstance(child_ids_raw, str):
            child_ids = json.loads(child_ids_raw)
        else:
            child_ids = child_ids_raw or []

        return VectorRecord(
            chunk_id=results["ids"][index],
            document_id=meta.get("document_id", ""),
            source_id=meta.get("source_id", ""),
            content=doc,
            embedding_text="",
            vector=vec,
            metadata=meta,
            source_name=meta.get("source_name", ""),
            source_type=meta.get("source_type", ""),
            page_start=meta.get("page_start"),
            page_end=meta.get("page_end"),
            section_title=meta.get("section_title"),
            header_path=hp,
            header_path_text=meta.get("header_path_text", ""),
            content_type=meta.get("content_type", ""),
            chunk_level=meta.get("chunk_level", ""),
            parent_id=meta.get("parent_id"),
            child_ids=child_ids,
            embedding_provider=meta.get("embedding_provider", ""),
            embedding_model=meta.get("embedding_model", ""),
            embedding_dimension=meta.get("embedding_dimension", 0),
            embedding_version=meta.get("embedding_version", ""),
            embedding_text_hash=meta.get("embedding_text_hash", ""),
        )

    def _meta_to_search_result(
        self,
        chunk_id: str,
        meta: dict,
        document: str,
        distance: float,
        score: float,
    ) -> VectorSearchResult:
        hp_raw = meta.get("header_path", "[]")
        if isinstance(hp_raw, str):
            hp = json.loads(hp_raw)
        else:
            hp = hp_raw or []

        child_ids_raw = meta.get("child_ids", "[]")
        if isinstance(child_ids_raw, str):
            child_ids = json.loads(child_ids_raw)
        else:
            child_ids = child_ids_raw or []

        return VectorSearchResult(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            source_id=meta.get("source_id", ""),
            content=document,
            embedding_text="",
            metadata=meta,
            score=score,
            distance=distance,
            source_name=meta.get("source_name", ""),
            source_type=meta.get("source_type", ""),
            page_start=meta.get("page_start"),
            page_end=meta.get("page_end"),
            section_title=meta.get("section_title"),
            header_path=hp,
            header_path_text=meta.get("header_path_text", ""),
            content_type=meta.get("content_type", ""),
            chunk_level=meta.get("chunk_level", ""),
            parent_id=meta.get("parent_id"),
            child_ids=child_ids,
            embedding_provider=meta.get("embedding_provider", ""),
            embedding_model=meta.get("embedding_model", ""),
            embedding_dimension=meta.get("embedding_dimension", 0),
            embedding_version=meta.get("embedding_version", ""),
            embedding_text_hash=meta.get("embedding_text_hash", ""),
        )

    @staticmethod
    def _distance_to_score(distance: float) -> float:
        if distance >= 2.0:
            return 0.0
        if distance < 0.0:
            return 1.0
        return 1.0 - (distance / 2.0)
