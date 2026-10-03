from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import time

from event_bus import (
    subscribe,
    unsubscribe,
    publish,
)

from event_graph import EventGraph

from vision import VisionEngine


# =====================================================
# NOVA APPLICATION
# =====================================================

app = FastAPI(
    title="NOVA AI Backend",
    version="0.6.0",
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
# CORE SERVICES
# =====================================================

event_graph = EventGraph()

vision_engine = None

last_event_id = None


# =====================================================
# EVENT PROCESSOR
# =====================================================

async def process_event(event: dict):

    global last_event_id

    # ---------------------------------------------
    # SAVE EVENT TO MEMORY
    # ---------------------------------------------

    event_graph.add_event(event)

    # ---------------------------------------------
    # CREATE EVENT RELATION
    # ---------------------------------------------

    if last_event_id is not None:

        event_graph.add_relation(
            last_event_id,
            event["id"],
            "FOLLOWED_BY",
        )

    last_event_id = event["id"]

    # ---------------------------------------------
    # SEND TO FRONTEND
    # ---------------------------------------------

    await publish(event)


# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
async def startup():

    global vision_engine

    loop = asyncio.get_running_loop()

    # ---------------------------------------------
    # VISION → EVENT BUS
    # ---------------------------------------------

    async def vision_publish(event):

        await process_event(event)

    # ---------------------------------------------
    # CREATE VISION ENGINE
    # ---------------------------------------------

    vision_engine = VisionEngine(
        loop,
        vision_publish,
    )

    vision_engine.start()

    # ---------------------------------------------
    # TRACE ONLINE
    # ---------------------------------------------

    await process_event({

        "id": int(
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
            "#f87171",
    })

    # ---------------------------------------------
    # MEMORY READY
    # ---------------------------------------------

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
            "#c084fc",
    })

    print()
    print("=" * 55)
    print("NOVA AI BACKEND")
    print("=" * 55)
    print("✓ Event Graph")
    print("✓ Persistent Memory")
    print("✓ Event Bus")
    print("✓ Vision Engine")
    print("✓ WebSocket")
    print("=" * 55)
    print("Waiting for NOVA frontend...")
    print("=" * 55)
    print()


# =====================================================
# SHUTDOWN
# =====================================================

@app.on_event("shutdown")
async def shutdown():

    global vision_engine

    if vision_engine:

        vision_engine.stop()

    event_graph.close()

    print(
        "NOVA backend stopped"
    )


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
            "active",

        "websocket":
            "active",
    }


# =====================================================
# EVENTS API
# =====================================================

@app.get("/events")
async def get_events():

    return {

        "events":
            event_graph.get_events(
                limit=50
            )
    }


# =====================================================
# GRAPH API
# =====================================================

@app.get("/graph")
async def get_graph():

    return {

        "events":
            event_graph.get_events(
                limit=50
            ),

        "relations":
            event_graph.get_relations(
                limit=100
            ),
    }


# =====================================================
# WEBSOCKET
# =====================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):

    await websocket.accept()

    queue = subscribe()

    print(
        "NOVA frontend connected"
    )

    # =================================================
    # SEND RECENT HISTORY
    # =================================================

    try:

        history = (
            event_graph.get_events(
                limit=8
            )
        )

        for event in reversed(history):

            await websocket.send_json(
                event
            )

    except Exception as error:

        print(
            "History error:",
            error
        )


    # =================================================
    # RECEIVE FROM FRONTEND
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

                # =====================================
                # CAMERA FRAME
                # =====================================

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

                            frame,
                        )


                # =====================================
                # FRONTEND PING
                # =====================================

                elif (
                    message_type
                    ==
                    "PING"
                ):

                    await websocket.send_json({

                        "type":
                            "PONG",

                        "source":
                            "NOVA",

                        "message":
                            "Backend alive",

                        "timestamp":
                            time.strftime(
                                "%H:%M:%S"
                            ),

                        "color":
                            "#67e8f9",

                    })


                # =====================================
                # GESTURE
                # =====================================

                elif (
                    message_type
                    ==
                    "GESTURE"
                ):

                    gesture = (
                        message.get(
                            "gesture"
                        )
                    )

                    if gesture:

                        await process_event({

                            "id":
                                int(
                                    time.time()
                                    * 1000
                                ),

                            "type":
                                "GESTURE_DETECTED",

                            "source":
                                "VISION",

                            "message":
                                f"Gesture: {gesture}",

                            "timestamp":
                                time.strftime(
                                    "%H:%M:%S"
                                ),

                            "color":
                                "#facc15",

                            "observation": {

                                "gesture":
                                    gesture,

                            },

                        })


        except Exception as error:

            print(
                "Frontend receiver stopped:",
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
                "Frontend sender stopped:",
                error
            )


    # =================================================
    # RUN BOTH TASKS
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
                sender_task,
            ],

            return_when=
                asyncio.FIRST_COMPLETED,
        )

        for task in pending:

            task.cancel()


    except Exception as error:

        print(
            "WebSocket error:",
            error
        )


    finally:

        unsubscribe(queue)

        print(
            "NOVA frontend disconnected"
        )