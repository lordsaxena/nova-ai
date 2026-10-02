import sqlite3
import threading
import json
from datetime import datetime


class EventGraph:

    def __init__(self, database="nova_memory.db"):

        self.database = database

        self.lock = threading.Lock()

        self.connection = sqlite3.connect(
            self.database,
            check_same_thread=False
        )

        self.create_tables()
        self.migrate_tables()

    # --------------------------------------------------
    # CREATE TABLES
    # --------------------------------------------------

    def create_tables(self):

        with self.connection:

            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    type TEXT,
                    source TEXT,
                    message TEXT,
                    timestamp TEXT,
                    color TEXT,
                    observation TEXT
                )
            """)

            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_event INTEGER,
                    to_event INTEGER,
                    relation TEXT,
                    timestamp TEXT
                )
            """)

    # --------------------------------------------------
    # DATABASE MIGRATION
    # --------------------------------------------------

    def migrate_tables(self):

        cursor = self.connection.execute(
            "PRAGMA table_info(events)"
        )

        columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        if "observation" not in columns:

            with self.connection:

                self.connection.execute("""
                    ALTER TABLE events
                    ADD COLUMN observation TEXT
                """)

            print(
                "NOVA Memory: added observation column"
            )

    # --------------------------------------------------
    # ADD EVENT
    # --------------------------------------------------

    def add_event(self, event):

        observation = event.get(
            "observation"
        )

        observation_json = None

        if observation is not None:

            observation_json = json.dumps(
                observation
            )

        with self.lock:

            with self.connection:

                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO events
                    (
                        id,
                        type,
                        source,
                        message,
                        timestamp,
                        color,
                        observation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["id"],
                        event["type"],
                        event["source"],
                        event["message"],
                        event["timestamp"],
                        event["color"],
                        observation_json,
                    )
                )

    # --------------------------------------------------
    # ADD RELATION
    # --------------------------------------------------

    def add_relation(
        self,
        from_event,
        to_event,
        relation
    ):

        with self.lock:

            with self.connection:

                self.connection.execute(
                    """
                    INSERT INTO relations
                    (
                        from_event,
                        to_event,
                        relation,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        from_event,
                        to_event,
                        relation,
                        datetime.now().strftime(
                            "%H:%M:%S"
                        ),
                    )
                )

    # --------------------------------------------------
    # GET EVENTS
    # --------------------------------------------------

    def get_events(self, limit=50):

        cursor = self.connection.execute(
            """
            SELECT
                id,
                type,
                source,
                message,
                timestamp,
                color,
                observation
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        events = []

        for row in rows:

            observation = None

            if row[6]:

                try:

                    observation = json.loads(
                        row[6]
                    )

                except json.JSONDecodeError:

                    observation = None

            events.append({

                "id": row[0],

                "type": row[1],

                "source": row[2],

                "message": row[3],

                "timestamp": row[4],

                "color": row[5],

                "observation": observation,
            })

        return events

    # --------------------------------------------------
    # GET RELATIONS
    # --------------------------------------------------

    def get_relations(self, limit=100):

        cursor = self.connection.execute(
            """
            SELECT
                from_event,
                to_event,
                relation,
                timestamp
            FROM relations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        return [

            {
                "from": row[0],
                "to": row[1],
                "relation": row[2],
                "timestamp": row[3],
            }

            for row in rows

        ]

    # --------------------------------------------------
    # CLOSE
    # --------------------------------------------------

    def close(self):

        self.connection.close()