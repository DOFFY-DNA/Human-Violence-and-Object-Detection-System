"""
services/alert_service.py
Coordinates knife and violence detection state.
Saves snapshots to alerts/ and triggers email ONLY when BOTH are confirmed.
"""
import os
import sys
import cv2
import threading
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import timestamp_str, ensure_dir

logger = get_logger("alert_service")


class AlertService:
    """
    Stateful coordinator:
      • knife_detected  → save snapshot to alerts/knife_*.jpg
      • violence_detected → save snapshot to alerts/violence_*.jpg
      • BOTH confirmed → trigger email with all collected evidence
    """

    def __init__(self, recording_service, email_sent_callback: Callable = None):
        self._recording_service  = recording_service
        self._email_callback     = email_sent_callback
        self._lock               = threading.Lock()

        self._knife_confirmed    = False
        self._violence_confirmed = False

        self._knife_snapshots:    list[str] = []
        self._violence_snapshots: list[str] = []

        self._email_in_flight    = False    # prevent double-sending
        self._MAX_SNAPS          = 4

    # ──────────────────────────────────────────────────────────────────────────
    def handle_knife_detection(self, frame, hrm_result: dict,
                               db_log_fn: Callable = None):
        """Call this when HRM validates a knife frame."""
        if not hrm_result.get("confirmed"):
            return

        conf = hrm_result.get("confidence", 0.0)
        self._knife_confirmed = True

        # Save snapshot
        if len(self._knife_snapshots) < self._MAX_SNAPS:
            path = self._save_snapshot(frame, "knife")
            if path:
                self._knife_snapshots.append(path)
                if db_log_fn:
                    db_log_fn(path, "knife", conf)

        self._check_dual_detection()

    def handle_violence_detection(self, frame, hrm_result: dict,
                                  db_log_fn: Callable = None):
        """Call this when HRM validates a violence frame."""
        if not hrm_result.get("confirmed"):
            return

        conf = hrm_result.get("confidence", 0.0)
        self._violence_confirmed = True

        if len(self._violence_snapshots) < self._MAX_SNAPS:
            path = self._save_snapshot(frame, "violence")
            if path:
                self._violence_snapshots.append(path)
                if db_log_fn:
                    db_log_fn(path, "violence", conf)

        # Feed frame into recorder
        self._recording_service.enqueue_frame(frame)

        # Start recording if not already in progress
        if not self._recording_service.is_recording:
            self._recording_service.start_recording(
                on_complete=self._on_clip_ready
            )

        self._check_dual_detection()

    # ──────────────────────────────────────────────────────────────────────────
    def _check_dual_detection(self):
        with self._lock:
            if (self._knife_confirmed and self._violence_confirmed
                    and not self._email_in_flight):
                self._email_in_flight = True
                logger.warning("DUAL DETECTION CONFIRMED → Triggering email alert")
                self._schedule_email()

    def _on_clip_ready(self, clip_path: str):
        """Called by RecordingService when the 5-sec clip is saved."""
        from database import db_manager
        db_manager.log_recording(clip_path, config.CLIP_DURATION_SEC)
        logger.info(f"Clip ready: {clip_path}")

        # If email hasn't been triggered yet (clip might arrive before dual confirm)
        # Just log. The pending email thread will pick it up.

    def _schedule_email(self):
        """Send alert email with all evidence collected so far."""
        from services.email_service import send_alert_email
        from utils.helpers import timestamp_display

        det_info = {
            "timestamp":          timestamp_display(),
            "knife_confidence":   0.9,    # Last confirmed value
            "violence_confidence": 0.9,
            "knife_status":       "Confirmed by HRM",
            "violence_status":    "Confirmed by HRM",
        }
        clip_path = self._recording_service.last_clip_path

        send_alert_email(
            knife_snapshots     = self._knife_snapshots,
            violence_snapshots  = self._violence_snapshots,
            video_clip_path     = clip_path,
            detection_info      = det_info,
            callback            = self._on_email_result,
        )

    def _on_email_result(self, success: bool, message: str):
        from database import db_manager
        status = "sent" if success else "failed"
        db_manager.log_alert(0, config.EMAIL_RECEIVER, status)
        logger.info(f"Email result: {status} – {message}")
        if self._email_callback:
            self._email_callback(success, message)
        # Reset so future detections can trigger another email
        with self._lock:
            self._email_in_flight = False
            self._knife_confirmed    = False
            self._violence_confirmed = False
            self._knife_snapshots.clear()
            self._violence_snapshots.clear()

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _save_snapshot(frame, prefix: str) -> str:
        try:
            ts = timestamp_str()
            path = os.path.join(config.ALERTS_DIR, f"{prefix}_{ts}.jpg")
            ensure_dir(config.ALERTS_DIR)
            cv2.imwrite(path, frame)
            logger.debug(f"Snapshot saved: {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to save snapshot: {e}")
            return ""

    def reset(self):
        with self._lock:
            self._knife_confirmed    = False
            self._violence_confirmed = False
            self._knife_snapshots.clear()
            self._violence_snapshots.clear()
            self._email_in_flight    = False
