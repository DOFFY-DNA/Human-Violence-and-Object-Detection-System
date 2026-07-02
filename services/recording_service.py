"""
services/recording_service.py
Automatically records a 5-second video clip when violence is detected.
Saves the clip to the recordings/ directory.
"""
import os
import sys
import cv2
import queue
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import timestamp_str

logger = get_logger("recording_service")


class RecordingService:
    """
    Listens to a frame queue and writes a fixed-duration video clip.
    Call start_recording() to begin; it will stop automatically after
    CLIP_DURATION_SEC seconds.
    """

    def __init__(self):
        self._recording = False
        self._thread: threading.Thread | None = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=200)
        self._last_clip_path: str = ""

    def enqueue_frame(self, frame):
        """Push a frame to the recorder (non-blocking; drops if full)."""
        if self._recording:
            try:
                self._frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def start_recording(self, on_complete=None) -> str:
        """
        Start recording a CLIP_DURATION_SEC clip.
        on_complete(clip_path: str) is called when done.
        Returns the expected output file path.
        """
        if self._recording:
            logger.warning("Recording already in progress; skipping new request")
            return self._last_clip_path

        ts = timestamp_str()
        filename = f"violence_clip_{ts}.mp4"
        clip_path = os.path.join(config.RECORDINGS_DIR, filename)
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        self._last_clip_path = clip_path
        self._recording = True

        def _record():
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                clip_path, fourcc, config.VIDEO_FPS,
                (config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
            )
            frames_needed = int(config.CLIP_DURATION_SEC * config.VIDEO_FPS)
            written = 0
            logger.info(f"Recording clip: {clip_path} (target {frames_needed} frames)")

            while written < frames_needed:
                try:
                    frame = self._frame_queue.get(timeout=2.0)
                    resized = cv2.resize(frame, (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
                    writer.write(resized)
                    written += 1
                except queue.Empty:
                    logger.warning("RecordingService: frame queue timeout – padding clip")
                    break

            writer.release()
            self._recording = False
            logger.info(f"Clip saved: {clip_path} ({written} frames)")
            if on_complete:
                on_complete(clip_path)

        self._thread = threading.Thread(target=_record,
                                        name="RecordingThread", daemon=True)
        self._thread.start()
        return clip_path

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def last_clip_path(self) -> str:
        return self._last_clip_path
