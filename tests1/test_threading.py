"""
tests/test_threading.py
Tests for multi-threading safety: shared state, race conditions, load.
"""
import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from utils.profiler import SpeedProfiler


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_profiler_thread_safety():
    """Multiple threads writing to profiler simultaneously should not crash."""
    p = SpeedProfiler()
    errors = []

    def _worker(name):
        for _ in range(100):
            with p.measure(name):
                time.sleep(0.0001)

    threads = [threading.Thread(target=_worker, args=(f"op_{i}",))
               for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert not errors
    report = p.report()
    assert len(report) == 5

def test_shared_frame_buffer():
    """Simulate camera thread writing + detection thread reading shared frame."""
    shared = {"frame": None}
    lock   = threading.Lock()
    read_results = []

    def _writer():
        for i in range(50):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = i
            with lock:
                shared["frame"] = frame
            time.sleep(0.005)

    def _reader():
        for _ in range(50):
            with lock:
                f = shared["frame"]
            if f is not None:
                read_results.append(f.shape)
            time.sleep(0.005)

    w = threading.Thread(target=_writer)
    r = threading.Thread(target=_reader)
    w.start(); r.start()
    w.join();  r.join()

    assert len(read_results) > 0
    for shape in read_results:
        assert shape == (480, 640, 3)

def test_concurrent_db_writes():
    """Multiple threads writing to DB simultaneously should not crash."""
    from database import db_manager
    errors = []

    def _write(i):
        try:
            db_manager.log_detection("knife", f"test_{i}", 0.5 + i*0.01,
                                     status="thread_test")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(errors) == 0, f"DB thread errors: {errors}"

def test_thread_termination():
    """A daemon thread must stop when its flag is False."""
    running = {"v": True}
    results = []

    def _task():
        while running["v"]:
            results.append(1)
            time.sleep(0.01)

    t = threading.Thread(target=_task, daemon=True)
    t.start()
    time.sleep(0.1)
    running["v"] = False
    t.join(timeout=0.5)
    assert not t.is_alive(), "Thread did not terminate"
    assert len(results) > 0

def test_multiple_threads_no_crash():
    """Run 3 threads doing heavy numpy work in parallel — no crash."""
    errors = []

    def _heavy(tid):
        try:
            for _ in range(20):
                arr = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                _ = np.mean(arr)
        except Exception as e:
            errors.append(f"Thread {tid}: {e}")

    threads = [threading.Thread(target=_heavy, args=(i,)) for i in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"Thread errors: {errors}"

def test_alert_cooldown_thread_safety():
    """Simulate concurrent _trigger_alert calls — only one should fire."""
    lock    = threading.Lock()
    cooldown= {}
    fired   = []

    def _trigger(det_type):
        now = time.time()
        with lock:
            if now - cooldown.get(det_type, 0) < 60:
                return
            cooldown[det_type] = now
        fired.append(det_type)

    threads = [threading.Thread(target=_trigger, args=("knife",))
               for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(fired) == 1, f"Cooldown fired {len(fired)} times instead of 1"


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    tests = [
        ("Profiler Thread Safety",       test_profiler_thread_safety),
        ("Shared Frame Buffer",          test_shared_frame_buffer),
        ("Concurrent DB Writes",         test_concurrent_db_writes),
        ("Thread Termination",           test_thread_termination),
        ("Multi Thread No Crash",        test_multiple_threads_no_crash),
        ("Alert Cooldown Thread Safety", test_alert_cooldown_thread_safety),
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


if __name__ == "__main__":
    for name, status, ms in run_tests():
        print(f"[{status}] {name} ({ms}ms)")
