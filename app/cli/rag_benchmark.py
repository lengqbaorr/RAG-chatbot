from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.services.benchmark import BenchmarkCase, load_benchmark_dataset
from app.services.rag_benchmark import RAGBenchmarkConfig, RAGBenchmarkReport, RAGBenchmarkRunner


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
        runner = RAGBenchmarkRunner(app.state.rag_pipeline, stop_on_error=args.stop_on_error)
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
    parser = argparse.ArgumentParser(description="Run end-to-end RAG answer benchmark.")
    parser.add_argument("--dataset", required=True, help="Path to .jsonl or .json benchmark dataset.")
    parser.add_argument("--strategies", default="parent_child", help="Comma-separated strategies. Default: parent_child")
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
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--reranker-enabled", action="store_true")
    parser.add_argument("--reranker-model", default=None)
    parser.add_argument("--min-answer-keyword-coverage", type=float, default=0.5)
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=13.0,
        help="Delay between LLM requests. Default 13s is safe for Gemini free tier 5 RPM.",
    )
    parser.add_argument("--stop-on-error", action="store_true", help="Raise on first LLM error instead of recording it.")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N dataset cases.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--failure-limit", type=int, default=20)
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


def _configs_from_args(args: argparse.Namespace, cases: list[BenchmarkCase]) -> list[RAGBenchmarkConfig]:
    filters = json.loads(args.filters_json) if args.filters_json else None
    source_name = args.source_name
    if args.auto_source_filter and not source_name:
        source_name = _single_expected_source_name(cases)
    filters = _merge_source_filter(filters, source_name)
    strategies = [strategy.strip() for strategy in args.strategies.split(",") if strategy.strip()]
    if not strategies:
        raise ValueError("At least one strategy is required")
    return [
        RAGBenchmarkConfig(
            strategy=strategy,
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            min_score=args.min_score,
            filters=filters,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            reranker_enabled=args.reranker_enabled,
            reranker_model=args.reranker_model,
            min_answer_keyword_coverage=args.min_answer_keyword_coverage,
            request_delay_seconds=args.request_delay_seconds,
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


def _format_report_table(reports: list[RAGBenchmarkReport]) -> str:
    lines = [
        "| strategy | top_k | fetch_k | min_score | questions | answer_acc | answer_keywords | citation | source_hit | unanswerable | retrieval_latency | llm_latency | total_latency | failed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for report in reports:
        lines.append(
            "| "
            f"{report.config.strategy} | "
            f"{report.config.top_k} | "
            f"{report.config.fetch_k} | "
            f"{report.config.min_score:.2f} | "
            f"{report.total_questions} | "
            f"{report.answer_accuracy:.4f} | "
            f"{report.answer_keyword_coverage:.4f} | "
            f"{report.citation_accuracy:.4f} | "
            f"{report.source_hit_rate:.4f} | "
            f"{report.unanswerable_rejection:.4f} | "
            f"{report.avg_retrieval_latency:.4f}s | "
            f"{report.avg_llm_latency:.4f}s | "
            f"{report.avg_total_latency:.4f}s | "
            f"{len(report.failed_cases)} |"
        )
    return "\n".join(lines)


def _format_failures(reports: list[RAGBenchmarkReport], *, limit: int | None = None) -> str:
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
                f"| keywords={failure.answer_keyword_coverage:.2f} "
                f"| sources={failure.source_names[:3]} "
                f"| pages={failure.source_pages[:3]} "
                f"| answer={failure.answer_preview!r}"
            )
    return "\n".join(lines)


def _write_json(path: Path, reports: list[RAGBenchmarkReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = [report.model_dump(mode="json") for report in reports]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
