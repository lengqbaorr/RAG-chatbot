from __future__ import annotations

from app.services.evaluation.config import EvaluationConfig, ExperimentConfig
from app.services.evaluation.evaluator import RetrievalEvaluator
from app.services.evaluation.models import EvaluationCase, ExperimentReport, ExperimentResult
from app.services.reranking.service import RerankingRetrieverAdapter


class RetrievalExperimentRunner:
    def __init__(self, *, retriever, reranker=None) -> None:
        self.retriever = retriever
        self.reranker = reranker

    def run(
        self,
        cases: list[EvaluationCase],
        configs: list[ExperimentConfig],
    ) -> ExperimentReport:
        results: list[ExperimentResult] = []
        for experiment in configs:
            retriever = self.retriever
            if experiment.use_reranker:
                if self.reranker is None:
                    raise ValueError(f"Experiment requires reranker: {experiment.name}")
                retriever = RerankingRetrieverAdapter(
                    retriever=self.retriever,
                    reranker=self.reranker,
                    rerank_top_k=experiment.rerank_top_k,
                )

            report = RetrievalEvaluator(
                retriever,
                config=EvaluationConfig(
                    recall_ks=(1, 3, 5, 10),
                    precision_k=5,
                    citation_k=5,
                    default_strategy=experiment.strategy,
                    default_top_k=experiment.top_k,
                    default_fetch_k=experiment.fetch_k,
                    default_min_score=experiment.min_score,
                    filters=experiment.filters,
                ),
                config_name=experiment.name,
            ).evaluate(cases)
            summary = report.summary
            results.append(
                ExperimentResult(
                    config_name=experiment.name,
                    recall_at_3=summary.recall_at_k.get(3, 0.0),
                    mrr=summary.mrr,
                    precision_at_5=summary.precision_at_k,
                    citation_accuracy=summary.citation_accuracy,
                    avg_latency=summary.avg_latency,
                    failed_cases=summary.failed_cases,
                )
            )
        return ExperimentReport(results=results)
