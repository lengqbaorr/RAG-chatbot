from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexingConfig:
    upload_dir: str = "./data/raw"
    max_upload_mb: int = 50
    allowed_extensions: tuple[str, ...] = (
        "pdf",
        "docx",
        "txt",
        "md",
        "png",
        "jpg",
        "jpeg",
        "bmp",
        "gif",
        "tif",
        "tiff",
        "webp",
    )
    duplicate_policy: str = "skip"


@dataclass(frozen=True)
class UploadSubmission:
    job_id: str
    source_id: str
    status: str
    duplicate: bool = False


@dataclass(frozen=True)
class IndexingReport:
    source_id: str
    source_name: str
    documents: int
    chunks: int
    embedded: int
    upserted: int
    excluded: int
    collection: str


@dataclass(frozen=True)
class IndexingTask:
    job_id: str
    source_id: str
