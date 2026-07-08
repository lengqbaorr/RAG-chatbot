from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.evaluation import EvaluationQuestion, LexicalChunkRetriever, RetrievalEvaluator
from app.services.ingestion import DocumentLoaderService, LoaderInput


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality on a question set.")
    parser.add_argument(
        "source",
        nargs="?",
        default="23520108_23520383_23521714.pdf",
        help="Document path or URL to evaluate.",
    )
    parser.add_argument(
        "--questions",
        default="data/evaluation/sample_questions.jsonl",
        help="JSONL file with question, expected_pages, expected_sections, expected_keywords.",
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--chunk-size", type=int, default=450)
    parser.add_argument("--chunk-overlap", type=int, default=60)
    parser.add_argument(
        "--include-excluded",
        action="store_true",
        help="Include cover/toc/reference chunks in retrieval baseline.",
    )
    return parser.parse_args()


def load_questions(path: Path) -> list[EvaluationQuestion]:
    questions: list[EvaluationQuestion] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            questions.append(EvaluationQuestion.model_validate(json.loads(stripped)))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {path}:{line_number}") from exc
    return questions


def main() -> None:
    args = parse_args()
    questions_path = Path(args.questions)
    questions = load_questions(questions_path)

    documents = DocumentLoaderService().load(LoaderInput(source=args.source))
    chunks = DocumentChunker(
        config=ChunkingConfig(
            chunk_size_tokens=args.chunk_size,
            chunk_overlap_tokens=args.chunk_overlap,
        )
    ).chunk_documents(documents)

    retriever = LexicalChunkRetriever()
    results = [
        retriever.retrieve(
            question.question,
            chunks,
            k=args.k,
            include_retrieval_excluded=args.include_excluded,
        )
        for question in questions
    ]
    report = RetrievalEvaluator().evaluate(questions, results, k=args.k)

    print(f"source: {args.source}")
    print(f"questions: {questions_path}")
    print(f"chunks: {len(chunks)}")
    print(f"k: {report.k}")
    print(f"recall_at_k: {report.recall_at_k}")
    print(f"mrr: {report.mrr}")
    print(f"citation_accuracy: {report.citation_accuracy}")
    print(f"unanswered_questions: {report.unanswered_questions}")


if __name__ == "__main__":
    main()
