"""
ai_models/hrm_validator.py
Hierarchical Reasoning Model (HRM) – reduces false positives for both
knife and violence detections using multi-frame temporal consistency.
"""
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import iou

logger = get_logger("hrm_validator")

KNIFE_CLASSES = {"knife", "knives", "blade", "weapon"}


class HRMValidator:
    """
    Five-stage HRM pipeline:
    1. Confidence threshold check
    2. Object class validation  (knife only for YOLO)
    3. Multi-frame confirmation (N consecutive positive frames)
    4. Temporal consistency     (positive ratio over window)
    5. BBox stability            (IOU across consecutive frames)
    """

    def __init__(self, mode: str = "knife"):
        """
        mode: 'knife' | 'violence'
        """
        assert mode in ("knife", "violence"), "mode must be 'knife' or 'violence'"
        self.mode = mode
        self._n = config.HRM_FRAMES_REQUIRED       # consecutive frames required
        self._iou_threshold = config.HRM_IOU_THRESHOLD

        # Sliding history windows
        self._detection_history: deque = deque(maxlen=self._n * 3)
        self._bbox_history: deque = deque(maxlen=self._n)
        self._confirmed = False

    # ──────────────────────────────────────────────────────────────────────────
    def validate_knife(self, detect_result: dict) -> dict:
        """
        Validate a YOLO knife detection result.
        Returns:
            {
              'confirmed': bool,
              'reason': str,
              'confidence': float,
              'bbox': tuple | None
            }
        """
        output = {"confirmed": False, "reason": "", "confidence": 0.0, "bbox": None}

        detections = detect_result.get("detections", [])
        if not detections:
            self._detection_history.append(False)
            output["reason"] = "No detections in frame"
            self._update_confirmed_state(False)
            return output

        # Stage 1 – Confidence threshold
        best = max(detections, key=lambda d: d["confidence"])
        if best["confidence"] < config.YOLO_CONF_THRESHOLD:
            self._detection_history.append(False)
            output["reason"] = f"Conf {best['confidence']:.2f} < threshold {config.YOLO_CONF_THRESHOLD}"
            self._update_confirmed_state(False)
            return output

        # Stage 2 – Class validation
        if best["label"].lower() not in KNIFE_CLASSES:
            self._detection_history.append(False)
            output["reason"] = f"Class '{best['label']}' is not a knife class"
            self._update_confirmed_state(False)
            return output

        # Stage 3 & 4 – Multi-frame + temporal consistency
        self._detection_history.append(True)
        consecutive = self._count_consecutive_tail()
        ratio = sum(self._detection_history) / len(self._detection_history)

        if consecutive < self._n:
            output["reason"] = f"Only {consecutive}/{self._n} consecutive frames"
            self._update_confirmed_state(False)
            return output

        # Stage 5 – BBox stability
        bbox = best["bbox"]
        if self._bbox_history:
            prev_bbox = self._bbox_history[-1]
            score = iou(bbox, prev_bbox)
            if score < self._iou_threshold:
                self._bbox_history.append(bbox)
                output["reason"] = f"BBox IOU {score:.2f} < {self._iou_threshold} (unstable)"
                self._update_confirmed_state(False)
                return output

        self._bbox_history.append(bbox)
        output["confirmed"]   = True
        output["confidence"]  = best["confidence"]
        output["bbox"]        = bbox
        output["reason"]      = f"HRM confirmed (consecutive={consecutive}, ratio={ratio:.2f})"
        self._update_confirmed_state(True)
        logger.debug(f"[HRM-knife] CONFIRMED – {output['reason']}")
        return output

    # ──────────────────────────────────────────────────────────────────────────
    def validate_violence(self, violence_result: dict) -> dict:
        """
        Validate a violence detection result.
        Returns same structure as validate_knife.
        """
        output = {"confirmed": False, "reason": "", "confidence": 0.0, "bbox": None}

        conf = violence_result.get("confidence", 0.0)
        detected = violence_result.get("violence_detected", False)

        # Stage 1 – Confidence threshold
        if not detected or conf < config.VIOLENCE_CONF_THRESHOLD:
            self._detection_history.append(False)
            output["reason"] = f"Conf {conf:.2f} < threshold or non-violence label"
            self._update_confirmed_state(False)
            return output

        # Stage 3 & 4 – Multi-frame consistency
        self._detection_history.append(True)
        consecutive = self._count_consecutive_tail()
        ratio = sum(self._detection_history) / len(self._detection_history)

        if consecutive < self._n:
            output["reason"] = f"Only {consecutive}/{self._n} consecutive frames"
            self._update_confirmed_state(False)
            return output

        output["confirmed"]  = True
        output["confidence"] = conf
        output["reason"]     = f"HRM confirmed (consecutive={consecutive}, ratio={ratio:.2f})"
        self._update_confirmed_state(True)
        logger.debug(f"[HRM-violence] CONFIRMED – {output['reason']}")
        return output

    # ──────────────────────────────────────────────────────────────────────────
    def _count_consecutive_tail(self) -> int:
        count = 0
        for v in reversed(self._detection_history):
            if v:
                count += 1
            else:
                break
        return count

    def _update_confirmed_state(self, confirmed: bool):
        self._confirmed = confirmed

    @property
    def is_confirmed(self) -> bool:
        return self._confirmed

    def reset(self):
        self._detection_history.clear()
        self._bbox_history.clear()
        self._confirmed = False
