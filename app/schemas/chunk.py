from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.document import DocumentType


class UnitType(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table = "table"
    code = "code"
    ocr_block = "ocr_block"


class ContentType(StrEnum):
    body = "body"
    heading = "heading"
    table = "table"
    code = "code"
    cover = "cover"
    toc = "toc"
    reference = "reference"
    ocr = "ocr"


class ChunkingStrategy(StrEnum):
    auto = "auto"
    recursive_token = "recursive_token"
    markdown_heading = "markdown_heading"
    semantic = "semantic"
    parent_child = "parent_child"
    contextual = "contextual"


class StructuredUnit(BaseModel):
    unit_id: str
    document_id: str
    source_id: str
    text: str = Field(..., min_length=1)
    unit_type: UnitType
    unit_index: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_title: str | None = None
    header_path: list[str] = Field(default_factory=list)
    content_type: ContentType = ContentType.body

    @model_validator(mode="after")
    def validate_offsets(self) -> "StructuredUnit":
        if self.char_start is not None and self.char_end is not None:
            if self.char_end < self.char_start:
                raise ValueError("char_end must be greater than or equal to char_start")
        return self


class ChunkMetadata(BaseModel):
    source_id: str
    source_name: str
    source_type: DocumentType
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_title: str | None = None
    header_path: list[str] = Field(default_factory=list)
    chunk_index: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    content_hash: str
    parent_id: str | None = None
    child_ids: list[str] = Field(default_factory=list)
    content_type: ContentType = ContentType.body
    retrieval_excluded: bool = False
    language: str | None = None
    chunk_level: str = "child"
    embedding_text_hash: str
    parser_version: str = "structure_parser_v1"
    chunker_version: str = "recursive_token_v1"
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    chunk_strategy: ChunkingStrategy
    embedding_model: str | None = None
    embedding_version: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_ranges(self) -> "ChunkMetadata":
        if self.page_start is not None and self.page_end is not None:
            if self.page_end < self.page_start:
                raise ValueError("page_end must be greater than or equal to page_start")
        if self.char_start is not None and self.char_end is not None:
            if self.char_end < self.char_start:
                raise ValueError("char_end must be greater than or equal to char_start")
        return self


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    text: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    content_hash: str
    metadata: ChunkMetadata
