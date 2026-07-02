"""
ai_models/violence_detector.py
Violence detection using a fine-tuned ResNet-18 model.
The model was trained on the RWF-2000 dataset.
Supports both full-model saves (torch.save(model,...)) and state_dict saves.
"""
import os
import sys
import io
import cv2
import numpy as np
import threading
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import draw_label

logger = get_logger("violence_detector")


class ViolenceDetector:
    """
    Processes a rolling window of frames and classifies as Violence / Non Violence.
    Uses a fine-tuned ResNet-18 with a binary head.
    """

    LABELS = ["Non Violence", "Violence"]

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()
        self._loaded = False
        self._frame_buffer: deque = deque(maxlen=config.VIOLENCE_WINDOW_FRAMES)
        self.device = self._get_device()
        self._transform = None
        logger.info(f"ViolenceDetector will use device: {self.device}")

    @staticmethod
    def _get_device():
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _build_model(self):
        """Build ResNet-18 with binary output head."""
        import torch.nn as nn
        from torchvision import models
        model = models.resnet18(weights=None)
        model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(model.fc.in_features, 2),
        )
        return model

    def load(self):
        """Load the violence model. Call once before the detection loop."""
        if self._loaded:
            return
        import torch
        from torchvision import transforms

        try:
            logger.info(f"Loading violence model from: {config.VIOLENCE_MODEL}")
            # ── Key fix ──────────────────────────────────────────────────────
            # Python's built-in open() handles the apostrophe in the directory
            # name correctly. We read the entire .pth file into a BytesIO buffer
            # and pass THAT to torch.load. torch.load accepts any file-like
            # object and never touches the original path string, so ultralytics'
            # shlex.split() path-mangling is completely bypassed.
            with open(config.VIOLENCE_MODEL, "rb") as f:
                buf = io.BytesIO(f.read())
            checkpoint = torch.load(
                buf,
                map_location=torch.device(self.device),
                weights_only=False,
            )

            # Support both full-model save and state_dict save
            if isinstance(checkpoint, dict):
                # state_dict save
                model = self._build_model()
                # Sometimes saved with 'model_state_dict' or 'state_dict' key
                state = (checkpoint.get("model_state_dict")
                         or checkpoint.get("state_dict")
                         or checkpoint)
                model.load_state_dict(state, strict=False)
            else:
                # Full model save
                model = checkpoint

            model.to(self.device)
            model.eval()
            self._model = model
            self._loaded = True

            self._transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])
            logger.info("Violence model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load violence model: {e}", exc_info=True)
            raise

    def add_frame(self, frame: np.ndarray):
        """Push a BGR frame into the rolling buffer."""
        self._frame_buffer.append(frame)

    def predict(self, frame: np.ndarray = None) -> dict:
        """
        Run violence prediction on the current frame buffer (+ optional new frame).
        Returns:
            {
              'label': 'Violence' | 'Non Violence',
              'confidence': float,
              'violence_detected': bool,
              'annotated_frame': np.ndarray  (the last frame, annotated)
            }
        """
        if frame is not None:
            self.add_frame(frame)

        last_frame = frame if frame is not None else (
            self._frame_buffer[-1] if self._frame_buffer else None
        )
        annotated = last_frame.copy() if last_frame is not None else \
            np.zeros((480, 640, 3), dtype=np.uint8)

        result = {
            "label": "Non Violence",
            "confidence": 0.0,
            "violence_detected": False,
            "annotated_frame": annotated,
        }

        if not self._loaded or self._model is None:
            draw_label(annotated, "Model not loaded", (10, 30), (0, 0, 255))
            return result

        if len(self._frame_buffer) < 4:
            draw_label(annotated, "Buffering frames...", (10, 30), (200, 200, 0))
            return result

        import torch
        import torch.nn.functional as F

        try:
            # Use up to VIOLENCE_WINDOW_FRAMES frames; always use the most recent
            frames_to_use = list(self._frame_buffer)
            tensors = [self._transform(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
                       for f in frames_to_use]

            # Average-pool over frames for temporal representation
            batch = torch.stack(tensors).to(self.device)  # (N, 3, 224, 224)

            with self._lock:
                with torch.no_grad():
                    # Pass each frame through the model, average logits
                    logits = self._model(batch)           # (N, 2)
                    avg_logit = logits.mean(dim=0, keepdim=True)  # (1, 2)
                    probs = F.softmax(avg_logit, dim=1)

            confidence = float(probs[0][1])  # Index 1 = Violence
            label_idx  = 1 if confidence >= config.VIOLENCE_CONF_THRESHOLD else 0
            label      = self.LABELS[label_idx]

            result["label"]              = label
            result["confidence"]         = confidence if label_idx == 1 else 1.0 - confidence
            result["violence_detected"]  = label_idx == 1

            # Annotate the last frame
            color = (0, 0, 255) if label_idx == 1 else (0, 200, 0)
            display_conf = confidence if label_idx == 1 else 1.0 - confidence
            text = f"{label}  {display_conf:.0%}"
            draw_label(annotated, text, (10, 30), color, 0.9, 2)

            # Draw a full-frame border when violence detected
            if label_idx == 1:
                h, w = annotated.shape[:2]
                cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), (0, 0, 255), 4)

            result["annotated_frame"] = annotated

        except Exception as e:
            logger.warning(f"Violence inference error: {e}")

        return result

    def reset_buffer(self):
        self._frame_buffer.clear()
