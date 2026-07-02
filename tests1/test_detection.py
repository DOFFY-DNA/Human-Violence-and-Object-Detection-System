"""
tests/test_detection.py
Tests for YOLO inference (knife + violence), confidence, output shape, and speed.
Uses pytest-benchmark for performance measurement.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import cv2
import config
import shutil, tempfile

KNIFE_MODEL_PATH    = os.path.join(config.BASE_DIR, "models", "best.pt")
VIOLENCE_MODEL_PATH = os.path.join(config.BASE_DIR, "models", "best2.pt")
KNIFE_CONF          = 0.45
VIOLENCE_CONF       = 0.40

# ── Safe path helper (apostrophe in project path breaks ultralytics) ───────────
_TEMP_MODEL_DIR = ""
def _safe_model_path(src: str) -> str:
    """Copy model to a tmp dir without special chars so ultralytics loads happily."""
    global _TEMP_MODEL_DIR
    if not _TEMP_MODEL_DIR:
        _TEMP_MODEL_DIR = tempfile.mkdtemp(prefix="surv_test_")
    dst = os.path.join(_TEMP_MODEL_DIR, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return dst

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def knife_model():
    if not os.path.exists(KNIFE_MODEL_PATH):
        pytest.skip("best.pt not found")
    from ultralytics import YOLO
    return YOLO(_safe_model_path(KNIFE_MODEL_PATH))

@pytest.fixture(scope="module")
def violence_model():
    if not os.path.exists(VIOLENCE_MODEL_PATH):
        pytest.skip("best2.pt not found")
    from ultralytics import YOLO
    return YOLO(_safe_model_path(VIOLENCE_MODEL_PATH))

@pytest.fixture(scope="module")
def blank_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)

@pytest.fixture(scope="module")
def noise_frame():
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_knife_model_loads(knife_model):
    assert knife_model is not None

def test_violence_model_loads(violence_model):
    assert violence_model is not None

def test_knife_model_predict_returns_result(knife_model, blank_frame):
    res = knife_model.predict(blank_frame, conf=KNIFE_CONF, verbose=False)
    assert res is not None
    assert len(res) > 0

def test_violence_model_predict_returns_result(violence_model, blank_frame):
    res = violence_model.predict(blank_frame, conf=VIOLENCE_CONF, verbose=False)
    assert res is not None
    assert len(res) > 0

def test_knife_model_boxes_accessible(knife_model, blank_frame):
    res   = knife_model.predict(blank_frame, conf=KNIFE_CONF, verbose=False)
    boxes = res[0].boxes
    assert boxes is not None   # boxes object always exists (may be empty)

def test_violence_model_boxes_accessible(violence_model, blank_frame):
    res   = violence_model.predict(blank_frame, conf=VIOLENCE_CONF, verbose=False)
    boxes = res[0].boxes
    assert boxes is not None

def test_knife_inference_speed(knife_model, noise_frame):
    """Knife inference on GPU should complete in < 500ms (after warmup)."""
    # Warm-up call so GPU is initialized
    knife_model.predict(noise_frame, conf=KNIFE_CONF, verbose=False)
    # Timed call
    t0 = time.perf_counter()
    knife_model.predict(noise_frame, conf=KNIFE_CONF, verbose=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"Knife inference too slow: {elapsed_ms:.1f}ms"

def test_violence_inference_speed(violence_model, noise_frame):
    """Violence inference should complete in < 500ms (after warmup)."""
    violence_model.predict(noise_frame, conf=VIOLENCE_CONF, verbose=False)
    t0 = time.perf_counter()
    violence_model.predict(noise_frame, conf=VIOLENCE_CONF, verbose=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"Violence inference too slow: {elapsed_ms:.1f}ms"

def test_knife_model_has_class_names(knife_model):
    assert hasattr(knife_model, "names")
    assert isinstance(knife_model.names, dict)
    assert len(knife_model.names) > 0

def test_violence_model_has_class_names(violence_model):
    assert hasattr(violence_model, "names")
    assert isinstance(violence_model.names, dict)
    assert len(violence_model.names) > 0

# pytest-benchmark test
def test_knife_benchmark(benchmark, knife_model, noise_frame):
    result = benchmark(knife_model.predict, noise_frame, conf=KNIFE_CONF, verbose=False)
    assert result is not None

def test_violence_benchmark(benchmark, violence_model, noise_frame):
    result = benchmark(violence_model.predict, noise_frame, conf=VIOLENCE_CONF, verbose=False)
    assert result is not None


# ── Manual runner (no benchmark fixture available) ────────────────────────────
def run_tests() -> list:
    try:
        if not os.path.exists(KNIFE_MODEL_PATH):
            return [("Models Not Found", "SKIP: best.pt missing", 0)]
        if not os.path.exists(VIOLENCE_MODEL_PATH):
            return [("Models Not Found", "SKIP: best2.pt missing", 0)]
        from ultralytics import YOLO
        # Use safe temp paths (no apostrophe in path)
        km = YOLO(_safe_model_path(KNIFE_MODEL_PATH))
        vm = YOLO(_safe_model_path(VIOLENCE_MODEL_PATH))
    except Exception as e:
        return [("Model Load", f"FAIL: {e}", 0)]

    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    noise = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    tests = [
        ("Knife Model Loads",              lambda: assert_true(km is not None)),
        ("Violence Model Loads",           lambda: assert_true(vm is not None)),
        ("Knife Predict Returns Result",   lambda: assert_true(km.predict(blank, conf=KNIFE_CONF, verbose=False) is not None)),
        ("Violence Predict Returns Result",lambda: assert_true(vm.predict(blank, conf=VIOLENCE_CONF, verbose=False) is not None)),
        ("Knife Has Class Names",          lambda: assert_true(len(km.names) > 0)),
        ("Violence Has Class Names",       lambda: assert_true(len(vm.names) > 0)),
        ("Knife Inference Speed <500ms",   lambda: _speed_check(km, noise, KNIFE_CONF, 500)),
        ("Violence Inference Speed <500ms",lambda: _speed_check(vm, noise, VIOLENCE_CONF, 500)),
    ]
    results = []
    for name, fn in tests:
        t0 = time.perf_counter()
        try:
            fn()
            status = "PASS"
        except Exception as e:
            status = f"FAIL: {e}"
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        results.append((name, status, elapsed))
    return results

def assert_true(val):
    if not val:
        raise AssertionError(f"Expected truthy, got {val}")

def _speed_check(model, frame, conf, max_ms):
    t0 = time.perf_counter()
    model.predict(frame, conf=conf, verbose=False)
    ms = (time.perf_counter() - t0) * 1000
    if ms > max_ms:
        raise AssertionError(f"Too slow: {ms:.1f}ms > {max_ms}ms")


if __name__ == "__main__":
    for name, status, ms in run_tests():
        print(f"[{status}] {name} ({ms}ms)")
