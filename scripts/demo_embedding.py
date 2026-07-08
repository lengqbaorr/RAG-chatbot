from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.chunk import ChunkMetadata, ChunkingStrategy, ContentType, DocumentChunk
from app.schemas.document import DocumentType
from app.services.chunking.hashers import stable_hash
from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.embedding import (
    BGEM3EmbeddingProvider,
    EmbeddingConfig,
    EmbeddingReport,
    EmbeddingService,
    SQLiteEmbeddingCache,
)


def demo_mock() -> None:
    print("=" * 55)
    print("  [1] MOCK CHUNKS -> BGE-M3")
    print("=" * 55)

    chunks = [
        DocumentChunk(
            chunk_id=f"c{i}",
            document_id="doc1",
            source_id="s1",
            text=f"Xin chao, day la doan van mau so {i+1}. RAG chatbot giup tra loi cau hoi dua tren ngu canh.",
            chunk_index=i,
            token_count=12,
            content_hash=stable_hash(f"c{i}"),
            metadata=ChunkMetadata(
                source_id="s1",
                source_name="doc.pdf",
                source_type=DocumentType.pdf,
                chunk_index=i,
                token_count=12,
                content_hash=stable_hash(f"c{i}"),
                header_path=["Section A", f"Chapter {i+1}"],
                content_type=ContentType.body if i % 2 == 0 else ContentType.heading,
                retrieval_excluded=(i == 2),
                embedding_text_hash="",
                chunk_strategy=ChunkingStrategy.recursive_token,
            ),
        )
        for i in range(3)
    ]

    provider = BGEM3EmbeddingProvider()
    config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=provider.dimension,
        batch_size=2,
    )
    svc = EmbeddingService(
        config=config,
        provider=provider,
        cache=SQLiteEmbeddingCache(),
    )

    t0 = time.perf_counter()
    result = svc.embed_chunks(chunks)
    elapsed = time.perf_counter() - t0

    print(f"  model:    {result.report.model_name}")
    print(f"  dimension:{result.report.dimension}")
    print(f"  total:    {result.report.total_chunks}")
    print(f"  excluded: {result.report.excluded_chunks}")
    print(f"  embedded: {result.report.embedded_count}")
    print(f"  time:     {elapsed:.2f}s")
    print(f"  provider: {result.report.provider_name}")
    for ec in result.chunks:
        print(f"    {ec.chunk_id}: dim={len(ec.vector)} first=[{ec.vector[0]:.4f}, {ec.vector[1]:.4f}, {ec.vector[2]:.4f}]")


def demo_real_pdf() -> None:
    print()
    print("=" * 55)
    print("  [2] REAL PDF -> CHUNK -> BGE-M3")
    print("=" * 55)

    docs = DocumentLoaderService().load(
        LoaderInput(source="23520108_23520383_23521714.pdf")
    )
    print(f"  loaded: {len(docs)} pages")

    chunks = DocumentChunker(
        config=ChunkingConfig(chunk_size_tokens=300, chunk_overlap_tokens=40),
    ).chunk_documents(docs)
    print(f"  chunked: {len(chunks)} chunks")

    cover_count = sum(1 for c in chunks if c.metadata.content_type == ContentType.cover)
    excluded_count = sum(1 for c in chunks if c.metadata.retrieval_excluded)
    print(f"  cover: {cover_count}, retrieval_excluded: {excluded_count}")

    provider = BGEM3EmbeddingProvider()
    config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=provider.dimension,
        batch_size=16,
        skip_retrieval_excluded=True,
    )
    svc = EmbeddingService(
        config=config,
        provider=provider,
        cache=SQLiteEmbeddingCache("data/embeddings.db"),
    )

    t0 = time.perf_counter()
    result = svc.embed_chunks(chunks)
    elapsed = time.perf_counter() - t0

    print(f"\n--- REPORT ---")
    print(f"  model:       {result.report.model_name}")
    print(f"  dimension:   {result.report.dimension}")
    print(f"  total_chunks:{result.report.total_chunks}")
    print(f"  excluded:    {result.report.excluded_chunks}")
    print(f"  cache_hits:  {result.report.cache_hits}")
    print(f"  cache_misses:{result.report.cache_misses}")
    print(f"  embedded:    {result.report.embedded_count}")
    print(f"  time:        {elapsed:.2f}s  ({elapsed/max(result.report.embedded_count,1):.3f}s/chunk)")

    print(f"\n--- SAMPLE EMBEDDED CHUNKS ---")
    for ec in result.chunks[:3]:
        src = ec.metadata.source_name
        ct = ec.metadata.content_type
        vec = ec.vector
        print(f"  [{ec.chunk_id}] {ct.value:8s} | dim={len(vec)} | "
              f"first=[{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}] | {src}")

    print(f"\n  -> {len(result.chunks)} chunks ready for VectorStore")


if __name__ == "__main__":
    demo_mock()
    demo_real_pdf()
