from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import time

from event_bus import (
    subscribe,
    unsubscribe,
    publish
)

from event_graph import EventGraph

from vision import VisionEngine


app = FastAPI(
    title="NOVA AI Backend",
    version="0.6.0"
)


# =====================================================
# CORS
# =====================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =====================================================
# CORE
# =====================================================

event_graph = EventGraph()

vision_engine = None

last_event_id = None


# =====================================================
# EVENT PROCESSOR
# =====================================================

async def process_event(
    event
):

    global last_event_id

    event_graph.add_event(
        event
    )

    if last_event_id is not None:

        event_graph.add_relation(

            last_event_id,

            event["id"],

            "FOLLOWED_BY"
        )

    last_event_id = event["id"]

    await publish(
        event
    )


# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
async def startup():

    global vision_engine

    loop = asyncio.get_running_loop()

    async def vision_publish(
        event
    ):

        await process_event(
            event
        )

    vision_engine = VisionEngine(

        loop,

        vision_publish
    )

    vision_engine.start()

    # ================================================
    # TRACE
    # ================================================

    await process_event({

        "id":
            int(
                time.time() * 1000
            ),

        "type":
            "TRACE_ONLINE",

        "source":
            "TRACE",

        "message":
            "Event graph initialized",

        "timestamp":
            time.strftime(
                "%H:%M:%S"
            ),

        "color":
            "#f87171"
    })

    # ================================================
    # MEMORY
    # ================================================

    await process_event({

        "id":
            int(
                time.time() * 1000
            ) + 1,

        "type":
            "MEMORY_READY",

        "source":
            "MEMORY",

        "message":
            "Persistent event memory ready",

        "timestamp":
            time.strftime(
                "%H:%M:%S"
            ),

        "color":
            "#c084fc"
    })


# =====================================================
# SHUTDOWN
# =====================================================

@app.on_event("shutdown")
async def shutdown():

    global vision_engine

    if vision_engine:

        vision_engine.stop()

    event_graph.close()


# =====================================================
# ROOT
# =====================================================

@app.get("/")
async def root():

    return {

        "name":
            "NOVA AI",

        "status":
            "online",

        "version":
            "0.6.0",

        "vision":
            "browser-stream",

        "trace":
            "active",

        "memory":
            "active"
    }


# =====================================================
# EVENTS
# =====================================================

@app.get("/events")
async def events():

    return {

        "events":
            event_graph.get_events()
    }


# =====================================================
# GRAPH
# =====================================================

@app.get("/graph")
async def graph():

    return {

        "events":
            event_graph.get_events(),

        "relations":
            event_graph.get_relations()
    }


# =====================================================
# WEBSOCKET
# =====================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    queue = subscribe()

    print(
        "NOVA frontend connected"
    )

    # =================================================
    # SEND STORED EVENTS
    # =================================================

    history = event_graph.get_events(
        limit=8
    )

    for event in reversed(
        history
    ):

        await websocket.send_json(
            event
        )

    # =================================================
    # RECEIVE CAMERA FRAMES
    # =================================================

    async def receive_messages():

        try:

            while True:

                message = (
                    await websocket
                    .receive_json()
                )

                message_type = (
                    message.get("type")
                )

                # -------------------------------------
                # CAMERA FRAME
                # -------------------------------------

                if (
                    message_type
                    ==
                    "CAMERA_FRAME"
                ):

                    frame = (
                        message.get(
                            "frame"
                        )
                    )

                    if (
                        frame
                        and
                        vision_engine
                    ):

                        await asyncio.to_thread(

                            vision_engine
                            .process_base64_frame,

                            frame
                        )

        except Exception as error:

            print(
                "Camera receive stopped:",
                error
            )

    # =================================================
    # SEND EVENTS TO FRONTEND
    # =================================================

    async def send_events():

        try:

            while True:

                event = (
                    await queue.get()
                )

                await websocket.send_json(
                    event
                )

        except Exception as error:

            print(
                "Event sender stopped:",
                error
            )

    # =================================================
    # RUN BOTH SIDES
    # =================================================

    receiver_task = asyncio.create_task(
        receive_messages()
    )

    sender_task = asyncio.create_task(
        send_events()
    )

    try:

        done, pending = await asyncio.wait(

            [
                receiver_task,
                sender_task
            ],

            return_when=
                asyncio.FIRST_COMPLETED
        )

        for task in pending:

            task.cancel()

    finally:

        unsubscribe(
            queue
        )

        print(
            "NOVA frontend disconnected"
        )