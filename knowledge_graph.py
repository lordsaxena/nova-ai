
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class KnowledgeGraph:
    """SQLite-backed knowledge graph for NOVA AI."""

    def __init__(self, db_path: str = "nova_knowledge.db"):
        self.db_path = db_path
        self._lock = threading.RLock()

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30,
        )
        self.connection.row_factory = sqlite3.Row

        with self._lock:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA busy_timeout = 30000")
            self._initialize_database()

    # ---------------------------------------------------------
    # Serialization helpers
    # ---------------------------------------------------------

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, default=str)

    @staticmethod
    def _decode(value: Any) -> Any:
        if value is None:
            return {}

        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

    @classmethod
    def _entity_dict(
        cls,
        row: sqlite3.Row | None,
    ) -> dict[str, Any] | None:
        if row is None:
            return None

        result = dict(row)

        if "metadata" in result:
            result["metadata"] = cls._decode(result["metadata"])

        return result

    # ---------------------------------------------------------
    # Database initialization and migration
    # ---------------------------------------------------------

    def _initialize_database(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'GENERAL',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(name, entity_type)
                )
                """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_entities (
                    event_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    PRIMARY KEY(event_id, entity_id),
                    FOREIGN KEY(entity_id)
                        REFERENCES entities(id) ON DELETE CASCADE
                )
                """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entity_relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    UNIQUE(source_id, target_id, relation),
                    FOREIGN KEY(source_id)
                        REFERENCES entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_id)
                        REFERENCES entities(id) ON DELETE CASCADE
                )
                """
            )

            # Preserve existing data while adding missing columns.
            event_columns = {
                row["name"]
                for row in self.connection.execute(
                    "PRAGMA table_info(event_entities)"
                ).fetchall()
            }

            if "metadata" not in event_columns:
                self.connection.execute(
                    """
                    ALTER TABLE event_entities
                    ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'
                    """
                )

            relation_columns = {
                row["name"]
                for row in self.connection.execute(
                    "PRAGMA table_info(entity_relations)"
                ).fetchall()
            }

            if "metadata" not in relation_columns:
                self.connection.execute(
                    """
                    ALTER TABLE entity_relations
                    ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'
                    """
                )

            # Remove duplicate event links before creating a unique index.
            # Keep the most recently created row for each event/entity pair.
            self.connection.execute(
                """
                DELETE FROM event_entities
                WHERE rowid NOT IN (
                    SELECT MAX(rowid)
                    FROM event_entities
                    GROUP BY event_id, entity_id
                )
                """
            )

            # Explicit indexes support older database schemas too.
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entities_name
                ON entities(name)
                """
            )

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entities_type
                ON entities(entity_type)
                """
            )

            self.connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_event_entities_unique
                ON event_entities(event_id, entity_id)
                """
            )

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_event_entities_event
                ON event_entities(event_id)
                """
            )

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_event_entities_entity
                ON event_entities(entity_id)
                """
            )

            self.connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_entity_relations_unique
                ON entity_relations(source_id, target_id, relation)
                """
            )

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relations_source
                ON entity_relations(source_id)
                """
            )

            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relations_target
                ON entity_relations(target_id)
                """
            )

    # ---------------------------------------------------------
    # Entity operations
    # ---------------------------------------------------------

    def add_entity(
        self,
        name: str,
        entity_type: str = "GENERAL",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        name = str(name).strip()
        entity_type = str(entity_type).strip().upper() or "GENERAL"

        if not name:
            raise ValueError("Entity name cannot be empty.")

        now = time.time()
        entity_id = uuid.uuid4().hex

        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO entities (
                    id, name, entity_type, metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, entity_type)
                DO UPDATE SET
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at
                """,
                (
                    entity_id,
                    name,
                    entity_type,
                    self._json(metadata),
                    now,
                    now,
                ),
            )

            row = self.connection.execute(
                """
                SELECT *
                FROM entities
                WHERE name = ? AND entity_type = ?
                """,
                (name, entity_type),
            ).fetchone()

        return self._entity_dict(row) or {}

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM entities WHERE id = ?",
                (str(entity_id),),
            ).fetchone()

        return self._entity_dict(row)

    def get_entity_by_name(
        self,
        name: str,
        entity_type: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            if entity_type:
                row = self.connection.execute(
                    """
                    SELECT *
                    FROM entities
                    WHERE name = ? AND entity_type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (str(name), str(entity_type).strip().upper()),
                ).fetchone()
            else:
                row = self.connection.execute(
                    """
                    SELECT *
                    FROM entities
                    WHERE name = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (str(name),),
                ).fetchone()

        return self._entity_dict(row)

    def get_entities(
        self,
        query: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM entities WHERE 1=1"
        params: list[Any] = []

        if query:
            sql += " AND name LIKE ?"
            params.append(f"%{str(query).strip()}%")

        if entity_type:
            sql += " AND entity_type = ?"
            params.append(str(entity_type).strip().upper())

        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(max(0, int(limit)))

        with self._lock:
            rows = self.connection.execute(sql, params).fetchall()

        return [self._entity_dict(row) or {} for row in rows]

    # ---------------------------------------------------------
    # Event/entity linking
    # ---------------------------------------------------------

    def link_event(
        self,
        event_id: str | int,
        entity_id: str,
        entity_type: str = "GENERAL",
        metadata: dict[str, Any] | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Link an event to an entity by its ID or name."""

        event_id = str(event_id)
        entity_key = str(entity_id).strip()

        if not entity_key:
            raise ValueError("Entity ID or name cannot be empty.")

        link_metadata = dict(metadata or {})

        if role is not None:
            link_metadata["role"] = role

        entity = self.get_entity(entity_key)

        if entity is None:
            entity = self.get_entity_by_name(entity_key, entity_type)

        if entity is None:
            entity = self.add_entity(
                name=entity_key,
                entity_type=entity_type,
                metadata=metadata,
            )

        resolved_entity_id = str(entity["id"])
        now = time.time()

        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE event_entities
                SET metadata = ?, created_at = ?
                WHERE event_id = ? AND entity_id = ?
                """,
                (
                    self._json(link_metadata),
                    now,
                    event_id,
                    resolved_entity_id,
                ),
            )

            if cursor.rowcount == 0:
                self.connection.execute(
                    """
                    INSERT INTO event_entities (
                        event_id, entity_id, metadata, created_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(event_id, entity_id)
                    DO UPDATE SET
                        metadata = excluded.metadata,
                        created_at = excluded.created_at
                    """,
                    (
                        event_id,
                        resolved_entity_id,
                        self._json(link_metadata),
                        now,
                    ),
                )

        return {
            "event_id": event_id,
            "entity_id": resolved_entity_id,
            "entity": entity,
            "role": role,
            "metadata": link_metadata,
        }

    def get_event_entities(
        self,
        event_id: str | int,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT
                    e.*,
                    ee.event_id,
                    ee.metadata AS link_metadata,
                    ee.created_at AS linked_at
                FROM entities e
                JOIN event_entities ee ON ee.entity_id = e.id
                WHERE ee.event_id = ?
                ORDER BY e.name
                """,
                (str(event_id),),
            ).fetchall()

        results = []

        for row in rows:
            item = self._entity_dict(row) or {}
            item["link_metadata"] = self._decode(
                item.get("link_metadata")
            )
            item["role"] = item["link_metadata"].get("role")
            results.append(item)

        return results

    def get_entity_events(
        self,
        entity_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT event_id, entity_id, metadata, created_at
                FROM event_entities
                WHERE entity_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(entity_id), max(0, int(limit))),
            ).fetchall()

        results = []

        for row in rows:
            item = dict(row)
            item["metadata"] = self._decode(item.get("metadata"))
            results.append(item)

        return results

    # ---------------------------------------------------------
    # Semantic relations
    # ---------------------------------------------------------

    def add_relation(
        self,
        source: str,
        target: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between entity IDs or entity names."""

        relation = str(relation).strip().upper()

        if not relation:
            raise ValueError("Relation type cannot be empty.")

        def resolve(value: str) -> dict[str, Any]:
            key = str(value).strip()

            if not key:
                raise ValueError("Entity name or ID cannot be empty.")

            entity = self.get_entity(key)

            if entity is None:
                entity = self.get_entity_by_name(key)

            if entity is None:
                entity = self.add_entity(key)

            return entity

        source_entity = resolve(source)
        target_entity = resolve(target)

        source_id = str(source_entity["id"])
        target_id = str(target_entity["id"])

        if source_id == target_id:
            raise ValueError("An entity cannot relate to itself.")

        relation_id = uuid.uuid4().hex
        now = time.time()

        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO entity_relations (
                    id, source_id, target_id, relation, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relation)
                DO UPDATE SET metadata = excluded.metadata
                """,
                (
                    relation_id,
                    source_id,
                    target_id,
                    relation,
                    self._json(metadata),
                    now,
                ),
            )

            row = self.connection.execute(
                """
                SELECT *
                FROM entity_relations
                WHERE source_id = ? AND target_id = ? AND relation = ?
                """,
                (source_id, target_id, relation),
            ).fetchone()

        result = dict(row) if row else {}

        if result:
            result["metadata"] = self._decode(result.get("metadata"))

        return result

    def get_relations(
        self,
        entity_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                r.*,
                s.name AS source_name,
                s.entity_type AS source_type,
                t.name AS target_name,
                t.entity_type AS target_type
            FROM entity_relations r
            JOIN entities s ON s.id = r.source_id
            JOIN entities t ON t.id = r.target_id
        """
        params: list[Any] = []

        if entity_id:
            entity = self.get_entity(entity_id)
            resolved_id = entity["id"] if entity else str(entity_id)

            sql += " WHERE r.source_id = ? OR r.target_id = ?"
            params.extend([resolved_id, resolved_id])

        sql += " ORDER BY r.created_at DESC LIMIT ?"
        params.append(max(0, int(limit)))

        with self._lock:
            rows = self.connection.execute(sql, params).fetchall()

        results = []

        for row in rows:
            item = dict(row)
            item["metadata"] = self._decode(item.get("metadata"))
            results.append(item)

        return results

    # ---------------------------------------------------------
    # Graph traversal
    # ---------------------------------------------------------

    def get_neighborhood(
        self,
        entity_id: str,
        depth: int = 1,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Return an entity and connected entities through events/relations."""

        depth = max(0, int(depth))
        limit = max(1, int(limit))

        root = self.get_entity(entity_id)

        if root is None:
            root = self.get_entity_by_name(entity_id)

        if root is None:
            return {
                "entity": None,
                "entities": [],
                "events": [],
                "relations": [],
                "depth": depth,
            }

        discovered = [root]
        visited = {root["id"]}
        frontier = {root["id"]}
        event_ids: set[str] = set()

        with self._lock:
            for _ in range(depth):
                if not frontier or len(discovered) >= limit:
                    break

                frontier_list = list(frontier)
                placeholders = ",".join("?" for _ in frontier_list)

                event_rows = self.connection.execute(
                    f"""
                    SELECT DISTINCT event_id
                    FROM event_entities
                    WHERE entity_id IN ({placeholders})
                    """,
                    frontier_list,
                ).fetchall()

                new_events = {
                    str(row["event_id"]) for row in event_rows
                }
                event_ids.update(new_events)

                next_frontier: set[str] = set()

                if new_events:
                    event_list = list(new_events)
                    event_placeholders = ",".join(
                        "?" for _ in event_list
                    )

                    neighbor_rows = self.connection.execute(
                        f"""
                        SELECT DISTINCT e.*
                        FROM entities e
                        JOIN event_entities ee ON ee.entity_id = e.id
                        WHERE ee.event_id IN ({event_placeholders})
                        """,
                        event_list,
                    ).fetchall()

                    for row in neighbor_rows:
                        item = self._entity_dict(row)

                        if item and item["id"] not in visited:
                            visited.add(item["id"])
                            next_frontier.add(item["id"])
                            discovered.append(item)

                            if len(discovered) >= limit:
                                break

                # Expand semantic relations from the current frontier.
                if len(discovered) < limit and frontier:
                    current_ids = list(frontier)
                    current_placeholders = ",".join(
                        "?" for _ in current_ids
                    )

                    relation_rows = self.connection.execute(
                        f"""
                        SELECT DISTINCT e.*
                        FROM entities e
                        JOIN entity_relations r
                          ON (
                              r.source_id IN ({current_placeholders})
                              AND r.target_id = e.id
                          )
                          OR (
                              r.target_id IN ({current_placeholders})
                              AND r.source_id = e.id
                          )
                        """,
                        current_ids + current_ids,
                    ).fetchall()

                    for row in relation_rows:
                        item = self._entity_dict(row)

                        if item and item["id"] not in visited:
                            visited.add(item["id"])
                            next_frontier.add(item["id"])
                            discovered.append(item)

                            if len(discovered) >= limit:
                                break

                frontier = next_frontier

            event_details: list[dict[str, Any]] = []

            if event_ids:
                event_list = list(event_ids)
                placeholders = ",".join("?" for _ in event_list)

                rows = self.connection.execute(
                    f"""
                    SELECT event_id, entity_id, metadata, created_at
                    FROM event_entities
                    WHERE event_id IN ({placeholders})
                    ORDER BY created_at DESC
                    """,
                    event_list,
                ).fetchall()

                for row in rows:
                    item = dict(row)
                    item["metadata"] = self._decode(item.get("metadata"))
                    event_details.append(item)

        return {
            "entity": root,
            "entities": discovered,
            "events": event_details,
            "relations": self.get_relations(root["id"], limit=limit),
            "depth": depth,
        }

    # ---------------------------------------------------------
    # Search and graph export
    # ---------------------------------------------------------

    def search_entities(
        self,
        query: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        pattern = f"%{str(query).strip()}%"

        with self._lock:
            rows = self.connection.execute(
                """
                SELECT *
                FROM entities
                WHERE name LIKE ? OR entity_type LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (pattern, pattern, max(0, int(limit))),
            ).fetchall()

        return [self._entity_dict(row) or {} for row in rows]

    def get_graph(self, limit: int = 200) -> dict[str, Any]:
        entities = self.get_entities(limit=limit)
        relations = self.get_relations(limit=limit)

        with self._lock:
            rows = self.connection.execute(
                """
                SELECT event_id, entity_id, metadata, created_at
                FROM event_entities
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()

        links = []

        for row in rows:
            item = dict(row)
            item["metadata"] = self._decode(item.get("metadata"))
            links.append(item)

        return {
            "entities": entities,
            "relations": relations,
            "event_links": links,
            "stats": self.get_stats(),
        }

    def get_stats(self) -> dict[str, int]:
        with self._lock:
            entity_count = self.connection.execute(
                "SELECT COUNT(*) FROM entities"
            ).fetchone()[0]

            link_count = self.connection.execute(
                "SELECT COUNT(*) FROM event_entities"
            ).fetchone()[0]

            event_count = self.connection.execute(
                "SELECT COUNT(DISTINCT event_id) FROM event_entities"
            ).fetchone()[0]

            relation_count = self.connection.execute(
                "SELECT COUNT(*) FROM entity_relations"
            ).fetchone()[0]

        return {
            "entities": entity_count,
            "links": link_count,
            "events": event_count,
            "relations": relation_count,
        }

    # ---------------------------------------------------------
    # Deletion and lifecycle
    # ---------------------------------------------------------

    def delete_entity(self, entity_id: str) -> bool:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                "DELETE FROM entities WHERE id = ?",
                (str(entity_id),),
            )

        return cursor.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def __enter__(self) -> "KnowledgeGraph":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()