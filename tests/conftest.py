from datetime import datetime

from app.schemas.chunk import ChunkMetadata, ChunkingStrategy, ContentType, DocumentChunk
from app.schemas.document import DocumentType
from app.services.embedding.models import EmbeddedChunk


def make_embedded_chunk(
    chunk_id: str = "c1",
    document_id: str = "doc_001",
    source_id: str = "src_test_pdf",
    text: str = "Sample content",
    source_name: str = "test.pdf",
    source_type: DocumentType = DocumentType.pdf,
    page_start: int | None = 1,
    page_end: int | None = 1,
    header_path: list[str] | None = None,
    content_type: ContentType = ContentType.body,
    chunk_level: str = "child",
    retrieval_excluded: bool = False,
    parent_id: str | None = None,
    child_ids: list[str] | None = None,
    embedding_provider: str = "bge-m3",
    embedding_model: str = "BAAI/bge-m3",
    embedding_dimension: int = 4,
    embedding_version: str = "v1",
    vector: list[float] | None = None,
) -> EmbeddedChunk:
    hp = header_path or []
    meta = ChunkMetadata(
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,
        page_start=page_start,
        page_end=page_end,
        section_title=hp[-1] if hp else None,
        header_path=hp,
        chunk_index=0,
        token_count=10,
        content_hash=f"hash_{chunk_id}",
        parent_id=parent_id,
        child_ids=child_ids or [],
        content_type=content_type,
        retrieval_excluded=retrieval_excluded,
        chunk_level=chunk_level,
        embedding_text_hash=f"emb_hash_{chunk_id}",
        chunk_strategy=ChunkingStrategy.recursive_token,
    )
    return EmbeddedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        content=text,
        embedding_text=f"Document: {source_name}\nContent:\n{text}",
        embedding_text_hash=f"emb_hash_{chunk_id}",
        vector=vector or [0.1, 0.2, 0.3, 0.4],
        metadata=meta,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        embedding_version=embedding_version,
        embedded_at=datetime.utcnow(),
    )
