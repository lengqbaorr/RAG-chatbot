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

from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.embedding import (
    BGEM3EmbeddingProvider,
    EmbeddingConfig,
    EmbeddingService,
    SQLiteEmbeddingCache,
)
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.llm import LLMConfig, LLMService
from app.services.rag import AnswerGenerator, RAGPipeline, RAGPipelineConfig
from app.services.retrieval import ParentChildRetrievalConfig, RetrievalConfig, RetrievalService
from app.services.vectorstore import ChromaVectorStore, VectorStoreConfig, VectorStoreService


DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openrouter": "qwen/qwen3-8b",
    "ollama": "qwen3:8b",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Real end-to-end RAG demo: PDF -> BGE-M3 -> Chroma -> Retriever -> LLM."
    )
    parser.add_argument("--source", default="23520108_23520383_23521714.pdf")
    parser.add_argument(
        "--query",
        default="Bông tuyết Koch được xây dựng như thế nào?",
    )
    parser.add_argument("--provider", choices=("gemini", "openrouter", "ollama"), default="gemini")
    parser.add_argument("--model", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--fetch-k", type=int, default=10)
    parser.add_argument("--min-score", type=float, default=0.78)
    parser.add_argument("--max-context-tokens", type=int, default=3000)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Load BGE-M3 from local cache only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = args.model or DEFAULT_MODELS[args.provider]

    print("=" * 72)
    print("  DEMO: Real RAG Answer Pipeline")
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
        collection_name="demo_rag_bge_m3_1024",
        persist_directory="./data/chroma_rag_demo",
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
    upsert = VectorStoreService(config=vs_config, store=store).upsert_embeddings(embedded.chunks)
    print(f"  upserted:   {upsert.upserted_count}")
    print(f"  collection: {upsert.collection_name}")

    print("\n[4] Build RAG pipeline")
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
    llm_service = LLMService(
        config=LLMConfig(
            provider=args.provider,
            model=model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    )
    pipeline = RAGPipeline(
        retriever_service=retrieval_service,
        answer_generator=AnswerGenerator(llm_service=llm_service),
        config=RAGPipelineConfig(
            retrieval_strategy="parent_child",
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            min_score=args.min_score,
        ),
    )

    print(f"\nquery:     {args.query}")
    print(f"provider:  {args.provider}")
    print(f"model:     {model}")
    print(f"min_score: {args.min_score}")

    print("\n[5] Generate answer")
    result = pipeline.answer(args.query)

    print("\nanswer:")
    print(result.answer)

    print("\nsources:")
    for source in result.sources:
        print(f"  [{source.source_number}] {source.source_name} page {source.page_start}-{source.page_end}")
        print(f"      section: {source.section_title}")
        print(f"      score:   {source.score:.4f}")

    print("\nreport:")
    print(f"  retrieval_strategy: {result.retrieval_report.strategy}")
    print(f"  retrieval_results:  {result.retrieval_report.final_results}")
    print(f"  context_sources:    {result.report.context_sources}")
    print(f"  llm:                {result.llm_provider}/{result.llm_model}")
    print(f"  llm_latency:        {result.report.llm_latency:.4f}s")
    print(f"  total_latency:      {result.latency:.4f}s")


if __name__ == "__main__":
    main()
