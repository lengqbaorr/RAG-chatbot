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

from app.services.reranking import BGERerankerProvider, RerankerConfig
from app.services.retrieval.models import RetrievedChunk


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preload and verify BGE reranker weights.")
    parser.add_argument("--model-name", default="BAAI/bge-reranker-base")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cache-folder", default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--query", default="Bông tuyết Koch được xây dựng như thế nào?")
    parser.add_argument(
        "--text",
        default="Bông tuyết Koch được xây dựng bằng cách chia đoạn thẳng thành ba phần và dựng tam giác đều.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("=" * 72)
    print("  PRELOAD: BGE reranker model")
    print("=" * 72)
    print(f"model:            {args.model_name}")
    print(f"device:           {args.device}")
    print(f"cache_folder:     {args.cache_folder or '(sentence-transformers default)'}")
    print(f"local_files_only: {args.local_files_only}")

    provider = BGERerankerProvider(
        RerankerConfig(
            model_name=args.model_name,
            device=args.device,
            cache_folder=args.cache_folder,
            local_files_only=args.local_files_only,
        )
    )

    t0 = time.perf_counter()
    model_name = provider.preload()
    load_time = time.perf_counter() - t0

    chunk = RetrievedChunk(
        chunk_id="warmup",
        document_id="warmup-doc",
        source_id="warmup-source",
        content=args.text,
        metadata={},
        score=0.0,
        distance=1.0,
        rank=1,
        source_name="warmup.txt",
        source_type="txt",
        content_type="body",
        chunk_level="child",
        retrieval_strategy="warmup",
    )
    t1 = time.perf_counter()
    result = provider.rerank(args.query, [chunk], top_k=1)
    warmup_time = time.perf_counter() - t1

    print()
    print("status:           ok")
    print(f"loaded_model:     {model_name}")
    print(f"warmup_score:     {result[0].rerank_score:.4f}")
    print(f"load_time:        {load_time:.2f}s")
    print(f"warmup_time:      {warmup_time:.2f}s")


if __name__ == "__main__":
    main()
