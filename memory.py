"""
SQLite dedup memory for papers already seen/delivered.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_papers (
    arxiv_id   TEXT PRIMARY KEY,
    seen_at    TEXT NOT NULL,
    score      INTEGER,
    delivered  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_seen_at ON seen_papers(seen_at);
"""


class Memory:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def is_seen(self, arxiv_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM seen_papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
        return row is not None

    def filter_new(self, arxiv_ids: list[str]) -> set[str]:
        if not arxiv_ids:
            return set()
        with self._conn() as c:
            qmarks = ",".join("?" * len(arxiv_ids))
            seen = {
                r[0]
                for r in c.execute(
                    f"SELECT arxiv_id FROM seen_papers WHERE arxiv_id IN ({qmarks})",
                    arxiv_ids,
                )
            }
        return set(arxiv_ids) - seen

    def mark(self, arxiv_id: str, score: int | None, delivered: bool) -> None:
        from datetime import datetime, timezone
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO seen_papers (arxiv_id, seen_at, score, delivered)
                   VALUES (?, ?, ?, ?)""",
                (arxiv_id, datetime.now(timezone.utc).isoformat(), score, int(delivered)),
            )
