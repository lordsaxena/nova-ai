import asyncio
from typing import Any


clients: set[asyncio.Queue] = set()


def subscribe():

    queue = asyncio.Queue()

    clients.add(queue)

    return queue


def unsubscribe(queue):

    clients.discard(queue)


async def publish(
    event: dict[str, Any]
):

    dead_clients = []

    for queue in list(clients):

        try:

            queue.put_nowait(event)

        except Exception:

            dead_clients.append(queue)

    for queue in dead_clients:

        clients.discard(queue)