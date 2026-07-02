"""
tests/test_profiler.py — Module 10: Speed Profiler
Test IDs: TC-P01 to TC-P05
Tests the SpeedProfiler directly — no mocking needed.
"""
import sys, os, unittest, time, threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.profiler import SpeedProfiler


class TestProfiler(unittest.TestCase):
    """Module 10 — Speed Profiler (5 tests)"""

    def setUp(self):
        """Fresh profiler for each test."""
        self.profiler = SpeedProfiler()

    # ── TC-P01 ────────────────────────────────────────────────────────────────
    def test_TCP01_profiler_records_timing_correctly(self):
        """Profiler should record approximately correct timing"""
        with self.profiler.measure("test_op"):
            time.sleep(0.1)
        report = self.profiler.report()
        self.assertIn("test_op", report)
        # Should be roughly 100ms (allow 50-300ms for CI variance)
        self.assertGreater(report["test_op"]["avg_ms"], 50)
        self.assertLess(report["test_op"]["avg_ms"], 300)
        self.assertEqual(report["test_op"]["count"], 1)

    # ── TC-P02 ────────────────────────────────────────────────────────────────
    def test_TCP02_profiler_tracks_min_max_avg(self):
        """After 3 runs, min <= avg <= max should hold"""
        for delay in [0.01, 0.05, 0.03]:
            with self.profiler.measure("multi"):
                time.sleep(delay)

        report = self.profiler.report()
        stats = report["multi"]
        self.assertEqual(stats["count"], 3)
        self.assertLessEqual(stats["min_ms"], stats["avg_ms"])
        self.assertLessEqual(stats["avg_ms"], stats["max_ms"])

    # ── TC-P03 ────────────────────────────────────────────────────────────────
    def test_TCP03_profiler_reset_clears_data(self):
        """reset() should clear all recorded data"""
        with self.profiler.measure("something"):
            time.sleep(0.01)
        self.assertIn("something", self.profiler.report())

        self.profiler.reset()
        report = self.profiler.report()
        self.assertEqual(len(report), 0)

    # ── TC-P04 ────────────────────────────────────────────────────────────────
    def test_TCP04_profiler_thread_safe(self):
        """5 threads measuring simultaneously should all be recorded"""
        errors = []

        def _measure(thread_id):
            try:
                with self.profiler.measure("concurrent"):
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_measure, args=(i,))
                   for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        report = self.profiler.report()
        self.assertEqual(report["concurrent"]["count"], 5)

    # ── TC-P05 ────────────────────────────────────────────────────────────────
    def test_TCP05_summary_lines_formatted(self):
        """summary_lines() should return formatted strings"""
        with self.profiler.measure("camera_read"):
            time.sleep(0.01)
        with self.profiler.measure("knife_inference"):
            time.sleep(0.01)

        lines = self.profiler.summary_lines()
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)
        # Each line should contain 'avg=' and 'calls='
        for line in lines:
            self.assertIn("avg=", line)
            self.assertIn("calls=", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
