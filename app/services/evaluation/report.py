from __future__ import annotations

import csv
import json
from io import StringIO

from app.services.evaluation.models import EvaluationReport, ExperimentReport


class EvaluationReportWriter:
    def to_json(self, report: EvaluationReport | ExperimentReport) -> str:
        return report.model_dump_json(indent=2)

    def to_markdown(self, report: EvaluationReport) -> str:
        summary = report.summary
        lines = [
            f"# Retrieval Evaluation: {report.config_name}",
            "",
            f"- total_questions: {summary.total_questions}",
            f"- answerable_questions: {summary.answerable_questions}",
            f"- unanswerable_questions: {summary.unanswerable_questions}",
            f"- mrr: {summary.mrr:.4f}",
            f"- precision@5: {summary.precision_at_k:.4f}",
            f"- citation_accuracy: {summary.citation_accuracy:.4f}",
            f"- keyword_coverage: {summary.keyword_coverage:.4f}",
            f"- avg_latency: {summary.avg_latency:.4f}s",
            "",
            "| k | recall |",
            "|---|---:|",
        ]
        for k, value in summary.recall_at_k.items():
            lines.append(f"| {k} | {value:.4f} |")
        return "\n".join(lines)

    def experiments_to_csv(self, report: ExperimentReport) -> str:
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "config_name",
                "recall_at_3",
                "mrr",
                "precision_at_5",
                "citation_accuracy",
                "avg_latency",
                "failed_cases",
            ],
        )
        writer.writeheader()
        for result in report.results:
            writer.writerow(result.model_dump())
        return output.getvalue()

    def experiments_to_markdown(self, report: ExperimentReport) -> str:
        lines = [
            "| config_name | recall@3 | mrr | precision@5 | citation_accuracy | avg_latency |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for result in report.results:
            lines.append(
                f"| {result.config_name} | {result.recall_at_3:.4f} | {result.mrr:.4f} | "
                f"{result.precision_at_5:.4f} | {result.citation_accuracy:.4f} | "
                f"{result.avg_latency:.4f}s |"
            )
        return "\n".join(lines)
