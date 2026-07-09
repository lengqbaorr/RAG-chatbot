from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.embedding import (
    BGEM3EmbeddingProvider,
    EmbeddingConfig,
    EmbeddingService,
    SQLiteEmbeddingCache,
)
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.vectorstore import ChromaVectorStore, VectorStoreConfig, VectorStoreService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index a document into a Chroma collection for evaluation.")
    parser.add_argument("source", nargs="?", default="Test.pdf")
    parser.add_argument("--collection", default="eval_test_pdf_bge_m3_1024")
    parser.add_argument("--persist-directory", default="./data/chroma_eval")
    parser.add_argument("--embedding-cache-path", default="data/embeddings_eval.db")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=450)
    parser.add_argument("--chunk-overlap", type=int, default=60)
    parser.add_argument("--parent-size", type=int, default=1600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    if not source.exists() and not str(args.source).startswith(("http://", "https://")):
        raise SystemExit(f"source not found: {args.source}")

    provider = BGEM3EmbeddingProvider(
        model_name="BAAI/bge-m3",
        local_files_only=args.local_files_only,
    )
    embedding_config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=provider.dimension,
        batch_size=16,
        skip_retrieval_excluded=True,
        cache_enabled=not args.no_cache,
        cache_db_path=args.embedding_cache_path,
    )
    embedding_service = EmbeddingService(
        config=embedding_config,
        provider=provider,
        cache=None if args.no_cache else SQLiteEmbeddingCache(embedding_config.cache_db_path),
    )

    vector_config = VectorStoreConfig(
        collection_name=args.collection,
        persist_directory=args.persist_directory,
        embedding_model="BAAI/bge-m3",
        embedding_dimension=1024,
        distance_metric="cosine",
        include_retrieval_excluded=False,
    )
    store = ChromaVectorStore(
        collection_name=vector_config.collection_name,
        persist_directory=vector_config.persist_directory,
        embedding_dimension=vector_config.embedding_dimension,
        distance_metric=vector_config.distance_metric,
    )
    vector_service = VectorStoreService(config=vector_config, store=store)

    docs = DocumentLoaderService().load(LoaderInput(source=args.source))
    chunks = DocumentChunker(
        config=ChunkingConfig(
            chunk_size_tokens=args.chunk_size,
            chunk_overlap_tokens=args.chunk_overlap,
            build_parent_chunks=True,
            parent_chunk_size_tokens=args.parent_size,
        )
    ).chunk_documents(docs)
    embedded = embedding_service.embed_chunks(chunks)
    upsert = vector_service.upsert_embeddings(embedded.chunks)

    child_count = sum(1 for chunk in chunks if chunk.metadata.chunk_level == "child")
    parent_count = sum(1 for chunk in chunks if chunk.metadata.chunk_level == "parent")
    print(f"source:           {args.source}")
    print(f"documents:        {len(docs)}")
    print(f"chunks:           {len(chunks)} ({child_count} child, {parent_count} parent)")
    print(f"embedded:         {embedded.report.embedded_count}")
    print(f"cache:            {embedded.report.cache_hits}+{embedded.report.cache_misses}")
    print(f"excluded:         {embedded.report.excluded_chunks}")
    print(f"upserted:         {upsert.upserted_count}")
    print(f"collection:       {upsert.collection_name}")
    print(f"persist_directory:{args.persist_directory}")
    print(f"collection_count: {store.count()}")


if __name__ == "__main__":
    main()
