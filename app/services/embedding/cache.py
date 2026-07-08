import hashlib
import sqlite3
import struct
import warnings
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path


class EmbeddingCache(ABC):
    @abstractmethod
    def get(self, key: str) -> list[float] | None:
        ...

    @abstractmethod
    def set(self, key: str, vector: list[float]) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    def build_key(
        self,
        provider_name: str,
        model_name: str,
        dimension: int,
        text_hash: str,
    ) -> str:
        raw = f"{provider_name}|{model_name}|{dimension}|{text_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SQLiteEmbeddingCache(EmbeddingCache):
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            db_path = self._db_path or ":memory:"
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        return self._conn

    def get(self, key: str) -> list[float] | None:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT vector FROM embeddings WHERE cache_key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._deserialize_vector(row[0])

    def set(self, key: str, vector: list[float]) -> None:
        conn = self._get_connection()
        blob = self._serialize_vector(vector)
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (cache_key, vector, created_at) VALUES (?, ?, ?)",
            (key, blob, now),
        )
        conn.commit()

    def exists(self, key: str) -> bool:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM embeddings WHERE cache_key = ?", (key,)
        )
        return cursor.fetchone() is not None

    def clear(self) -> None:
        conn = self._get_connection()
        conn.execute("DELETE FROM embeddings")
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _serialize_vector(vector: Sequence[float]) -> bytes:
        return struct.pack(f"{len(vector)}d", *vector)

    @staticmethod
    def _deserialize_vector(data: bytes) -> list[float]:
        count = len(data) // 8
        return list(struct.unpack(f"{count}d", data))
