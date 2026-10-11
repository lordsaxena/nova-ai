
from __future__ import annotations

import time
import uuid
from typing import Any


class AgentEngine:
    """Coordinates NOVA agents with TRACE, KnowledgeGraph and NovaCore."""

    def __init__(
        self,
        router=None,
        event_graph=None,
        knowledge_graph=None,
        nova_core=None,
    ):
        self.router = router
        self.event_graph = event_graph
        self.knowledge_graph = knowledge_graph
        self.nova_core = nova_core
        self.started_at = time.time()
        self.status = "online"

    def _record_event(
        self,
        event_type: str,
        source: str,
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "source": source,
            "timestamp": time.time(),
            "observation": observation,
        }

        if self.event_graph is not None:
            add_event = getattr(self.event_graph, "add_event", None)
            if callable(add_event):
                try:
                    result = add_event(
                        event_type=event_type,
                        source=source,
                        payload=observation,
                    )
                    if isinstance(result, dict):
                        event.update(result)
                except TypeError:
                    try:
                        result = add_event(event)
                        if isinstance(result, dict):
                            event.update(result)
                    except Exception:
                        pass

        return event

    def _route(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        if self.router is None:
            return {
                "agent": "ANALYSIS_AGENT",
                "response": (
                    "NOVA received your task. The agent router is not "
                    "available, so this is a fallback response."
                ),
            }

        for method_name in ("route", "dispatch", "select_agent", "run"):
            method = getattr(self.router, method_name, None)
            if not callable(method):
                continue

            try:
                result = method(task, context)
            except TypeError:
                try:
                    result = method(task)
                except TypeError:
                    continue

            if isinstance(result, dict):
                return result

            if result is not None:
                return {"response": str(result)}

        return {
            "agent": "ANALYSIS_AGENT",
            "response": "No compatible routing method was found.",
        }

    def execute(
        self,
        task: str,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        task = str(task or "").strip()
        if not task:
            raise ValueError("Task cannot be empty.")

        context: dict[str, Any] = {}

        if self.nova_core is not None:
            try:
                context = self.nova_core.build_context(
                    event={"id": event_id} if event_id else {},
                    query=task,
                )
            except Exception as exc:
                context = {"context_error": str(exc)}

        result = self._route(task, context)
        output = {
            "id": str(uuid.uuid4()),
            "task": task,
            "agent": result.get("agent", result.get("agent_name", "UNKNOWN")),
            "response": result.get(
                "response",
                result.get("message", result.get("result", str(result))),
            ),
            "context": context,
            "timestamp": time.time(),
        }

        self._record_event(
            "AGENT_EXECUTED",
            "AGENT_ENGINE",
            output,
        )

        return output

    def run(
        self,
        task: str,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return self.execute(task, event_id)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "router_available": self.router is not None,
        }

    def close(self) -> None:
        self.status = "offline"