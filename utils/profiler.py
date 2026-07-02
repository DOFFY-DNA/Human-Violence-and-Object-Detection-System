"""
utils/profiler.py – Lightweight Speed Profiler for AI Surveillance System.

Usage:
    from utils.profiler import profiler

    with profiler.measure("knife_inference"):
        res = model.predict(frame)

    report = profiler.report()   # → dict of stats
"""
import time
import threading
from collections import defaultdict


class SpeedProfiler:
    """
    Thread-safe speed profiler.
    Tracks min / max / avg / last / count for each named operation.
    """

    def __init__(self):
        self._lock   = threading.Lock()
        self._totals = defaultdict(float)  # name → total seconds
        self._counts = defaultdict(int)    # name → call count
        self._mins   = {}                  # name → min seconds
        self._maxs   = {}                  # name → max seconds
        self._lasts  = {}                  # name → last seconds
        self._start_times = {}             # for context manager

    # ──────────────────────────────────────────────────────────────────────────
    class _Timer:
        """Context manager returned by profiler.measure()."""
        def __init__(self, profiler, name):
            self._p    = profiler
            self._name = name
            self._t0   = None

        def __enter__(self):
            self._t0 = time.perf_counter()
            return self

        def __exit__(self, *_):
            elapsed = time.perf_counter() - self._t0
            self._p._record(self._name, elapsed)

    def measure(self, name: str) -> "_Timer":
        """Use as:  with profiler.measure('step_name'): ..."""
        return self._Timer(self, name)

    # ──────────────────────────────────────────────────────────────────────────
    def _record(self, name: str, elapsed: float):
        with self._lock:
            self._totals[name] += elapsed
            self._counts[name] += 1
            self._lasts[name]   = elapsed
            if name not in self._mins or elapsed < self._mins[name]:
                self._mins[name] = elapsed
            if name not in self._maxs or elapsed > self._maxs[name]:
                self._maxs[name] = elapsed

    # ──────────────────────────────────────────────────────────────────────────
    def report(self) -> dict:
        """
        Returns a dict:
          { name: {avg_ms, min_ms, max_ms, last_ms, count} }
        """
        result = {}
        with self._lock:
            for name in self._counts:
                count = self._counts[name]
                avg   = (self._totals[name] / count) * 1000   # → ms
                result[name] = {
                    "avg_ms":  round(avg,                        2),
                    "min_ms":  round(self._mins[name]  * 1000,  2),
                    "max_ms":  round(self._maxs[name]  * 1000,  2),
                    "last_ms": round(self._lasts[name] * 1000,  2),
                    "count":   count,
                }
        return result

    def reset(self):
        """Clear all recorded data."""
        with self._lock:
            self._totals.clear()
            self._counts.clear()
            self._mins.clear()
            self._maxs.clear()
            self._lasts.clear()

    def summary_lines(self) -> list:
        """Returns list of formatted strings for display."""
        rep   = self.report()
        lines = []
        order = [
            "camera_read",
            "knife_inference",
            "violence_inference",
            "snapshot_save",
            "gui_render",
        ]
        # Show ordered first, then any extra keys
        shown = set()
        for key in order:
            if key in rep:
                lines.append(_fmt(key, rep[key]))
                shown.add(key)
        for key, val in rep.items():
            if key not in shown:
                lines.append(_fmt(key, val))
        return lines


def _fmt(name: str, d: dict) -> str:
    label = name.replace("_", " ").title()
    return (f"{label:<22}  "
            f"avg={d['avg_ms']:7.2f}ms  "
            f"min={d['min_ms']:7.2f}ms  "
            f"max={d['max_ms']:7.2f}ms  "
            f"calls={d['count']}")


# ── Singleton ─────────────────────────────────────────────────────────────────
profiler = SpeedProfiler()
