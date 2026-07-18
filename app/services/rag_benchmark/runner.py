from __future__ import annotations

import time

from app.services.benchmark.models import BenchmarkCase
from app.services.rag.pipeline import RAGPipeline
from app.services.rag_benchmark.metrics import evaluate_rag_answer, summarize_rag_results
from app.services.rag_benchmark.models import RAGBenchmarkConfig, RAGBenchmarkReport, RAGBenchmarkResult


class RAGBenchmarkRunner:
    def __init__(self, rag_pipeline: RAGPipeline, *, stop_on_error: bool = False) -> None:
        self.rag_pipeline = rag_pipeline
        self.stop_on_error = stop_on_error

    def run(
        self,
        cases: list[BenchmarkCase],
        configs: list[RAGBenchmarkConfig],
    ) -> list[RAGBenchmarkReport]:
        reports: list[RAGBenchmarkReport] = []
        for config in configs:
            results: list[RAGBenchmarkResult] = []
            for index, case in enumerate(cases):
                try:
                    results.append(
                        evaluate_rag_answer(
                            case,
                            self.rag_pipeline.answer(
                                case.question,
                                strategy=config.strategy,
                                filters=config.filters,
                                top_k=config.top_k,
                                fetch_k=config.fetch_k,
                                min_score=config.min_score,
                                model=config.model,
                                temperature=config.temperature,
                                max_tokens=config.max_tokens,
                                reranker_enabled=config.reranker_enabled,
                                reranker_model=config.reranker_model,
                            ),
                            config=config,
                        )
                    )
                except Exception as exc:
                    if self.stop_on_error:
                        raise
                    results.append(_error_result(case, config=config, exc=exc))
                if config.request_delay_seconds > 0 and index < len(cases) - 1:
                    time.sleep(config.request_delay_seconds)
            reports.append(summarize_rag_results(results, config=config))
        return reports


def _error_result(
    case: BenchmarkCase,
    *,
    config: RAGBenchmarkConfig,
    exc: Exception,
) -> RAGBenchmarkResult:
    message = f"{type(exc).__name__}: {exc}"
    return RAGBenchmarkResult(
        case_id=case.id,
        question=case.question,
        answerable=case.answerable,
        topic=case.topic,
        group=case.group,
        strategy=config.strategy,
        answered=False,
        refused=False,
        answer_preview=message[:220],
        failure_type="llm_error",
    )
