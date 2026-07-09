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

from app.services.embedding import BGEM3EmbeddingProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preload and verify embedding model weights.")
    parser.add_argument("--model-name", default="BAAI/bge-m3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cache-folder", default=None)
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Only load from local cache. Use this to verify the model is already cached.",
    )
    parser.add_argument(
        "--warmup-text",
        default="Kiểm tra tải sẵn embedding model.",
        help="Short text used to run one warmup embedding.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 72)
    print("  PRELOAD: BGE-M3 embedding model")
    print("=" * 72)
    print(f"model:            {args.model_name}")
    print(f"device:           {args.device}")
    print(f"cache_folder:     {args.cache_folder or '(sentence-transformers default)'}")
    print(f"local_files_only: {args.local_files_only}")

    provider = BGEM3EmbeddingProvider(
        model_name=args.model_name,
        device=args.device,
        cache_folder=args.cache_folder,
        local_files_only=args.local_files_only,
    )

    t0 = time.perf_counter()
    dimension = provider.preload()
    load_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    vector = provider.embed_query(args.warmup_text)
    warmup_time = time.perf_counter() - t1

    print()
    print("status:           ok")
    print(f"dimension:        {dimension}")
    print(f"vector_length:    {len(vector)}")
    print(f"load_time:        {load_time:.2f}s")
    print(f"warmup_time:      {warmup_time:.2f}s")


if __name__ == "__main__":
    main()
