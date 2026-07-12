from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

from app.core.config import Settings
from app.services.reranking import CrossEncoderReranker, RerankerConfig


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(description="Preload the reranker model into the Hugging Face cache.")
    parser.add_argument("--model", default=settings.reranker_model)
    parser.add_argument("--device", default=settings.reranker_device)
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        default=settings.reranker_local_files_only,
    )
    parser.add_argument(
        "--clean-incomplete",
        action="store_true",
        help="Remove stale *.incomplete files for this model before downloading.",
    )
    args = parser.parse_args()

    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{args.model.replace('/', '--')}"
    if args.clean_incomplete and cache_dir.exists():
        for path in cache_dir.rglob("*.incomplete"):
            print(f"remove incomplete: {path}")
            path.unlink(missing_ok=True)

    print("=" * 72)
    print("PRELOAD RERANKER")
    print("=" * 72)
    print(f"model:            {args.model}")
    print(f"device:           {args.device}")
    print(f"local_files_only: {args.local_files_only}")

    snapshot_path = snapshot_download(
        repo_id=args.model,
        local_files_only=args.local_files_only,
        resume_download=True,
    )
    print(f"snapshot:         {snapshot_path}")

    reranker = CrossEncoderReranker(
        RerankerConfig(
            model_name=args.model,
            device=args.device,
            local_files_only=True,
        )
    )
    reranker.rerank(query="test", chunks=[], top_k=1)
    reranker._get_model()
    print("status:           loaded")


if __name__ == "__main__":
    main()
