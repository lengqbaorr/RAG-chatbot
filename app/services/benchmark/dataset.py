from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.benchmark.models import BenchmarkCase


def load_benchmark_dataset(path: str | Path) -> list[BenchmarkCase]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found: {dataset_path}")

    if dataset_path.suffix.lower() == ".jsonl":
        records = _read_jsonl(dataset_path)
    elif dataset_path.suffix.lower() == ".json":
        records = _read_json(dataset_path)
    else:
        raise ValueError("Benchmark dataset must be .jsonl or .json")

    cases = [BenchmarkCase.model_validate(record) for record in records]
    if not cases:
        raise ValueError("Benchmark dataset is empty")
    return cases


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"JSONL record must be an object at {path}:{line_number}")
        records.append(record)
    return records


def _read_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        payload = payload["cases"]
    if not isinstance(payload, list):
        raise ValueError("JSON dataset must be a list or an object with a 'cases' list")
    if not all(isinstance(record, dict) for record in payload):
        raise ValueError("Every JSON dataset case must be an object")
    return payload
