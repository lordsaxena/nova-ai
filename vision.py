from __future__ import annotations

import logging
import os
import threading
import time
from collections import Counter
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("NOVA.VISION")


class VisionEngine:
    def __init__(
        self,
        model_path: str | None = None,
        confidence: float = 0.45,
        max_detections: int = 50,
    ):
        self.model_path = model_path or os.getenv(
            "NOVA_YOLO_MODEL", "yolov8n.pt"
        )
        self.confidence = max(0.05, min(float(confidence), 0.99))
        self.max_detections = max(1, min(int(max_detections), 200))

        self._model = None
        self._model_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._previous_labels: Counter[str] = Counter()
        self._frame_count = 0
        self._last_frame_at: float | None = None
        self._last_error: str | None = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            try:
                from ultralytics import YOLO

                logger.info("Loading YOLO model: %s", self.model_path)
                self._model = YOLO(self.model_path)
                self._last_error = None
                logger.info("YOLO model ready.")
                return self._model
            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("Could not load YOLO model.")
                raise RuntimeError(
                    "YOLO model could not be loaded. Check that "
                    "ultralytics is installed and the model weights "
                    "are available."
                ) from exc

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0:
            raise ValueError("The uploaded data is not a valid image.")

        height, width = frame.shape[:2]
        if width < 2 or height < 2:
            raise ValueError("The image dimensions are invalid.")

        if width > 4096 or height > 4096:
            raise ValueError("Image dimensions cannot exceed 4096 pixels.")

        return frame

    def process_frame(self, image_bytes: bytes) -> dict[str, Any]:
        """Detect objects in one JPEG/PNG frame."""
        frame = self._decode_image(image_bytes)
        model = self._load_model()

        results = model.predict(
            source=frame,
            conf=self.confidence,
            max_det=self.max_detections,
            verbose=False,
        )

        detections: list[dict[str, Any]] = []
        labels: Counter[str] = Counter()

        if results:
            result = results[0]
            names = result.names or {}

            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()

                    label = str(names.get(class_id, class_id))
                    labels[label] += 1

                    detections.append({
                        "name": label,
                        "class_id": class_id,
                        "confidence": round(confidence, 4),
                        "bbox": [
                            round(float(value), 2)
                            for value in xyxy
                        ],
                    })

        with self._state_lock:
            previous = self._previous_labels
            new_objects = []

            # Report a class when its count increases relative to the
            # previous frame. This is a lightweight change detector,
            # not persistent object identity tracking.
            for label, count in labels.items():
                increase = count - previous.get(label, 0)
                for _ in range(max(0, increase)):
                    new_objects.append(label)

            self._previous_labels = labels
            self._frame_count += 1
            self._last_frame_at = time.time()
            self._last_error = None

            return {
                "status": "ok",
                "timestamp": self._last_frame_at,
                "frame_number": self._frame_count,
                "image_width": int(frame.shape[1]),
                "image_height": int(frame.shape[0]),
                "detection_count": len(detections),
                "detections": detections,
                "new_objects": new_objects,
            }

    def reset_tracking(self) -> None:
        """Reset class-count comparison when a camera session restarts."""
        with self._state_lock:
            self._previous_labels.clear()

    def get_status(self) -> dict:
        with self._state_lock:
            return {
                "status": "ready" if self._model is not None else "idle",
                "model": self.model_path,
                "model_loaded": self._model is not None,
                "confidence_threshold": self.confidence,
                "frame_count": self._frame_count,
                "last_frame_at": self._last_frame_at,
                "last_error": self._last_error,
            }