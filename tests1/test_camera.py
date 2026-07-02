"""
tests/test_camera.py
Tests for webcam availability and frame capture.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import cv2
import numpy as np
import config


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_camera_opens():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    opened = cap.isOpened()
    cap.release()
    assert opened, f"Camera index {config.CAMERA_INDEX} could not be opened"

def test_camera_frame_read():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    assert cap.isOpened(), "Camera not available"
    ret, frame = cap.read()
    cap.release()
    assert ret, "cap.read() returned False"
    assert frame is not None, "Frame is None"

def test_camera_frame_shape():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        pytest.skip("Camera not available")
    ret, frame = cap.read()
    cap.release()
    assert ret
    assert len(frame.shape) == 3, "Frame must be 3-dimensional (H, W, C)"
    h, w, c = frame.shape
    assert c == 3,   "Frame must have 3 channels (BGR)"
    assert w  > 0,   "Width must be > 0"
    assert h  > 0,   "Height must be > 0"

def test_camera_frame_not_blank():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        pytest.skip("Camera not available")
    ret, frame = cap.read()
    cap.release()
    assert ret
    mean_val = np.mean(frame)
    assert mean_val > 1.0, "Frame appears to be completely black"

def test_camera_multiple_frames():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        pytest.skip("Camera not available")
    read_count = 0
    for _ in range(10):
        ret, frame = cap.read()
        if ret:
            read_count += 1
    cap.release()
    assert read_count >= 5, f"Only {read_count}/10 frames captured"

def test_camera_fps_resolution():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        pytest.skip("Camera not available")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()
    assert w == 640, f"Expected width 640, got {w}"
    assert h == 480, f"Expected height 480, got {h}"

def test_camera_read_speed():
    """First real frames (after warmup) must be read in < 500ms."""
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        pytest.skip("Camera not available")
    # Warm-up: discard first 5 frames (camera init is always slow)
    for _ in range(5):
        cap.read()
    # Now time a real frame
    t0 = time.perf_counter()
    ret, frame = cap.read()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    cap.release()
    assert ret
    assert elapsed_ms < 500, f"Camera read too slow after warmup: {elapsed_ms:.1f}ms"


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    tests = [
        ("Camera Opens",           test_camera_opens),
        ("Camera Frame Read",      test_camera_frame_read),
        ("Camera Frame Shape",     test_camera_frame_shape),
        ("Camera Frame Not Blank", test_camera_frame_not_blank),
        ("Camera Multi Frames",    test_camera_multiple_frames),
        ("Camera FPS/Resolution",  test_camera_fps_resolution),
        ("Camera Read Speed",      test_camera_read_speed),
    ]
    results = []
    for name, fn in tests:
        t0 = time.perf_counter()
        try:
            fn()
            status = "PASS"
        except pytest.skip.Exception as e:
            status = f"SKIP: {e}"
        except Exception as e:
            status = f"FAIL: {e}"
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        results.append((name, status, elapsed))
    return results


if __name__ == "__main__":
    for name, status, ms in run_tests():
        print(f"[{status}] {name} ({ms}ms)")
