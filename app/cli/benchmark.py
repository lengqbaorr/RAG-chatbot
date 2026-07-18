from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.services.benchmark import BenchmarkConfig, load_benchmark_dataset
from app.services.benchmark.models import BenchmarkCase, BenchmarkReport
from app.services.benchmark.runner import RetrievalBenchmarkRunner


def main() -> None:
    args = _parse_args()
    if args.local_files_only:
        os.environ["EMBEDDING_LOCAL_FILES_ONLY"] = "true"
        os.environ["RERANKER_LOCAL_FILES_ONLY"] = "true"

    from app.core.config import Settings
    from app.core.startup import build_services

    config = Settings()
    app = FastAPI()
    build_services(app, config)
    try:
        cases = load_benchmark_dataset(args.dataset)
        cases = _slice_cases(cases, offset=args.offset, limit=args.limit)
        benchmark_configs = _configs_from_args(args, cases)
        runner = RetrievalBenchmarkRunner(app.state.retrieval_service)
        reports = runner.run(cases, benchmark_configs)
    finally:
        worker = getattr(app.state, "indexing_worker", None)
        if worker is not None:
            worker.stop()

    print(_format_report_table(reports))
    if args.show_failures:
        print()
        print(_format_failures(reports, limit=args.failure_limit))
    if args.output_json:
        _write_json(Path(args.output_json), reports)
    if args.output_md:
        _write_text(Path(args.output_md), _format_report_table(reports) + "\n\n" + _format_failures(reports))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retrieval benchmark against the current vector store.")
    parser.add_argument("--dataset", required=True, help="Path to .jsonl or .json benchmark dataset.")
    parser.add_argument(
        "--strategies",
        default="parent_child,dense",
        help="Comma-separated strategies to benchmark. Default: parent_child,dense",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--fetch-k", type=int, default=8)
    parser.add_argument("--min-score", type=float, default=0.76)
    parser.add_argument("--filters-json", default=None, help='Optional retrieval filters, e.g. {"source_type":"pdf"}')
    parser.add_argument("--source-name", default=None, help="Shortcut filter for one source_name, e.g. Test.pdf")
    parser.add_argument(
        "--auto-source-filter",
        action="store_true",
        help="If answerable cases use one expected_source_name, filter retrieval to that source.",
    )
    parser.add_argument(
        "--page-tolerance",
        type=int,
        default=1,
        help="Allow page labels to differ by N pages when scoring. Default: 1",
    )
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--failure-limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N dataset cases.")
    parser.add_argument("--limit", type=int, default=None, help="Run only N cases after offset.")
    parser.add_argument("--local-files-only", action="store_true", help="Force local model files only.")
    return parser.parse_args()


def _slice_cases(
    cases: list[BenchmarkCase],
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[BenchmarkCase]:
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")
    end = None if limit is None else offset + limit
    sliced = cases[offset:end]
    if not sliced:
        raise ValueError("No benchmark cases selected by offset/limit")
    return sliced


def _configs_from_args(args: argparse.Namespace, cases: list[BenchmarkCase]) -> list[BenchmarkConfig]:
    filters = json.loads(args.filters_json) if args.filters_json else None
    source_name = args.source_name
    if args.auto_source_filter and not source_name:
        source_name = _single_expected_source_name(cases)
    filters = _merge_source_filter(filters, source_name)
    strategies = [strategy.strip() for strategy in args.strategies.split(",") if strategy.strip()]
    if not strategies:
        raise ValueError("At least one strategy is required")
    return [
        BenchmarkConfig(
            strategy=strategy,
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            min_score=args.min_score,
            filters=filters,
            page_tolerance=args.page_tolerance,
        )
        for strategy in strategies
    ]


def _single_expected_source_name(cases: list[BenchmarkCase]) -> str | None:
    names = {
        case.expected_source_name
        for case in cases
        if case.answerable and case.expected_source_name
    }
    if len(names) == 1:
        return next(iter(names))
    return None


def _merge_source_filter(filters: dict | None, source_name: str | None) -> dict | None:
    if not source_name:
        return filters
    merged = dict(filters or {})
    merged.setdefault("source_name", source_name)
    return merged


def _format_report_table(reports: list[BenchmarkReport]) -> str:
    lines = [
        "| strategy | top_k | fetch_k | min_score | questions | recall@1 | recall@3 | recall@5 | mrr | precision@k | citation | keywords | unanswerable | avg_latency | failed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for report in reports:
        lines.append(
            "| "
            f"{report.config.strategy} | "
            f"{report.config.top_k} | "
            f"{report.config.fetch_k} | "
            f"{report.config.min_score:.2f} | "
            f"{report.total_questions} | "
            f"{report.recall_at_1:.4f} | "
            f"{report.recall_at_3:.4f} | "
            f"{report.recall_at_5:.4f} | "
            f"{report.mrr:.4f} | "
            f"{report.precision_at_k:.4f} | "
            f"{report.citation_accuracy:.4f} | "
            f"{report.keyword_coverage:.4f} | "
            f"{report.unanswerable_rejection:.4f} | "
            f"{report.avg_latency:.4f}s | "
            f"{len(report.failed_cases)} |"
        )
    return "\n".join(lines)


def _format_failures(reports: list[BenchmarkReport], *, limit: int | None = None) -> str:
    lines = ["## Failed Cases"]
    for report in reports:
        failures = report.failed_cases[:limit]
        lines.append("")
        lines.append(f"### {report.config.strategy}")
        if not failures:
            lines.append("No failed cases.")
            continue
        for failure in failures:
            labels = [value for value in (failure.topic, failure.group) if value]
            label_text = f" [{'/'.join(labels)}]" if labels else ""
            lines.append(
                f"- `{failure.case_id}`{label_text} {failure.failure_type}: {failure.question} "
                f"| sources={failure.retrieved_sources[:3]} "
                f"| pages={failure.retrieved_pages[:3]} "
                f"| scores={[round(score, 4) for score in failure.top_scores[:3]]}"
            )
    return "\n".join(lines)


def _write_json(path: Path, reports: list[BenchmarkReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = [report.model_dump(mode="json") for report in reports]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
