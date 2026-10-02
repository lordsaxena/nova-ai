import type { NovaEvent } from "../data/novaEvents";

type EventListener = (
  event: NovaEvent
) => void;

let listeners: EventListener[] = [];

let eventHistory: NovaEvent[] = [];


/* =========================================================
   SUBSCRIBE
========================================================= */

export function subscribeToEvents(
  listener: EventListener
) {
  listeners.push(listener);

  return () => {
    listeners = listeners.filter(
      (item) => item !== listener
    );
  };
}


/* =========================================================
   EMIT
========================================================= */

export function emitEvent(
  event: Omit<
    NovaEvent,
    "id" | "timestamp"
  >
) {

  const newEvent: NovaEvent = {
    id: Date.now(),

    timestamp:
      new Date().toLocaleTimeString(),

    ...event,
  };

  eventHistory = [
    newEvent,
    ...eventHistory,
  ].slice(0, 50);

  listeners.forEach(
    (listener) => {
      listener(newEvent);
    }
  );

  return newEvent;
}


/* =========================================================
   HISTORY
========================================================= */

export function getEventHistory() {
  return eventHistory;
}


/* =========================================================
   WEBSOCKET
========================================================= */

let socket: WebSocket | null = null;


export function connectToBackend() {

  if (socket) {
    return;
  }

  socket = new WebSocket(
    "ws://127.0.0.1:8000/ws"
  );


  socket.onopen = () => {

    console.log(
      "NOVA → Backend connected"
    );

  };


  socket.onmessage = (
    message
  ) => {

    try {

      const event =
        JSON.parse(
          message.data
        ) as NovaEvent;

      eventHistory = [
        event,
        ...eventHistory,
      ].slice(0, 50);


      listeners.forEach(
        (listener) => {
          listener(event);
        }
      );

    } catch (error) {

      console.error(
        "NOVA event error:",
        error
      );

    }

  };


  socket.onerror = (
    error
  ) => {

    console.error(
      "NOVA WebSocket error:",
      error
    );

  };


  socket.onclose = () => {

    console.log(
      "NOVA backend disconnected"
    );

    socket = null;

  };

}


export function disconnectFromBackend() {

  if (socket) {

    socket.close();

    socket = null;

  }

}
export function sendCameraFrame(frame: string) {
  if (
    !socket ||
    socket.readyState !== WebSocket.OPEN
  ) {
    return;
  }

  socket.send(
    JSON.stringify({
      type: "CAMERA_FRAME",
      frame,
    })
  );
}