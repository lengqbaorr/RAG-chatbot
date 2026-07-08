from app.schemas.chunk import ChunkingStrategy
from app.schemas.document import Document, DocumentMetadata, DocumentType
from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.evaluation import (
    EvaluationQuestion,
    LexicalChunkRetriever,
    RetrievalEvaluator,
    RetrievedHit,
)


def _document(text: str, document_type: DocumentType = DocumentType.txt) -> Document:
    return Document(
        text=text,
        metadata=DocumentMetadata(
            document_id="doc-eval",
            document_type=document_type,
            source="memory://doc-eval",
            title="Eval Doc",
            page_number=1,
        ),
    )


def test_retrieval_evaluator_computes_core_metrics() -> None:
    questions = [
        EvaluationQuestion(question="What is RAG?", expected_pages=[2]),
        EvaluationQuestion(question="What is chunking?", expected_keywords=["chunking"]),
    ]
    results = [
        [RetrievedHit(chunk_id="a", score=1.0, page_start=2, page_end=2, text="RAG answer")],
        [RetrievedHit(chunk_id="b", score=1.0, text="chunking splits text")],
    ]

    report = RetrievalEvaluator().evaluate(questions, results, k=5)

    assert report.total_questions == 2
    assert report.recall_at_k == 1.0
    assert report.mrr == 1.0
    assert report.citation_accuracy == 0.5


def test_lexical_retriever_excludes_cover_by_default() -> None:
    documents = [
        _document("UNIVERSITY\nREPORT TITLE\nstudent name", DocumentType.pdf),
        _document("# Body\nretrieval augmented generation chunking", DocumentType.markdown),
    ]
    config = ChunkingConfig(
        strategy=ChunkingStrategy.auto,
        chunk_size_tokens=80,
        chunk_overlap_tokens=0,
    )
    chunks = DocumentChunker(config=config).chunk_documents(documents)

    hits = LexicalChunkRetriever().retrieve("REPORT TITLE retrieval", chunks, k=5)

    assert hits
    assert all("REPORT TITLE" not in hit.text for hit in hits)
