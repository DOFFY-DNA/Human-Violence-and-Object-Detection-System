"""
tests/run_all_tests.py - Master Test Runner
========================================================================
Runs all 10 test modules, prints coloured terminal output, and shows a
final summary table with pass-rate per module and overall.

Usage:
    python tests/run_all_tests.py
========================================================================
"""
import sys, os, unittest, time, io

# ── Force UTF-8 output on Windows ────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                   errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                   errors="replace", line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── ANSI colour codes (Windows 10+ / macOS / Linux) ──────────────────────────
try:
    os.system("")  # Enable ANSI on Windows
except Exception:
    pass

GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"
WHITE   = "\033[97m"
MAGENTA = "\033[95m"

# ── Module registry ──────────────────────────────────────────────────────────
MODULES = [
    ("Login",               "tests.test_login",               "TestLogin"),
    ("Registration",        "tests.test_registration",        "TestRegistration"),
    ("Database",            "tests.test_database",            "TestDatabase"),
    ("Camera",              "tests.test_camera",              "TestCamera"),
    ("Knife Detection",     "tests.test_knife_detection",     "TestKnifeDetection"),
    ("Violence Detection",  "tests.test_violence_detection",  "TestViolenceDetection"),
    ("Email Service",       "tests.test_email",               "TestEmail"),
    ("Recording Service",   "tests.test_recording",           "TestRecording"),
    ("GUI / Dashboard",     "tests.test_gui",                 "TestGUI"),
    ("Speed Profiler",      "tests.test_profiler",            "TestProfiler"),
]


# ── Custom test result collector ─────────────────────────────────────────────
class _ColorResult(unittest.TestResult):
    """Collects results and prints each test with colour + TC-ID."""

    def __init__(self, module_label, stream=sys.stdout):
        super().__init__()
        self.stream = stream
        self.module_label = module_label
        self.test_details = []
        self._t0 = None

    def startTest(self, test):
        super().startTest(test)
        self._t0 = time.perf_counter()

    def _extract_tc_id(self, test):
        """Extract TC-ID from method name like test_TCL01_xxx -> TC-L01"""
        name = test._testMethodName
        parts = name.split("_")
        if len(parts) >= 2:
            raw = parts[1]  # e.g. "TCL01"
            if len(raw) >= 4 and raw.startswith("TC"):
                prefix = raw[:2]        # TC
                letter = raw[2:-2]      # L / R / D / C / K / V / E / RC / G / P
                number = raw[-2:]       # 01
                return f"{prefix}-{letter}{number}"
        return name

    def _finish(self, test, status_label, color):
        elapsed = (time.perf_counter() - self._t0) * 1000
        tc_id = self._extract_tc_id(test)
        desc = test.shortDescription() or test._testMethodName
        self.test_details.append((tc_id, desc, status_label, elapsed))

        line = (f"  {DIM}[{RESET}{color}{tc_id:<8}{RESET}{DIM}]{RESET}  "
                f"{desc[:58]:<58}  "
                f"{color}{status_label}{RESET}"
                f"  {DIM}({elapsed:.0f}ms){RESET}")
        self.stream.write(line + "\n")
        self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self._finish(test, "PASS", GREEN)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._finish(test, "FAIL", RED)

    def addError(self, test, err):
        super().addError(test, err)
        # Print the traceback for debugging
        self.stream.write(f"{RED}    ERROR: {err[1]}{RESET}\n")
        self._finish(test, "FAIL", RED)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        elapsed = (time.perf_counter() - self._t0) * 1000
        tc_id = self._extract_tc_id(test)
        desc = test.shortDescription() or test._testMethodName
        self.test_details.append((tc_id, desc, "SKIP", elapsed))
        line = (f"  {DIM}[{RESET}{YELLOW}{tc_id:<8}{RESET}{DIM}]{RESET}  "
                f"{desc[:58]:<58}  "
                f"{YELLOW}SKIP{RESET}"
                f"  {DIM}({reason}){RESET}")
        self.stream.write(line + "\n")
        self.stream.flush()


# ── Run all modules ──────────────────────────────────────────────────────────
def run_all():
    overall_start = time.perf_counter()
    summary = []

    print()
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}   AI SURVEILLANCE SYSTEM -- TEST REPORT{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print()

    total_all = 0
    pass_all  = 0
    fail_all  = 0
    skip_all  = 0

    for module_label, module_path, class_name in MODULES:
        print(f"{BOLD}{MAGENTA}-- Module: {module_label} --{RESET}")
        try:
            mod = __import__(module_path, fromlist=[class_name])
            test_class = getattr(mod, class_name)
        except Exception as e:
            print(f"  {RED}ERROR: Could not import {module_path}: {e}{RESET}\n")
            summary.append((module_label, 0, 0, 1, 0))
            fail_all += 1
            total_all += 1
            continue

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)

        result = _ColorResult(module_label)
        suite.run(result)

        passed  = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
        failed  = len(result.failures) + len(result.errors)
        skipped = len(result.skipped)
        total   = result.testsRun

        summary.append((module_label, total, passed, failed, skipped))
        total_all += total
        pass_all  += passed
        fail_all  += failed
        skip_all  += skipped

        print()

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}   SUMMARY{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print()

    hdr = (f"  {BOLD}{'Module':<25}  {'Total':>5}  {'Pass':>5}  "
           f"{'Fail':>5}  {'Skip':>5}  {'Rate':>7}{RESET}")
    print(hdr)
    print(f"  {'-' * 65}")

    for name, total, passed, failed, skipped in summary:
        rate = (passed / total * 100) if total > 0 else 0
        if rate == 100:
            rc = GREEN
        elif rate >= 80:
            rc = YELLOW
        else:
            rc = RED

        fc = RED if failed > 0 else GREEN
        sc = YELLOW if skipped > 0 else DIM

        print(
            f"  {WHITE}{name:<25}{RESET}  "
            f"{total:>5}  "
            f"{GREEN}{passed:>5}{RESET}  "
            f"{fc}{failed:>5}{RESET}  "
            f"{sc}{skipped:>5}{RESET}  "
            f"{rc}{rate:>6.1f}%{RESET}"
        )

    print(f"  {'-' * 65}")

    overall_rate = (pass_all / total_all * 100) if total_all > 0 else 0
    overall_color = GREEN if overall_rate == 100 else (YELLOW if overall_rate >= 80 else RED)

    print(
        f"  {BOLD}{'OVERALL':<25}{RESET}  "
        f"{total_all:>5}  "
        f"{GREEN}{pass_all:>5}{RESET}  "
        f"{RED if fail_all else GREEN}{fail_all:>5}{RESET}  "
        f"{YELLOW if skip_all else DIM}{skip_all:>5}{RESET}  "
        f"{overall_color}{BOLD}{overall_rate:>6.1f}%{RESET}"
    )

    elapsed_total = time.perf_counter() - overall_start
    print()
    print(f"  {DIM}Total time: {elapsed_total:.2f}s{RESET}")
    print()

    if fail_all == 0:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED!{RESET}")
    else:
        print(f"  {RED}{BOLD}{fail_all} TEST(S) FAILED -- see details above.{RESET}")

    print()
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")
    print()

    return fail_all == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
