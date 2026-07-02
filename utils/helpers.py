"""utils/helpers.py – Frame conversion, timestamp, directory utilities."""
import cv2
import numpy as np
from PIL import Image, ImageTk
import datetime
import os


def cv2_to_imagetk(frame: np.ndarray, width: int, height: int) -> ImageTk.PhotoImage:
    """Convert a BGR OpenCV frame to a Tkinter-compatible PhotoImage."""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    img = img.resize((width, height), Image.LANCZOS)
    return ImageTk.PhotoImage(image=img)


def timestamp_str(fmt: str = "%Y%m%d_%H%M%S") -> str:
    return datetime.datetime.now().strftime(fmt)


def timestamp_display() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def draw_box(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int,
             label: str, conf: float, color=(0, 0, 255)) -> np.ndarray:
    """Draw a bounding box with label and confidence on a frame."""
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text = f"{label} {conf:.0%}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, text, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame


def draw_label(frame: np.ndarray, text: str, org=(10, 30),
               color=(0, 0, 255), scale=0.8, thickness=2) -> np.ndarray:
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)
    return frame


def blank_frame(width: int = 640, height: int = 480, text: str = "") -> np.ndarray:
    """Return a dark placeholder frame with optional centred text."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (26, 26, 46)
    if text:
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x = (width - tw) // 2
        y = (height + th) // 2
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (100, 100, 150), 2)
    return frame


def iou(boxA, boxB) -> float:
    """Intersection-over-Union of two (x1, y1, x2, y2) boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0:
        return 0.0
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter / float(areaA + areaB - inter)
