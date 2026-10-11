from __future__ import annotations

import time
from typing import Any
from uuid import uuid4


class NovaCore:
    def __init__(self, event_graph, knowledge_graph):
        self.event_graph = event_graph
        self.knowledge_graph = knowledge_graph
        self.started_at = time.time()
        self.status = "online"

    def build_context(
        self,
        event: dict | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Build a context packet from TRACE and the knowledge graph."""
        limit = max(1, min(int(limit), 50))
        event = event or {}
        event_id = event.get("id")

        recent_events = self.event_graph.get_events(limit=limit)
        linked_entities = []
        related_entities = []
        relations = []
        related_events = []

        if event_id is not None:
            linked_entities = self.knowledge_graph.get_event_entities(
                event_id
            )
            related_events = self.event_graph.get_related_events(
                event_id, limit=limit
            )

        # Search entity names using useful terms from the current event/query.
        search_text = " ".join(
            str(value)
            for value in (
                query,
                event.get("event_type"),
                event.get("source"),
                event.get("message"),
            )
            if value
        )

        words = [
            word.strip(".,!?;:()[]{}\"'").lower()
            for word in search_text.split()
        ]
        words = [
            word for word in words
            if len(word) >= 4 and word not in {
                "that", "this", "from", "with", "have", "what",
                "when", "where", "which", "into", "event",
            }
        ]

        seen_ids = set()
        for word in words[:8]:
            for entity in self.knowledge_graph.get_entities(
                query=word, limit=5
            ):
                if entity["id"] not in seen_ids:
                    seen_ids.add(entity["id"])
                    related_entities.append(entity)

        for linked in linked_entities:
            entity_name = linked.get("name")
            if not entity_name and isinstance(linked.get("entity"), dict):
                entity_name = linked["entity"].get("name")

            if entity_name:
                neighborhood = self.knowledge_graph.get_neighborhood(
                    entity_name, depth=1
                )
                relations.extend(neighborhood.get("relations", []))
                for entity in neighborhood.get("entities", []):
                    if entity["id"] not in seen_ids:
                        seen_ids.add(entity["id"])
                        related_entities.append(entity)

        # Keep the context compact and suitable for an agent/model prompt.
        return {
            "generated_at": time.time(),
            "query": query,
            "current_event": event,
            "recent_events": recent_events,
            "related_events": related_events,
            "event_entities": linked_entities,
            "related_entities": related_entities[:30],
            "knowledge_relations": relations[:50],
        }

    def process_event(self, event: dict) -> dict:
        """Interpret an event using context from both graphs."""
        context = self.build_context(event=event, limit=10)
        event_type = str(event.get("event_type", "UNKNOWN"))
        source = str(event.get("source", "UNKNOWN"))

        linked_names = []
        for item in context["event_entities"]:
            name = item.get("name")
            if not name and isinstance(item.get("entity"), dict):
                name = item["entity"].get("name")
            if name:
                linked_names.append(name)

        reasoning = {
            "id": uuid4().hex,
            "event_type": "NOVA_REASONING",
            "source": "NOVA_CORE",
            "timestamp": time.time(),
            "parent_event_id": str(event.get("id", "")),
            "observation": {
                "input_event_type": event_type,
                "input_source": source,
                "linked_entities": linked_names,
                "recent_event_count": len(context["recent_events"]),
                "related_event_count": len(context["related_events"]),
                "related_entity_count": len(context["related_entities"]),
                "knowledge_relation_count": len(
                    context["knowledge_relations"]
                ),
                "context_available": bool(
                    context["recent_events"]
                    or context["related_entities"]
                    or context["event_entities"]
                ),
                "summary": (
                    f"Processed {event_type} from {source}; "
                    f"found {len(linked_names)} directly linked entities "
                    f"and {len(context['related_entities'])} related entities."
                ),
            },
        }

        return {
            "status": self.status,
            "reasoning": reasoning,
            "context": context,
        }

    def get_status(self) -> dict:
        return {
            "status": self.status,
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "event_count": self.event_graph.count(),
        }

    def close(self) -> None:
        self.status = "offline"