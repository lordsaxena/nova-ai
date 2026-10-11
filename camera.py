from __future__ import annotations

import base64
import binascii
import threading
import time
from typing import Any
from uuid import uuid4


class CameraError(ValueError):
    pass


class CameraSessionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def start(self, session_id: str | None = None) -> dict:
        session_id = session_id or uuid4().hex

        with self._lock:
            existing = self._sessions.get(session_id)

            if existing and existing["status"] == "running":
                return dict(existing)

            session = {
                "session_id": session_id,
                "status": "running",
                "started_at": time.time(),
                "last_frame_at": None,
                "frames_processed": 0,
            }
            self._sessions[session_id] = session
            return dict(session)

    def record_frame(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)

            if not session or session["status"] != "running":
                raise CameraError("Camera session is not running.")

            session["last_frame_at"] = time.time()
            session["frames_processed"] += 1
            return dict(session)

    def stop(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return {
                    "session_id": session_id,
                    "status": "stopped",
                    "frames_processed": 0,
                }

            session["status"] = "stopped"
            session["stopped_at"] = time.time()
            return dict(session)

    def get(self, session_id: str) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            return dict(session) if session else None

    def list_sessions(self) -> list[dict]:
        with self._lock:
            return [dict(session) for session in self._sessions.values()]


def decode_camera_frame(
    data_url: str,
    max_bytes: int = 5 * 1024 * 1024,
) -> bytes:
    """Decode a browser JPEG/PNG data URL into image bytes."""
    if not isinstance(data_url, str) or not data_url:
        raise CameraError("An image data URL is required.")

    header, separator, encoded = data_url.partition(",")
    if not separator:
        raise CameraError("Invalid image data URL.")

    header = header.lower()
    if not (
        header.startswith("data:image/jpeg;base64")
        or header.startswith("data:image/jpg;base64")
        or header.startswith("data:image/png;base64")
    ):
        raise CameraError("Only JPEG and PNG images are supported.")

    # Reject excessively large payloads before decoding.
    if len(encoded) > (max_bytes * 4 // 3 + 16):
        raise CameraError("Image exceeds the maximum allowed size.")

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CameraError("Invalid base64 image data.") from exc

    if not image_bytes:
        raise CameraError("The uploaded image is empty.")

    if len(image_bytes) > max_bytes:
        raise CameraError("Image exceeds the maximum allowed size.")

    return image_bytes