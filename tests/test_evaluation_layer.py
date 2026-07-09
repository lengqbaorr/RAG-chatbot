from __future__ import annotations

from pathlib import Path

from app.services.evaluation.config import EvaluationConfig, ExperimentConfig
from app.services.evaluation.dataset import EvaluationDatasetLoader
from app.services.evaluation.evaluator import RetrievalEvaluator
from app.services.evaluation.metrics import (
    RelevanceMatcher,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.services.evaluation.models import EvaluationCase
from app.services.evaluation.runners import RetrievalExperimentRunner
from app.services.retrieval.models import RetrievedChunk, RetrievedContext, RetrievalReport, RetrievalResult


class FakeRetriever:
    def __init__(self, chunks_by_question: dict[str, list[RetrievedChunk]]) -> None:
        self.chunks_by_question = chunks_by_question
        self.calls: list[dict] = []

    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        self.calls.append({"query": query, **kwargs})
        chunks = self.chunks_by_question.get(query, [])
        return RetrievalResult(
            query=query,
            normalized_query=query,
            context=RetrievedContext(query=query, normalized_query=query, strategy=kwargs["strategy"], chunks=chunks),
            chunks=chunks,
            report=RetrievalReport(
                query=query,
                normalized_query=query,
                top_k=kwargs.get("top_k") or 5,
                fetch_k=kwargs.get("fetch_k") or 20,
                initial_results=len(chunks),
                after_threshold=len(chunks),
                after_dedup=len(chunks),
                final_results=len(chunks),
                min_score=min((chunk.score for chunk in chunks), default=0.0),
                max_score=max((chunk.score for chunk in chunks), default=0.0),
                avg_score=sum(chunk.score for chunk in chunks) / len(chunks) if chunks else 0.0,
                retrieval_time=0.05,
                embedding_time=0.01,
                vector_search_time=0.02,
                strategy=kwargs["strategy"],
            ),
        )


def _chunk(
    chunk_id: str,
    *,
    source_name: str = "doc.pdf",
    page_start: int = 2,
    page_end: int = 2,
    section_title: str = "2.1.2. Quy trình xây dựng",
    content: str = "chia đoạn thẳng thành ba phần và dựng tam giác đều",
    score: float = 0.9,
    rank: int = 1,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=content,
        metadata={},
        score=score,
        distance=1.0 - score,
        rank=rank,
        source_name=source_name,
        source_type="pdf",
        page_start=page_start,
        page_end=page_end,
        section_title=section_title,
        header_path=[section_title],
        header_path_text=section_title,
        content_type="body",
        chunk_level="parent",
        retrieval_strategy="parent_child",
    )


def test_load_evaluation_dataset_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "eval.jsonl"
    path.write_text(
        '{"id":"q1","question":"Koch?","expected_source_name":"doc.pdf","expected_pages":[2],"expected_keywords":["tam giác"],"answerable":true,"topic":"koch"}\n'
        '{"id":"q2","question":"Blockchain?","answerable":false}\n',
        encoding="utf-8",
    )

    dataset = EvaluationDatasetLoader().load(path)

    assert len(dataset) == 2
    assert len(dataset.answerable()) == 1
    assert dataset.group_by("topic")["koch"][0].id == "q1"


def test_relevance_matching_scores_page_section_and_keywords() -> None:
    case = EvaluationCase(
        id="q1",
        question="Koch?",
        expected_source_name="doc.pdf",
        expected_pages=[2],
        expected_section="2.1.2. Quy trình xây dựng",
        expected_keywords=["chia đoạn thẳng", "tam giác đều"],
    )

    score = RelevanceMatcher().score(case, _chunk("c1"), rank=1)

    assert score.page_match_score == 1.0
    assert score.section_match_score == 1.0
    assert score.keyword_match_score == 1.0
    assert score.is_relevant is True


def test_retrieval_metrics() -> None:
    case = EvaluationCase(
        id="q1",
        question="Koch?",
        expected_source_name="doc.pdf",
        expected_pages=[2],
    )
    scores = [
        RelevanceMatcher().score(case, _chunk("wrong", source_name="other.pdf", rank=1), rank=1),
        RelevanceMatcher().score(case, _chunk("right", rank=2), rank=2),
    ]

    assert recall_at_k(scores, 1) == 0.0
    assert recall_at_k(scores, 2) == 1.0
    assert precision_at_k(scores, 2) == 0.5
    assert reciprocal_rank(scores) == 0.5


def test_evaluator_with_mock_retriever() -> None:
    case = EvaluationCase(
        id="q1",
        question="Koch?",
        expected_source_name="doc.pdf",
        expected_pages=[2],
        expected_section="2.1.2. Quy trình xây dựng",
        expected_keywords=["tam giác đều"],
    )
    retriever = FakeRetriever({"Koch?": [_chunk("c1")]})

    report = RetrievalEvaluator(retriever, config=EvaluationConfig(recall_ks=(1, 3))).evaluate([case])

    assert report.summary.total_questions == 1
    assert report.summary.recall_at_k[1] == 1.0
    assert report.summary.mrr == 1.0
    assert report.results[0].failure_type is None


def test_unanswerable_rejection() -> None:
    case = EvaluationCase(id="q999", question="Blockchain?", answerable=False)
    retriever = FakeRetriever({"Blockchain?": [_chunk("c1", score=0.2)]})

    report = RetrievalEvaluator(
        retriever,
        config=EvaluationConfig(unanswerable_score_threshold=0.55),
    ).evaluate([case])

    assert report.summary.unanswerable_rejection == 1.0
    assert report.results[0].unanswerable_rejected is True


def test_failed_case_classification_wrong_section() -> None:
    case = EvaluationCase(
        id="q1",
        question="Koch?",
        expected_section="2.1.2. Quy trình xây dựng",
    )
    retriever = FakeRetriever({"Koch?": [_chunk("c1", section_title="2.2. Minkowski", content="irrelevant")]})

    report = RetrievalEvaluator(retriever).evaluate([case])

    assert report.results[0].failure_type == "wrong_section"


def test_experiment_runner() -> None:
    case = EvaluationCase(id="q1", question="Koch?", expected_source_name="doc.pdf", expected_pages=[2])
    retriever = FakeRetriever({"Koch?": [_chunk("c1")]})

    report = RetrievalExperimentRunner(retriever=retriever).run(
        [case],
        [
            ExperimentConfig(name="dense", strategy="dense", top_k=3),
            ExperimentConfig(name="parent", strategy="parent_child", top_k=3),
        ],
    )

    assert [result.config_name for result in report.results] == ["dense", "parent"]
    assert report.results[0].recall_at_3 == 1.0
