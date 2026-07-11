from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: str = "./data/metadata.db") -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._migrate_existing_schema(conn)

    def _migrate_existing_schema(self, conn: sqlite3.Connection) -> None:
        document_columns = self._table_columns(conn, "documents")
        document_column_defaults = {
            "raw_path": "TEXT",
            "owner": "TEXT",
            "language": "TEXT",
            "page_count": "INTEGER DEFAULT 0",
            "chunk_count": "INTEGER DEFAULT 0",
            "embedding_model": "TEXT",
            "embedding_dimension": "INTEGER",
            "collection_name": "TEXT",
            "deleted_at": "TEXT",
        }
        for column, definition in document_column_defaults.items():
            if column not in document_columns:
                conn.execute(f"ALTER TABLE documents ADD COLUMN {column} {definition}")

        chunk_columns = self._table_columns(conn, "chunks")
        chunk_column_defaults = {
            "parent_id": "TEXT",
            "page_start": "INTEGER",
            "page_end": "INTEGER",
            "section_title": "TEXT",
            "header_path": "TEXT",
            "retrieval_excluded": "INTEGER NOT NULL DEFAULT 0",
            "content_hash": "TEXT",
        }
        for column, definition in chunk_column_defaults.items():
            if column not in chunk_columns:
                conn.execute(f"ALTER TABLE chunks ADD COLUMN {column} {definition}")

        session_columns = self._table_columns(conn, "chat_sessions")
        session_column_defaults = {
            "title": "TEXT NOT NULL DEFAULT 'New chat'",
            "owner": "TEXT",
            "selected_source_ids": "TEXT NOT NULL DEFAULT '[]'",
        }
        for column, definition in session_column_defaults.items():
            if column not in session_columns:
                conn.execute(f"ALTER TABLE chat_sessions ADD COLUMN {column} {definition}")

        message_columns = self._table_columns(conn, "chat_messages")
        message_column_defaults = {
            "sources": "TEXT NOT NULL DEFAULT '[]'",
            "selected_source_ids": "TEXT NOT NULL DEFAULT '[]'",
            "status": "TEXT NOT NULL DEFAULT 'completed'",
        }
        for column, definition in message_column_defaults.items():
            if column not in message_columns:
                conn.execute(f"ALTER TABLE chat_messages ADD COLUMN {column} {definition}")

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    raw_path TEXT NOT NULL,
    upload_time TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT,
    language TEXT,
    page_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    embedding_model TEXT,
    embedding_dimension INTEGER,
    collection_name TEXT,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_hash_size ON documents(sha256, file_size);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    parent_id TEXT,
    page_start INTEGER,
    page_end INTEGER,
    section_title TEXT,
    header_path TEXT,
    token_count INTEGER NOT NULL,
    retrieval_excluded INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES documents(source_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_parent_id ON chunks(parent_id);

CREATE TABLE IF NOT EXISTS index_jobs (
    job_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    current_stage TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES documents(source_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_index_jobs_source_id ON index_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_index_jobs_status ON index_jobs(status);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    owner TEXT,
    selected_source_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources TEXT NOT NULL DEFAULT '[]',
    selected_source_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'completed',
    timestamp TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_time
ON chat_messages(session_id, timestamp);
"""
