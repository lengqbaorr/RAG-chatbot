from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.retrieval import (
    ParentChildRetrievalConfig,
    RetrievalConfig,
    RetrievalService,
)
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreDeleteResult,
    VectorStoreStats,
    VectorStoreUpsertResult,
)


class MockEmbeddingService:
    def embed_query(self, text: str) -> list[float]:
        del text
        return [0.1, 0.2, 0.3, 0.4]


class MockVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self.records = {
            "parent-vsm": self._record(
                "parent-vsm",
                content=(
                    "Parent context: Vector Space Model biểu diễn tài liệu và truy vấn "
                    "dưới dạng vector trong không gian nhiều chiều. Độ tương đồng giữa "
                    "truy vấn và tài liệu thường được tính bằng cosine similarity."
                ),
                page_start=8,
                page_end=11,
                section_title="Vector Space Model",
            )
        }
        self.results = [
            self._result(
                "child-vsm-1",
                score=0.86,
                parent_id="parent-vsm",
                content=(
                    "Vector Space Model là mô hình biểu diễn văn bản thành vector, "
                    "trong đó mỗi chiều thường tương ứng với một thuật ngữ."
                ),
                page_start=8,
                page_end=8,
                section_title="Vector Space Model",
            ),
            self._result(
                "child-vsm-2",
                score=0.81,
                parent_id="parent-vsm",
                content="Cosine similarity được dùng để đo mức độ tương đồng giữa vector truy vấn và vector tài liệu.",
                page_start=10,
                page_end=10,
                section_title="Độ tương đồng cosine",
            ),
            self._result(
                "child-cover",
                score=0.99,
                content_type="cover",
                content="ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH",
                page_start=1,
                page_end=1,
                section_title="Trang bìa",
            ),
            self._result(
                "child-lsa",
                score=0.55,
                parent_id="parent-lsa",
                content="Latent Semantic Analysis dùng phân rã ma trận để giảm chiều và khai thác quan hệ ngữ nghĩa tiềm ẩn.",
                page_start=12,
                page_end=12,
                section_title="Latent Semantic Analysis",
            ),
        ]

    def upsert(self, records: list[VectorRecord]) -> VectorStoreUpsertResult:
        for record in records:
            self.records[record.chunk_id] = record
        return VectorStoreUpsertResult(
            total_input=len(records),
            skipped_excluded=0,
            upserted_count=len(records),
            failed_count=0,
            collection_name="mock",
        )

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        del query_vector
        results = self.results
        if filters:
            for field, value in filters.items():
                results = [result for result in results if getattr(result, field, None) == value]
        return results[:top_k]

    def delete_by_document_id(self, document_id: str) -> VectorStoreDeleteResult:
        del document_id
        return VectorStoreDeleteResult(deleted_count=0)

    def delete_by_source_id(self, source_id: str) -> VectorStoreDeleteResult:
        del source_id
        return VectorStoreDeleteResult(deleted_count=0)

    def delete_by_chunk_ids(self, chunk_ids: list[str]) -> VectorStoreDeleteResult:
        return VectorStoreDeleteResult(deleted_count=len(chunk_ids))

    def get_by_chunk_id(self, chunk_id: str) -> VectorRecord | None:
        return self.records.get(chunk_id)

    def count(self, filters: dict | None = None) -> int:
        del filters
        return len(self.records)

    def stats(self) -> VectorStoreStats:
        return VectorStoreStats(
            total_count=len(self.records),
            collection_name="mock",
            embedding_model="mock",
            embedding_dimension=4,
            distance_metric="cosine",
        )

    def _result(
        self,
        chunk_id: str,
        *,
        score: float,
        content: str,
        content_type: str = "body",
        chunk_level: str = "child",
        parent_id: str | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
        section_title: str | None = None,
    ) -> VectorSearchResult:
        return VectorSearchResult(
            chunk_id=chunk_id,
            document_id="mock-doc",
            source_id="mock-source",
            content=content,
            embedding_text="",
            metadata={"content_hash": f"hash-{chunk_id}"},
            score=score,
            distance=1.0 - score,
            source_name="mock_vector_space.pdf",
            source_type="pdf",
            page_start=page_start,
            page_end=page_end,
            section_title=section_title,
            header_path=[section_title] if section_title else [],
            header_path_text=section_title or "",
            content_type=content_type,
            chunk_level=chunk_level,
            parent_id=parent_id,
            child_ids=[],
            embedding_provider="mock",
            embedding_model="mock",
            embedding_dimension=4,
            embedding_version="v1",
            embedding_text_hash=f"eh-{chunk_id}",
        )

    def _record(
        self,
        chunk_id: str,
        *,
        content: str,
        page_start: int,
        page_end: int,
        section_title: str,
    ) -> VectorRecord:
        return VectorRecord(
            chunk_id=chunk_id,
            document_id="mock-doc",
            source_id="mock-source",
            content=content,
            embedding_text="",
            vector=[0.1, 0.2, 0.3, 0.4],
            metadata={"content_hash": f"hash-{chunk_id}"},
            source_name="mock_vector_space.pdf",
            source_type="pdf",
            page_start=page_start,
            page_end=page_end,
            section_title=section_title,
            header_path=[section_title],
            header_path_text=section_title,
            content_type="body",
            chunk_level="parent",
            child_ids=["child-vsm-1", "child-vsm-2"],
            embedding_provider="mock",
            embedding_model="mock",
            embedding_dimension=4,
            embedding_version="v1",
            embedding_text_hash=f"eh-{chunk_id}",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo Retriever Layer.")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Run real PDF -> BGE-M3 -> Chroma -> Retriever demo. Default uses mock services.",
    )
    parser.add_argument(
        "--source",
        default="Test.pdf",
        help="Document path for --real mode.",
    )
    parser.add_argument(
        "--query",
        default="Vector Space Model là gì?",
        help="Query to retrieve.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--fetch-k", type=int, default=10)
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="Minimum retrieval score. Default 0.78 filters weak cross-topic matches in this demo.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="In --real mode, load the embedding model from local cache only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.real:
        run_real_demo(args)
    else:
        run_mock_demo(args)


def run_mock_demo(args: argparse.Namespace) -> None:
    print("=" * 72)
    print("  DEMO: Retriever Layer (mock embedding + mock vector store)")
    print("=" * 72)

    service = RetrievalService(
        embedding_service=MockEmbeddingService(),
        vector_store=MockVectorStore(),
        dense_config=RetrievalConfig(
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            min_score=args.min_score,
        ),
        parent_child_config=ParentChildRetrievalConfig(
            parent_top_k=args.top_k,
            child_fetch_k=args.fetch_k,
            min_score=args.min_score,
        ),
    )

    print(f"\nquery: {args.query}")
    print(f"min_score: {args.min_score}")
    dense = service.retrieve(
        args.query,
        strategy="dense",
        top_k=args.top_k,
        fetch_k=args.fetch_k,
        filters={"chunk_level": "child"},
    )
    print_result("DenseRetriever", dense)

    parent_child = service.retrieve(
        args.query,
        strategy="parent_child",
        top_k=args.top_k,
        fetch_k=args.fetch_k,
    )
    print_result("ParentChildRetriever", parent_child)

    print("\nTip: run with --real to use BGE-M3 + ChromaDB on the sample PDF.")


def run_real_demo(args: argparse.Namespace) -> None:
    from app.services.chunking import ChunkingConfig, DocumentChunker
    from app.services.embedding import (
        BGEM3EmbeddingProvider,
        EmbeddingConfig,
        EmbeddingService,
        SQLiteEmbeddingCache,
    )
    from app.services.ingestion import DocumentLoaderService, LoaderInput
    from app.services.vectorstore import ChromaVectorStore, VectorStoreConfig, VectorStoreService

    print("=" * 72)
    print("  DEMO: Retriever Layer (PDF + BGE-M3 + ChromaDB)")
    print("=" * 72)

    print("\n[1] Load and chunk")
    docs = DocumentLoaderService().load(LoaderInput(source=args.source))
    chunks = DocumentChunker(
        config=ChunkingConfig(
            chunk_size_tokens=450,
            chunk_overlap_tokens=60,
            build_parent_chunks=True,
        )
    ).chunk_documents(docs)
    child_count = sum(1 for chunk in chunks if chunk.metadata.chunk_level == "child")
    parent_count = sum(1 for chunk in chunks if chunk.metadata.chunk_level == "parent")
    print(f"  documents: {len(docs)}")
    print(f"  chunks:    {len(chunks)} ({child_count} child, {parent_count} parent)")

    print("\n[2] Embed")
    provider = BGEM3EmbeddingProvider(local_files_only=args.local_files_only)
    embed_config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=provider.dimension,
        batch_size=16,
        skip_retrieval_excluded=True,
        cache_enabled=True,
        cache_db_path="data/embeddings.db",
    )
    embedding_service = EmbeddingService(
        config=embed_config,
        provider=provider,
        cache=SQLiteEmbeddingCache(embed_config.cache_db_path),
    )
    t0 = time.perf_counter()
    embedded = embedding_service.embed_chunks(chunks)
    print(f"  embedded: {embedded.report.embedded_count}")
    print(f"  excluded: {embedded.report.excluded_chunks}")
    print(f"  cache:    {embedded.report.cache_hits}+{embedded.report.cache_misses}")
    print(f"  time:     {time.perf_counter() - t0:.2f}s")

    print("\n[3] Upsert to ChromaDB")
    vs_config = VectorStoreConfig(
        collection_name="demo_retriever_bge_m3_1024",
        persist_directory="./data/chroma_retriever_demo",
        embedding_model="BAAI/bge-m3",
        embedding_dimension=1024,
        distance_metric="cosine",
        include_retrieval_excluded=False,
    )
    store = ChromaVectorStore(
        collection_name=vs_config.collection_name,
        persist_directory=vs_config.persist_directory,
        embedding_dimension=vs_config.embedding_dimension,
        distance_metric=vs_config.distance_metric,
    )
    vs_service = VectorStoreService(config=vs_config, store=store)
    upsert = vs_service.upsert_embeddings(embedded.chunks)
    print(f"  upserted:   {upsert.upserted_count}")
    print(f"  collection: {upsert.collection_name}")

    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=store,
        dense_config=RetrievalConfig(
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            min_score=args.min_score,
            filters={"content_type": "body", "chunk_level": "child"},
        ),
        parent_child_config=ParentChildRetrievalConfig(
            parent_top_k=args.top_k,
            child_fetch_k=args.fetch_k,
            min_score=args.min_score,
        ),
    )

    print(f"\nquery: {args.query}")
    print(f"min_score: {args.min_score}")
    dense = retrieval_service.retrieve(args.query, strategy="dense")
    print_result("DenseRetriever", dense)

    parent_child = retrieval_service.retrieve(args.query, strategy="parent_child")
    print_result("ParentChildRetriever", parent_child)

    print("\nChromaDB demo data stored at: data/chroma_retriever_demo/")


def print_result(title: str, result) -> None:
    print()
    print("-" * 72)
    print(title)
    print("-" * 72)
    report = result.report
    print("report:")
    print(f"  normalized_query:  {report.normalized_query}")
    print(f"  strategy:          {report.strategy}")
    print(f"  fetch_k/top_k:     {report.fetch_k}/{report.top_k}")
    print(f"  initial_results:   {report.initial_results}")
    print(f"  after_threshold:   {report.after_threshold}")
    print(f"  after_dedup:       {report.after_dedup}")
    print(f"  final_results:     {report.final_results}")
    print(f"  score min/max/avg: {report.min_score}/{report.max_score}/{report.avg_score}")
    print(f"  time e/v/total:    {report.embedding_time}s / {report.vector_search_time}s / {report.retrieval_time}s")

    print("chunks:")
    for chunk in result.chunks:
        print(f"  [{chunk.rank}] score={chunk.score:.4f} type={chunk.content_type}/{chunk.chunk_level}")
        print(f"      chunk_id: {chunk.chunk_id}")
        if chunk.retrieved_child is not None:
            print(f"      child:    {chunk.retrieved_child.chunk_id} score={chunk.child_score:.4f}")
        print(f"      source:   {chunk.source_name}")
        print(f"      page:     {chunk.page_start}-{chunk.page_end}")
        print(f"      section:  {chunk.header_path_text or chunk.section_title or '(none)'}")
        preview = chunk.content[:180].replace("\n", " ")
        print(f"      text:     {preview}...")


if __name__ == "__main__":
    main()

