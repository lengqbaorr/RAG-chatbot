from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from app.db import Database
from app.services.document.models import (
    ChunkRecord,
    DocumentCreate,
    DocumentRecord,
    DocumentStatus,
)


class DocumentRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_document(self, data: DocumentCreate) -> DocumentRecord:
        now = datetime.utcnow().isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    source_id, source_name, original_filename, mime_type, file_size,
                    sha256, raw_path, upload_time, status, owner
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.source_id,
                    data.source_name,
                    data.original_filename,
                    data.mime_type,
                    data.file_size,
                    data.sha256,
                    data.raw_path,
                    now,
                    data.status.value,
                    data.owner,
                ),
            )
        doc = self.get_document(data.source_id)
        if doc is None:
            raise RuntimeError("document insert failed")
        return doc

    def update_document(self, source_id: str, **fields) -> DocumentRecord | None:
        if not fields:
            return self.get_document(source_id)
        values = []
        assignments = []
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            if isinstance(value, DocumentStatus):
                value = value.value
            if isinstance(value, datetime):
                value = value.isoformat()
            values.append(value)
        values.append(source_id)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE documents SET {', '.join(assignments)} WHERE source_id = ?",
                values,
            )
        return self.get_document(source_id)

    def soft_delete_document(self, source_id: str) -> DocumentRecord | None:
        return self.update_document(
            source_id,
            status=DocumentStatus.deleted,
            deleted_at=datetime.utcnow(),
        )

    def list_documents(self, *, include_deleted: bool = False) -> list[DocumentRecord]:
        sql = "SELECT * FROM documents"
        params: tuple = ()
        if not include_deleted:
            sql += " WHERE deleted_at IS NULL"
        sql += " ORDER BY upload_time DESC"
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_document(row) for row in rows]

    def get_document(self, source_id: str) -> DocumentRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return self._row_to_document(row) if row else None

    def find_by_hash(self, sha256: str, file_size: int) -> DocumentRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM documents
                WHERE sha256 = ? AND file_size = ? AND deleted_at IS NULL
                ORDER BY upload_time DESC
                LIMIT 1
                """,
                (sha256, file_size),
            ).fetchone()
        return self._row_to_document(row) if row else None

    def find_by_filename(self, filename: str) -> list[DocumentRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM documents
                WHERE original_filename = ? AND deleted_at IS NULL
                ORDER BY upload_time DESC
                """,
                (filename,),
            ).fetchall()
        return [self._row_to_document(row) for row in rows]

    def replace_chunks(self, source_id: str, chunks: list[ChunkRecord]) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            columns = self._table_columns(conn, "chunks")
            if "content" in columns:
                conn.executemany(
                    """
                    INSERT INTO chunks (
                        chunk_id, source_id, parent_id, content, page_start, page_end,
                        section_title, header_path, token_count, retrieval_excluded, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            chunk.chunk_id,
                            chunk.source_id,
                            chunk.parent_id,
                            "",
                            chunk.page_start,
                            chunk.page_end,
                            chunk.section_title,
                            json.dumps(chunk.header_path, ensure_ascii=False),
                            chunk.token_count,
                            int(chunk.retrieval_excluded),
                            chunk.content_hash,
                        )
                        for chunk in chunks
                    ],
                )
                return

            conn.executemany(
                """
                INSERT INTO chunks (
                    chunk_id, source_id, parent_id, page_start, page_end, section_title,
                    header_path, token_count, retrieval_excluded, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.source_id,
                        chunk.parent_id,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.section_title,
                        json.dumps(chunk.header_path, ensure_ascii=False),
                        chunk.token_count,
                        int(chunk.retrieval_excluded),
                        chunk.content_hash,
                    )
                    for chunk in chunks
                ],
            )

    def delete_chunks(self, source_id: str) -> int:
        with self.db.connect() as conn:
            before = conn.total_changes
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            return conn.total_changes - before

    def list_chunks(self, source_id: str) -> list[ChunkRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE source_id = ? ORDER BY page_start, chunk_id",
                (source_id,),
            ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def completed_source_ids(self) -> list[str]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT source_id FROM documents
                WHERE status = ? AND deleted_at IS NULL
                """,
                (DocumentStatus.completed.value,),
            ).fetchall()
        return [str(row["source_id"]) for row in rows]

    def _row_to_document(self, row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            source_id=row["source_id"],
            source_name=row["source_name"],
            original_filename=row["original_filename"],
            mime_type=row["mime_type"],
            file_size=row["file_size"],
            sha256=row["sha256"],
            raw_path=row["raw_path"],
            upload_time=datetime.fromisoformat(row["upload_time"]),
            status=DocumentStatus(row["status"]),
            owner=row["owner"],
            language=row["language"],
            page_count=row["page_count"] or 0,
            chunk_count=row["chunk_count"] or 0,
            embedding_model=row["embedding_model"],
            embedding_dimension=row["embedding_dimension"],
            collection_name=row["collection_name"],
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )

    def _row_to_chunk(self, row: sqlite3.Row) -> ChunkRecord:
        header_path = json.loads(row["header_path"] or "[]")
        return ChunkRecord(
            chunk_id=row["chunk_id"],
            source_id=row["source_id"],
            parent_id=row["parent_id"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            section_title=row["section_title"],
            header_path=header_path,
            token_count=row["token_count"],
            retrieval_excluded=bool(row["retrieval_excluded"]),
            content_hash=row["content_hash"],
        )

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}
