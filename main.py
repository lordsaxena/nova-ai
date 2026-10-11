from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from event_graph import EventGraph
from knowledge_graph import KnowledgeGraph
from nova_core import NovaCore
from agent_engine import AgentEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NOVA")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

event_graph = EventGraph(str(DATA_DIR / "nova_trace.db"))
knowledge_graph = KnowledgeGraph(str(DATA_DIR / "nova_knowledge.db"))

# These optional modules are part of the wider NOVA project.
# The TRACE and knowledge APIs can still run if they are unavailable.
agent_router = None
vision_engine = None


try:
    from agent_router import AgentRouter
    from event_bus import publish

    agent_router = AgentRouter(
        publish_event=publish,
        agent_engine=None,
    )
    logger.info("Agent Router initialized.")
except Exception:
    logger.exception("Agent Router unavailable.")

try:
    from vision import VisionEngine

    vision_engine = VisionEngine()
    logger.info("Vision Engine initialized.")
except Exception:
    logger.exception("Vision Engine unavailable.")

nova_core = NovaCore(event_graph, knowledge_graph)

agent_engine = AgentEngine(
    router=agent_router,
    event_graph=event_graph,
    knowledge_graph=knowledge_graph,
    nova_core=nova_core,
)
# Connect the initialized router to the engine.
if agent_router is not None:
    agent_router.agent_engine = agent_engine

connected_clients: set[WebSocket] = set()
client_lock = asyncio.Lock()

SOURCE_ENTITIES = {
    "NOVA": ("NOVA AI", "SYSTEM"),
    "NOVA_CORE": ("NOVA Core", "SYSTEM"),
    "AGENT_ENGINE": ("NOVA Agent Engine", "SYSTEM"),
    "AGENT_ROUTER": ("NOVA Agent Router", "SYSTEM"),
    "VISION": ("NOVA Vision Engine", "SYSTEM"),
    "TRACE": ("TRACE Event Graph", "SYSTEM"),
    "API": ("NOVA API", "SYSTEM"),
}

AGENT_NAMES = {
    "ANALYSIS_AGENT": "Analysis Agent",
    "VISION_AGENT": "Vision Agent",
    "SYSTEM_AGENT": "System Agent",
    "RESEARCH_AGENT": "Research Agent",
    "COMMUNICATION_AGENT": "Communication Agent",
}


class EventInput(BaseModel):
    event_type: str = "USER_EVENT"
    source: str = "API"
    observation: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
    parent_event_id: str | None = None


class AgentTaskInput(BaseModel):
    task: str = Field(min_length=1, max_length=10000)
    event_id: str | None = None


def auto_link_event(event: dict) -> list[dict]:
    """Associate a stored event with its source and semantic entities."""
    event_id = str(event["id"])
    source = str(event.get("source", "UNKNOWN")).upper()
    event_type = str(event.get("event_type", "UNKNOWN")).upper()
    observation = event.get("observation", {})

    if not isinstance(observation, dict):
        observation = {}

    linked: list[dict] = []

    source_name, source_type = SOURCE_ENTITIES.get(
        source,
        (source.replace("_", " ").title(), "MODULE"),
    )

    linked.append(
        knowledge_graph.link_event(
            event_id,
            source_name,
            role="EVENT_SOURCE",
            entity_type=source_type,
            metadata={"source": source},
        )
    )

    def link_concept(
        name: str,
        entity_type: str,
        role: str,
        relation: str,
        metadata: dict | None = None,
    ) -> None:
        name = str(name).strip()
        if not name:
            return

        details = metadata or {}
        linked.append(
            knowledge_graph.link_event(
                event_id,
                name,
                role=role,
                entity_type=entity_type,
                metadata=details,
            )
        )

        if name.casefold() != source_name.casefold():
            try:
                knowledge_graph.add_relation(
                    source_name,
                    name,
                    relation,
                    metadata={"event_id": event_id, **details},
                )
            except Exception:
                logger.exception(
                    "Could not create semantic relation: %s -> %s",
                    source_name,
                    name,
                )

    # Link recognized gestures.
    gesture = observation.get("gesture")
    if isinstance(gesture, dict):
        gesture_name = gesture.get("name") or gesture.get("label")
        confidence = gesture.get("confidence")
    else:
        gesture_name = gesture
        confidence = observation.get("confidence")

    if gesture_name and (
        "GESTURE" in event_type or "GESTURE" in str(gesture_name).upper()
    ):
        link_concept(
            str(gesture_name),
            "GESTURE",
            "RECOGNIZED_GESTURE",
            "RECOGNIZED",
            {"confidence": confidence} if confidence is not None else {},
        )

    # Link objects reported by vision events.
    detections = observation.get("detections", [])
    if isinstance(detections, list):
        for detection in detections[:50]:
            if not isinstance(detection, dict):
                continue

            label = (
                detection.get("name")
                or detection.get("class_name")
                or detection.get("class")
                or detection.get("label")
            )
            if label is None:
                continue

            confidence = detection.get("confidence")
            details = {}
            if confidence is not None:
                details["confidence"] = confidence
            if detection.get("track_id") is not None:
                details["track_id"] = detection["track_id"]

            link_concept(
                str(label),
                "OBJECT",
                "DETECTED_OBJECT",
                "DETECTED",
                details,
            )

    # Link explicit tracked objects.
    track_ids = observation.get("track_ids", [])
    if not isinstance(track_ids, list):
        track_ids = []

    for track_id in track_ids[:50]:
        link_concept(
            f"Track {track_id}",
            "TRACK",
            "TRACK_REFERENCED",
            "REFERENCED_TRACK",
        )

    # Link agents involved in routing or execution.
    agent = (
        observation.get("agent")
        or observation.get("agent_name")
        or observation.get("selected_agent")
    )
    if agent:
        agent_key = str(agent).upper()
        agent_name = AGENT_NAMES.get(
            agent_key, str(agent).replace("_", " ").title()
        )
        link_concept(
            agent_name,
            "AI_AGENT",
            "AGENT_INVOLVED",
            "INVOLVED_AGENT",
        )

    # Link explicitly named entities supplied by other modules.
    entities = observation.get("entities", [])
    if isinstance(entities, list):
        for item in entities[:50]:
            if isinstance(item, str):
                name, kind = item, "CONCEPT"
            elif isinstance(item, dict):
                name = item.get("name") or item.get("label")
                kind = item.get("type", "CONCEPT")
            else:
                continue

            if name:
                link_concept(
                    str(name),
                    str(kind).upper(),
                    "MENTIONED_ENTITY",
                    "MENTIONS",
                )

    return linked


async def broadcast(message: dict) -> None:
    """Send an event to connected WebSocket clients."""
    async with client_lock:
        clients = list(connected_clients)

    disconnected = []
    for client in clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)

    if disconnected:
        async with client_lock:
            for client in disconnected:
                connected_clients.discard(client)


async def process_event(event: dict) -> dict:
    """Store, link, reason about, and broadcast a meaningful event."""
    event = dict(event)
    event.setdefault("id", uuid4().hex)
    event.setdefault("timestamp", time.time())
    event.setdefault("event_type", "UNKNOWN")
    event.setdefault("source", "UNKNOWN")
    event.setdefault("observation", {})

    event_id = str(event["id"])
    event["id"] = event_id

    # High-frequency camera detections can be broadcast without
    # filling persistent memory with every individual video frame.
    if event["event_type"] == "VISION_DETECTION":
        await broadcast({"type": "event", "data": event})
        return {"event": event, "persisted": False}

    previous_events = event_graph.get_events(limit=1)
    stored_event = event_graph.add_event(event)

    # Preserve chronological and causal links.
    if previous_events:
        previous_id = str(previous_events[0]["id"])
        if previous_id != event_id:
            try:
                event_graph.add_relation(
                    previous_id,
                    event_id,
                    "FOLLOWED_BY",
                    {"origin": "main.process_event"},
                )
            except ValueError:
                logger.exception("Could not create chronology link.")

    parent_id = event.get("parent_event_id")
    if parent_id is not None and event_graph.get_event(parent_id):
        if str(parent_id) != event_id:
            try:
                event_graph.add_relation(
                    str(parent_id),
                    event_id,
                    "TRIGGERED",
                    {"origin": "parent_event_id"},
                )
            except ValueError:
                logger.exception("Could not create causal link.")

    try:
        auto_link_event(stored_event)
    except Exception:
        logger.exception("Automatic entity linking failed for %s", event_id)

    await broadcast({"type": "event", "data": stored_event})

    # Do not recursively reason about NOVA's own reasoning events.
    if stored_event["event_type"] == "NOVA_REASONING":
        return {"event": stored_event, "persisted": True}

    try:
        result = nova_core.process_event(stored_event)
        reasoning_event = result["reasoning"]
        reasoning_event["parent_event_id"] = event_id

        event_graph.add_event(reasoning_event)
        event_graph.add_relation(
            event_id,
            reasoning_event["id"],
            "TRIGGERED",
            {"origin": "nova_core"},
        )

        auto_link_event(reasoning_event)
        await broadcast({
            "type": "reasoning",
            "data": reasoning_event,
        })

        return {
            "event": stored_event,
            "reasoning": reasoning_event,
            "context": result["context"],
            "persisted": True,
        }

    except Exception:
        logger.exception("NOVA Core failed to process event %s", event_id)
        return {
            "event": stored_event,
            "persisted": True,
            "reasoning_error": "NOVA Core could not process this event.",
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NOVA AI starting...")
    startup_events = [
        ("TRACE_ONLINE", "TRACE"),
        ("MEMORY_READY", "NOVA"),
        ("NOVA_CORE_ONLINE", "NOVA_CORE"),
        ("AGENT_ENGINE_ONLINE", "AGENT_ENGINE"),
    ]

    for event_type, source in startup_events:
        await process_event({
            "id": uuid4().hex,
            "event_type": event_type,
            "source": source,
            "timestamp": time.time(),
            "observation": {"status": "online"},
        })

    logger.info("NOVA AI is online.")
    yield

    async with client_lock:
        clients = list(connected_clients)
        connected_clients.clear()

    for client in clients:
        try:
            await client.close()
        except Exception:
            pass

    event_graph.close()
    knowledge_graph.close()
    logger.info("NOVA AI stopped.")


app = FastAPI(
    title="NOVA AI",
    version="2.0.0",
    description="NOVA AI, TRACE event graph, and knowledge graph API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "NOVA AI",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "online",
        "trace_events": event_graph.count(),
        "vision_available": vision_engine is not None,
        "agent_router_available": agent_router is not None,
    }


@app.get("/core/context")
async def get_core_context(query: str | None = None):
    return nova_core.build_context(query=query, limit=10)


@app.get("/core/status")
async def core_status():
    return nova_core.get_status()


@app.post("/events")
async def create_event(payload: EventInput):
    event = {
        "id": uuid4().hex,
        "event_type": payload.event_type,
        "source": payload.source,
        "timestamp": time.time(),
        "observation": payload.observation,
        "message": payload.message,
        "parent_event_id": payload.parent_event_id,
    }

    try:
        return await process_event(event)
    except Exception as exc:
        logger.exception("Event processing failed.")
        raise HTTPException(
            status_code=500,
            detail="Event processing failed.",
        ) from exc


@app.get("/events")
async def list_events(
    limit: int = 100,
    event_type: str | None = None,
    source: str | None = None,
):
    return {
        "events": event_graph.get_events(
            limit=limit,
            event_type=event_type,
            source=source,
        )
    }


@app.get("/events/{event_id}")
async def get_event(event_id: str):
    event = event_graph.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


@app.get("/events/{event_id}/related")
async def related_events(event_id: str, limit: int = 50):
    if event_graph.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {"events": event_graph.get_related_events(event_id, limit)}


@app.get("/events/{event_id}/entities")
async def event_entities(event_id: str):
    if event_graph.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {
        "event_id": event_id,
        "entities": knowledge_graph.get_event_entities(event_id),
    }


@app.get("/graph")
async def trace_graph(limit: int = 200):
    return event_graph.get_graph(limit=limit)


@app.get("/graph/causal-chain/{event_id}")
async def causal_chain(event_id: str, max_depth: int = 20):
    if event_graph.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {
        "event_id": event_id,
        "chain": event_graph.get_causal_chain(event_id, max_depth),
    }


@app.get("/knowledge/graph")
async def knowledge_graph_view(limit: int = 200):
    return knowledge_graph.get_graph(limit=limit)


@app.get("/knowledge/entities")
async def search_entities(
    query: str | None = None,
    entity_type: str | None = None,
    limit: int = 100,
):
    return {
        "entities": knowledge_graph.get_entities(
            query=query,
            entity_type=entity_type,
            limit=limit,
        )
    }


@app.get("/knowledge/entities/{entity_name}")
async def get_entity(entity_name: str, depth: int = 1):
    entity = knowledge_graph.get_entity(entity_name)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    return knowledge_graph.get_neighborhood(entity_name, depth=depth)


@app.post("/agents/execute")
async def execute_agent_task(payload: AgentTaskInput):
    event_id = payload.event_id

    if event_id and event_graph.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    try:
        context = nova_core.build_context(
            query=payload.task,
            limit=10,
        )

        if event_id:
            event = event_graph.get_event(event_id)
            event_context = nova_core.build_context(
                event=event,
                query=payload.task,
                limit=10,
            )
            context.update(event_context)

        result = await agent_engine.execute(
            task=payload.task,
            context=context,
            event_id=event_id,
        )

        await broadcast({"type": "agent_execution", "data": result})
        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent execution failed.")
        raise HTTPException(
            status_code=500,
            detail="Agent execution failed.",
        ) from exc


@app.get("/agents/status")
async def agent_status():
    return agent_engine.get_status()


@app.get("/vision/status")
async def vision_status():
    if vision_engine is None:
        return {
            "status": "unavailable",
            "message": "Vision Engine could not be initialized.",
        }

    return {"status": "initialized"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with client_lock:
        connected_clients.add(websocket)

    try:
        await websocket.send_json({
            "type": "connection",
            "data": {
                "status": "connected",
                "service": "NOVA AI",
                "timestamp": time.time(),
            },
        })

        while True:
            message = await websocket.receive_json()
            action = message.get("action")

            if action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time(),
                })

            elif action == "get_context":
                context = nova_core.build_context(
                    query=message.get("query"),
                    limit=10,
                )
                await websocket.send_json({
                    "type": "context",
                    "data": context,
                })

            elif action == "submit_event":
                event_payload = message.get("event", {})
                if not isinstance(event_payload, dict):
                    await websocket.send_json({
                        "type": "error",
                        "message": "The event must be a JSON object.",
                    })
                    continue

                event_payload.setdefault("id", uuid4().hex)
                event_payload.setdefault("source", "WEBSOCKET")
                event_payload.setdefault("event_type", "USER_EVENT")
                event_payload.setdefault("timestamp", time.time())

                result = await process_event(event_payload)
                await websocket.send_json({
                    "type": "event_result",
                    "data": result,
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error.")
    finally:
        async with client_lock:
            connected_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )