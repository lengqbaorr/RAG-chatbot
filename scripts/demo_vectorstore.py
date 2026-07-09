from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.embedding import BGEM3EmbeddingProvider, EmbeddingConfig, EmbeddingService, SQLiteEmbeddingCache
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.vectorstore import (
    ChromaVectorStore,
    VectorStoreConfig,
    VectorStoreService,
)


def main() -> None:
    print("=" * 60)
    print("  DEMO: VectorStore Layer (ChromaDB + BGE-M3)")
    print("=" * 60)

    # ── 1. Load & chunk ──
    print("\n[1] Load PDF & chunk")
    print("-" * 40)
    docs = DocumentLoaderService().load(
        LoaderInput(source="Test.pdf")
    )
    chunks = DocumentChunker(
        config=ChunkingConfig(chunk_size_tokens=300, chunk_overlap_tokens=40),
    ).chunk_documents(docs)
    print(f"  pages:  {len(docs)}")
    print(f"  chunks: {len(chunks)}")

    # ── 2. Embed ──
    print("\n[2] Embed with BGE-M3")
    print("-" * 40)
    embed_provider = BGEM3EmbeddingProvider()
    embed_config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=embed_provider.dimension,
        batch_size=16,
        skip_retrieval_excluded=True,
        cache_enabled=True,
        cache_db_path="data/embeddings.db",
    )
    embed_svc = EmbeddingService(
        config=embed_config,
        provider=embed_provider,
        cache=SQLiteEmbeddingCache(embed_config.cache_db_path),
    )

    t0 = time.perf_counter()
    embed_result = embed_svc.embed_chunks(chunks)
    t_embed = time.perf_counter() - t0
    print(f"  embedded: {embed_result.report.embedded_count}")
    print(f"  excluded: {embed_result.report.excluded_chunks}")
    print(f"  cache:    {embed_result.report.cache_hits}+{embed_result.report.cache_misses}")
    print(f"  time:     {t_embed:.2f}s")

    # ── 3. Upsert to ChromaDB ──
    print("\n[3] Upsert to ChromaDB")
    print("-" * 40)
    vs_config = VectorStoreConfig(
        collection_name="demo_bge_m3_1024",
        persist_directory="./data/chroma",
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
    vs_svc = VectorStoreService(config=vs_config, store=store)

    t0 = time.perf_counter()
    upsert_result = vs_svc.upsert_embeddings(embed_result.chunks)
    t_upsert = time.perf_counter() - t0
    print(f"  total_input:   {upsert_result.total_input}")
    print(f"  skipped_excl:  {upsert_result.skipped_excluded}")
    print(f"  upserted:      {upsert_result.upserted_count}")
    print(f"  collection:    {upsert_result.collection_name}")
    print(f"  time:          {t_upsert:.2f}s")

    # ── 4. Stats ──
    print("\n[4] Collection stats")
    print("-" * 40)
    stats = store.stats()
    print(f"  total_count:     {stats.total_count}")
    print(f"  collection_name: {stats.collection_name}")
    print(f"  dimension:       {stats.embedding_dimension}")
    print(f"  distance_metric: {stats.distance_metric}")

    count_all = store.count()
    count_body = store.count({"content_type": "body"})
    count_heading = store.count({"content_type": "heading"})
    print(f"\n  count(all):      {count_all}")
    print(f"  count(body):     {count_body}")
    print(f"  count(heading):  {count_heading}")

    # ── 5. Search ──
    print("\n[5] Similarity search")
    print("-" * 40)
    query = "Bong tuyet Koch duoc xay dung nhu the nao?"
    print(f'  query: "{query}"')
    query_vec = embed_provider.embed_query(query)

    results = vs_svc.search(
        query_vector=query_vec,
        top_k=5,
        filters={"content_type": "body", "chunk_level": "child"},
    )
    print(f"  results: {len(results)}")
    print()
    for i, r in enumerate(results):
        print(f"  [{i+1}] score={r.score:.4f}  dist={r.distance:.4f}")
        print(f"       source: {r.source_name}")
        print(f"       section: {r.header_path_text or r.section_title or '(no section)'}")
        print(f"       page:    {r.page_start}-{r.page_end}")
        print(f"       type:    {r.content_type} / {r.chunk_level}")
        text_preview = r.content[:120].replace("\n", " ")
        print(f"       text:    {text_preview}...")
        print()

    # ── 6. Get by chunk_id ──
    print("[6] Get by chunk_id")
    print("-" * 40)
    if results:
        cid = results[0].chunk_id
        rec = store.get_by_chunk_id(cid)
        print(f"  chunk_id:  {rec.chunk_id}")
        print(f"  document:  {rec.document_id}")
        print(f"  source_id: {rec.source_id}")
        print(f"  vector:    dim={len(rec.vector)}, first 3 = {[round(v,4) for v in rec.vector[:3]]}")
        print()

    # ── 7. Delete by source_id ──
    print("[7] Cleanup: delete by source_id")
    print("-" * 40)
    if results:
        sid = results[0].source_id
        before = store.count()
        store.delete_by_source_id(sid)
        after = store.count()
        print(f"  before: {before}, after: {after}, deleted: {before - after}")

    print("\nDone.")
    print(f"\nChromaDB data stored at: data/chroma/")


if __name__ == "__main__":
    main()

