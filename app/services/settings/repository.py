from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.db import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_settings(self, *, owner: str = "local") -> dict[str, Any]:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT settings_json FROM user_settings WHERE owner = ?",
                (owner,),
            ).fetchone()
        if row is None:
            return {}
        return json.loads(row["settings_json"] or "{}")

    def save_settings(self, values: dict[str, Any], *, owner: str = "local") -> None:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_settings (owner, settings_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(owner) DO UPDATE SET
                    settings_json = excluded.settings_json,
                    updated_at = excluded.updated_at
                """,
                (owner, payload, now),
            )
