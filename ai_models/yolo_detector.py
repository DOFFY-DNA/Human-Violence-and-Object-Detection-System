"""
ai_models/yolo_detector.py
Knife detection using YOLOv11 (ultralytics).
Loads models/best.pt and returns annotated frames with bounding boxes.
"""
import os
import sys
import cv2
import numpy as np
import threading
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import draw_box, draw_label

logger = get_logger("yolo_detector")

_TEMP_MODEL_DIR: str = ""   # set once on first load


def _safe_model_copy(src_path: str) -> str:
    """
    Copy the model file to a temp directory whose path contains no apostrophes.
    ultralytics internally runs the weight path through shlex.split(), which
    treats the apostrophe in 'Agents On Test's' as a shell string delimiter
    and corrupts the path.  Copying to a safe temp path avoids this entirely.
    Python's own shutil.copy2 / open() handle the apostrophe correctly.
    """
    global _TEMP_MODEL_DIR
    if not _TEMP_MODEL_DIR:
        _TEMP_MODEL_DIR = tempfile.mkdtemp(prefix="surveillance_models_")
    dst = os.path.join(_TEMP_MODEL_DIR, os.path.basename(src_path))
    if not os.path.exists(dst):
        logger.info(f"Copying model to safe temp path: {dst}")
        shutil.copy2(src_path, dst)
    return dst


class YOLODetector:
    """
    Wraps the YOLOv11 model for real-time knife detection.
    Thread-safe: one instance shared across threads via a lock.
    """

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()
        self._loaded = False
        self.device = "cuda" if self._cuda_available() else "cpu"
        logger.info(f"YOLODetector will use device: {self.device}")

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load(self):
        """Load the YOLO model. Call once before detection loop."""
        if self._loaded:
            return
        try:
            from ultralytics import YOLO
            # Copy to apostrophe-free temp path before handing to ultralytics
            safe_path = _safe_model_copy(config.YOLO_MODEL)
            logger.info(f"Loading YOLO model from safe path: {safe_path}")
            self._model = YOLO(safe_path)
            self._model.to(self.device)
            self._loaded = True
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}", exc_info=True)
            raise


    def detect(self, frame: np.ndarray) -> dict:
        """
        Run knife detection on a single BGR frame.
        Returns:
            {
              'annotated_frame': np.ndarray,
              'detections': [{'label': str, 'confidence': float, 'bbox': (x1,y1,x2,y2)}],
              'knife_detected': bool,
              'max_confidence': float
            }
        """
        result = {
            "annotated_frame": frame.copy(),
            "detections": [],
            "knife_detected": False,
            "max_confidence": 0.0,
        }
        if not self._loaded or self._model is None:
            draw_label(result["annotated_frame"], "Model not loaded", (10, 30), (0, 0, 255))
            return result

        annotated = frame.copy()
        try:
            with self._lock:
                results = self._model.predict(
                    frame,
                    conf=config.YOLO_CONF_THRESHOLD,
                    device=self.device,
                    verbose=False,
                )
        except Exception as e:
            logger.warning(f"YOLO inference error: {e}")
            return result

        max_conf = 0.0
        for res in results:
            if res.boxes is None:
                continue
            for box in res.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                label  = res.names.get(cls_id, str(cls_id))

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                color = (0, 0, 255)  # Red for threat
                draw_box(annotated, x1, y1, x2, y2, label, conf, color)

                result["detections"].append({
                    "label": label,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                })
                if conf > max_conf:
                    max_conf = conf

        result["knife_detected"] = len(result["detections"]) > 0
        result["max_confidence"] = max_conf
        result["annotated_frame"] = annotated

        # Overlay status text
        if result["knife_detected"]:
            status_text = f"THREAT: KNIFE {max_conf:.0%}"
            draw_label(annotated, status_text, (10, 30), (0, 0, 255), 0.8, 2)
        else:
            draw_label(annotated, "Safe – No Knife", (10, 30), (0, 200, 0), 0.8, 2)

        return result
