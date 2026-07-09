from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.evaluation.config import ExperimentConfig
from app.services.evaluation.dataset import EvaluationDatasetLoader
from app.services.evaluation.report import EvaluationReportWriter
from app.services.evaluation.runners import RetrievalExperimentRunner
from app.services.reranking import BGERerankerProvider, RerankerConfig, RerankerService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrieval evaluation experiments.")
    parser.add_argument("--dataset", default="data/evaluation/retrieval_koch_10.jsonl")
    parser.add_argument("--collection", default="personal_docs_bge_m3_1024")
    parser.add_argument("--persist-directory", default="./data/chroma")
    parser.add_argument("--embedding-cache-path", default="data/embeddings.db")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--with-reranker", action="store_true")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-base")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--output", choices=("markdown", "csv", "json"), default="markdown")
    return parser.parse_args()


def build_real_retriever(
    *,
    collection: str,
    persist_directory: str,
    embedding_cache_path: str,
    no_cache: bool,
    local_files_only: bool,
):
    from app.services.embedding import (
        BGEM3EmbeddingProvider,
        EmbeddingConfig,
        EmbeddingService,
        SQLiteEmbeddingCache,
    )
    from app.services.retrieval import ParentChildRetrievalConfig, RetrievalConfig, RetrievalService
    from app.services.vectorstore import ChromaVectorStore

    provider = BGEM3EmbeddingProvider(local_files_only=local_files_only)
    embedding_config = EmbeddingConfig(
        model_name="BAAI/bge-m3",
        dimension=provider.dimension,
        cache_enabled=not no_cache,
        cache_db_path=embedding_cache_path,
    )
    embedding_service = EmbeddingService(
        config=embedding_config,
        provider=provider,
        cache=None if no_cache else SQLiteEmbeddingCache(embedding_config.cache_db_path),
    )
    store = ChromaVectorStore(
        collection_name=collection,
        persist_directory=persist_directory,
        embedding_dimension=1024,
        distance_metric="cosine",
    )
    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=store,
        dense_config=RetrievalConfig(top_k=5, fetch_k=20, min_score=0.0),
        parent_child_config=ParentChildRetrievalConfig(parent_top_k=5, child_fetch_k=20, min_score=0.0),
    )


def main() -> None:
    args = parse_args()
    dataset = EvaluationDatasetLoader().load(args.dataset)
    retriever = build_real_retriever(
        collection=args.collection,
        persist_directory=args.persist_directory,
        embedding_cache_path=args.embedding_cache_path,
        no_cache=args.no_cache,
        local_files_only=args.local_files_only,
    )
    reranker = None
    if args.with_reranker:
        reranker = RerankerService(
            reranker=BGERerankerProvider(
                RerankerConfig(
                    model_name=args.reranker_model,
                    local_files_only=args.local_files_only,
                )
            )
        )

    configs = [
        ExperimentConfig(name="dense_min_0.70_top_3", strategy="dense", top_k=3, fetch_k=20, min_score=0.70),
        ExperimentConfig(name="dense_min_0.75_top_5", strategy="dense", top_k=5, fetch_k=20, min_score=0.75),
        ExperimentConfig(name="parent_child_min_0.70_top_3", strategy="parent_child", top_k=3, fetch_k=20, min_score=0.70),
        ExperimentConfig(name="parent_child_min_0.78_top_3", strategy="parent_child", top_k=3, fetch_k=20, min_score=0.78),
    ]
    if args.with_reranker:
        configs.extend(
            [
                ExperimentConfig(
                    name="dense_rerank_20_to_5",
                    strategy="dense",
                    top_k=5,
                    fetch_k=20,
                    min_score=0.0,
                    use_reranker=True,
                    rerank_top_k=5,
                ),
                ExperimentConfig(
                    name="parent_child_rerank_20_to_5",
                    strategy="parent_child",
                    top_k=5,
                    fetch_k=20,
                    min_score=0.0,
                    use_reranker=True,
                    rerank_top_k=5,
                ),
            ]
        )

    report = RetrievalExperimentRunner(retriever=retriever, reranker=reranker).run(dataset.cases, configs)
    writer = EvaluationReportWriter()
    if args.output == "csv":
        print(writer.experiments_to_csv(report))
    elif args.output == "json":
        print(writer.to_json(report))
    else:
        print(writer.experiments_to_markdown(report))


if __name__ == "__main__":
    main()
