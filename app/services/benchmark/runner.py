from __future__ import annotations

from app.services.benchmark.metrics import evaluate_retrieval_case, summarize_results
from app.services.benchmark.models import BenchmarkCase, BenchmarkConfig, BenchmarkReport
from app.services.retrieval.service import RetrievalService


class RetrievalBenchmarkRunner:
    def __init__(self, retrieval_service: RetrievalService) -> None:
        self.retrieval_service = retrieval_service

    def run(
        self,
        cases: list[BenchmarkCase],
        configs: list[BenchmarkConfig],
    ) -> list[BenchmarkReport]:
        reports: list[BenchmarkReport] = []
        for config in configs:
            results = [
                evaluate_retrieval_case(
                    case,
                    self.retrieval_service.retrieve(
                        case.question,
                        strategy=config.strategy,
                        filters=config.filters,
                        top_k=config.top_k,
                        fetch_k=config.fetch_k,
                        min_score=config.min_score,
                    ),
                    config=config,
                )
                for case in cases
            ]
            reports.append(summarize_results(results, config=config))
        return reports
