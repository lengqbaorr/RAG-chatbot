from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.services.evaluation.models import EvaluationCase


class EvaluationDataset:
    def __init__(self, cases: list[EvaluationCase]) -> None:
        self.cases = cases

    def __len__(self) -> int:
        return len(self.cases)

    def answerable(self) -> list[EvaluationCase]:
        return [case for case in self.cases if case.answerable]

    def unanswerable(self) -> list[EvaluationCase]:
        return [case for case in self.cases if not case.answerable]

    def group_by(self, field_name: str) -> dict[str, list[EvaluationCase]]:
        grouped: dict[str, list[EvaluationCase]] = defaultdict(list)
        for case in self.cases:
            value = getattr(case, field_name, None) or "unknown"
            grouped[str(value)].append(case)
        return dict(grouped)


class EvaluationDatasetLoader:
    def load(self, path: str | Path) -> EvaluationDataset:
        p = Path(path)
        if p.suffix.lower() == ".jsonl":
            return EvaluationDataset(self._load_jsonl(p))
        if p.suffix.lower() == ".json":
            return EvaluationDataset(self._load_json(p))
        raise ValueError(f"Unsupported evaluation dataset format: {p.suffix}")

    def _load_jsonl(self, path: Path) -> list[EvaluationCase]:
        cases: list[EvaluationCase] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
            cases.append(EvaluationCase.model_validate(data))
        return cases

    def _load_json(self, path: Path) -> list[EvaluationCase]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("cases", [])
        if not isinstance(data, list):
            raise ValueError("JSON evaluation dataset must be a list or an object with 'cases'")
        return [EvaluationCase.model_validate(item) for item in data]
