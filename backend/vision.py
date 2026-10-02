import asyncio
import base64
import time

import cv2
import numpy as np


class VisionEngine:

    def __init__(
        self,
        loop,
        publish_event
    ):

        self.loop = loop
        self.publish_event = publish_event

        self.running = False

        # ==========================================
        # PERSON DETECTOR
        # ==========================================

        self.person_detector = cv2.HOGDescriptor()

        self.person_detector.setSVMDetector(
            cv2.HOGDescriptor_getDefaultPeopleDetector()
        )

        # ==========================================
        # STATE
        # ==========================================

        self.previous_gray = None

        self.last_person_event = 0
        self.last_motion_event = 0

    # ==============================================
    # START
    # ==============================================

    def start(self):

        self.running = True

        print(
            "NOVA Vision Engine ready"
        )

        print(
            "Waiting for browser camera frames..."
        )

    # ==============================================
    # STOP
    # ==============================================

    def stop(self):

        self.running = False

        self.previous_gray = None

        print(
            "NOVA Vision Engine stopped"
        )

    # ==============================================
    # RECEIVE BASE64 FRAME
    # ==============================================

    def process_base64_frame(
        self,
        frame_data
    ):

        if not self.running:
            return

        try:

            # Remove data URL prefix
            if "," in frame_data:

                frame_data = (
                    frame_data
                    .split(",", 1)[1]
                )

            image_bytes = base64.b64decode(
                frame_data
            )

            array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                array,
                cv2.IMREAD_COLOR
            )

            if frame is None:
                return

            self.process_frame(frame)

        except Exception as error:

            print(
                "Vision frame error:",
                error
            )

    # ==============================================
    # PROCESS FRAME
    # ==============================================

    def process_frame(
        self,
        frame
    ):

        if not self.running:
            return

        height, width = frame.shape[:2]

        now = time.time()

        # ==========================================
        # MOTION DETECTION
        # ==========================================

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.GaussianBlur(
            gray,
            (21, 21),
            0
        )

        if self.previous_gray is not None:

            difference = cv2.absdiff(
                self.previous_gray,
                gray
            )

            _, threshold = cv2.threshold(
                difference,
                25,
                255,
                cv2.THRESH_BINARY
            )

            motion_area = (
                cv2.countNonZero(
                    threshold
                )
                / (width * height)
            )

            if (
                motion_area > 0.01
                and
                now - self.last_motion_event > 2
            ):

                self.last_motion_event = now

                self.emit({

                    "id": int(
                        time.time() * 1000
                    ),

                    "type":
                        "MOTION_DETECTED",

                    "source":
                        "VISION",

                    "message":
                        "Movement detected",

                    "timestamp":
                        time.strftime(
                            "%H:%M:%S"
                        ),

                    "color":
                        "#7dd3fc",

                    "observation": {

                        "motion":
                            True,

                        "motion_area":
                            motion_area,

                        "frame": {

                            "width":
                                width,

                            "height":
                                height
                        }
                    }
                })

        self.previous_gray = gray

        # ==========================================
        # PERSON DETECTION
        # ==========================================

        if (
            now -
            self.last_person_event
            < 0.2
        ):
            return

        boxes, weights = (
            self.person_detector
            .detectMultiScale(
                frame,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05
            )
        )

        if len(boxes) == 0:

            return

        # ==========================================
        # STRONGEST PERSON
        # ==========================================

        strongest_index = 0

        if len(weights) > 1:

            strongest_index = int(
                np.argmax(weights)
            )

        x, y, w, h = (
            boxes[strongest_index]
        )

        confidence = float(
            weights[strongest_index]
        )

        center_x = x + (w / 2)
        center_y = y + (h / 2)

        normalized_x = (
            center_x / width
        )

        normalized_y = (
            center_y / height
        )

        self.last_person_event = now

        # ==========================================
        # PERSON EVENT
        # ==========================================

        self.emit({

            "id": int(
                time.time() * 1000
            ),

            "type":
                "PERSON_DETECTED",

            "source":
                "VISION",

            "message":
                "Person detected",

            "timestamp":
                time.strftime(
                    "%H:%M:%S"
                ),

            "color":
                "#7dd3fc",

            "observation": {

                "person":
                    True,

                "person_count":
                    len(boxes),

                "confidence":
                    confidence,

                "position": {

                    "x":
                        normalized_x,

                    "y":
                        normalized_y
                },

                "frame": {

                    "width":
                        width,

                    "height":
                        height
                },

                "region": {

                    "x":
                        int(x),

                    "y":
                        int(y),

                    "width":
                        int(w),

                    "height":
                        int(h)
                }
            }
        })

    # ==============================================
    # EMIT EVENT
    # ==============================================

    def emit(
        self,
        event
    ):

        asyncio.run_coroutine_threadsafe(
            self.publish_event(event),
            self.loop
        )