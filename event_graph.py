from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class EventGraph:
    def __init__(self, db_path: str = "data/nova_trace.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            self.db_path, check_same_thread=False, timeout=30
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._db:
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    UNIQUE(source_id, target_id, relation)
                );

                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_type
                    ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_rel_source
                    ON event_relations(source_id);
                CREATE INDEX IF NOT EXISTS idx_rel_target
                    ON event_relations(target_id);
            """)

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, default=str, ensure_ascii=False)

    @staticmethod
    def _decode(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result

    def add_event(self, event: dict) -> dict:
        """Persist an event and return its stored representation."""
        if not isinstance(event, dict):
            raise TypeError("event must be a dictionary")

        stored = dict(event)
        stored.setdefault("id", uuid.uuid4().hex)
        stored.setdefault("event_type", "UNKNOWN")
        stored.setdefault("source", "UNKNOWN")
        stored.setdefault("timestamp", time.time())

        event_id = str(stored["id"])
        stored["id"] = event_id

        with self._lock, self._db:
            existing = self._db.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            ).fetchone()

            if existing:
                existing_event = self._decode(existing)
                if existing_event["payload"] != stored:
                    raise ValueError(
                        f"Event ID {event_id!r} already exists with "
                        "different content."
                    )
                return existing_event

            self._db.execute(
                """
                INSERT INTO events
                    (id, event_type, source, timestamp, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    str(stored["event_type"]),
                    str(stored["source"]),
                    float(stored["timestamp"]),
                    self._json(stored),
                ),
            )

        return stored

    def get_event(self, event_id: str | int) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM events WHERE id = ?", (str(event_id),)
            ).fetchone()
        return self._decode(row)

    def get_events(
        self,
        limit: int = 100,
        event_type: str | None = None,
        source: str | None = None,
        before: float | None = None,
    ) -> list[dict]:
        limit = max(1, min(int(limit), 5000))
        query = "SELECT * FROM events WHERE 1=1"
        params: list[Any] = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source:
            query += " AND source = ?"
            params.append(source)
        if before is not None:
            query += " AND timestamp < ?"
            params.append(float(before))

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._db.execute(query, params).fetchall()

        return [self._decode(row) for row in rows]

    def add_relation(
        self,
        source_id: str | int,
        target_id: str | int,
        relation: str = "FOLLOWED_BY",
        metadata: dict | None = None,
    ) -> dict:
        source_id, target_id = str(source_id), str(target_id)
        if source_id == target_id:
            raise ValueError("An event cannot relate to itself.")

        with self._lock, self._db:
            for event_id in (source_id, target_id):
                exists = self._db.execute(
                    "SELECT 1 FROM events WHERE id = ?", (event_id,)
                ).fetchone()
                if not exists:
                    raise ValueError(f"Event {event_id!r} does not exist.")

            self._db.execute(
                """
                INSERT INTO event_relations
                    (source_id, target_id, relation, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation)
                DO UPDATE SET metadata = excluded.metadata
                """,
                (
                    source_id,
                    target_id,
                    relation,
                    self._json(metadata or {}),
                    time.time(),
                ),
            )

            row = self._db.execute(
                """
                SELECT * FROM event_relations
                WHERE source_id = ? AND target_id = ? AND relation = ?
                """,
                (source_id, target_id, relation),
            ).fetchone()

        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def get_relations(
        self, event_id: str | int | None = None, limit: int = 500
    ) -> list[dict]:
        limit = max(1, min(int(limit), 5000))
        query = "SELECT * FROM event_relations"
        params: list[Any] = []

        if event_id is not None:
            query += " WHERE source_id = ? OR target_id = ?"
            params.extend([str(event_id), str(event_id)])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._db.execute(query, params).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item["metadata"])
            result.append(item)
        return result

    def get_related_events(
        self, event_id: str | int, limit: int = 100
    ) -> list[dict]:
        event_id = str(event_id)
        limit = max(1, min(int(limit), 1000))

        with self._lock:
            rows = self._db.execute(
                """
                SELECT e.*
                FROM events e
                JOIN event_relations r
                  ON e.id = r.target_id OR e.id = r.source_id
                WHERE (r.source_id = ? OR r.target_id = ?)
                  AND e.id != ?
                ORDER BY e.timestamp DESC
                LIMIT ?
                """,
                (event_id, event_id, event_id, limit),
            ).fetchall()

        return [self._decode(row) for row in rows]

    def get_causal_chain(
        self, event_id: str | int, max_depth: int = 20
    ) -> list[dict]:
        """Walk backwards through TRIGGERED relations."""
        current = str(event_id)
        visited: set[str] = set()
        chain: list[dict] = []
        max_depth = max(1, min(int(max_depth), 100))

        with self._lock:
            for _ in range(max_depth):
                if current in visited:
                    break
                visited.add(current)

                row = self._db.execute(
                    "SELECT * FROM events WHERE id = ?", (current,)
                ).fetchone()
                if row is None:
                    break

                event = self._decode(row)
                chain.append(event)

                relation = self._db.execute(
                    """
                    SELECT source_id FROM event_relations
                    WHERE target_id = ? AND relation = 'TRIGGERED'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (current,),
                ).fetchone()

                if relation is None:
                    break
                current = relation["source_id"]

        return chain

    def get_graph(self, limit: int = 200) -> dict:
        events = self.get_events(limit=limit)
        ids = {event["id"] for event in events}
        relations = self.get_relations(limit=min(limit * 5, 5000))
        edges = [
            edge for edge in relations
            if edge["source_id"] in ids and edge["target_id"] in ids
        ]
        return {"nodes": events, "edges": edges}

    def count(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) AS total FROM events"
            ).fetchone()
        return int(row["total"])

    def close(self) -> None:
        with self._lock:
            self._db.close()