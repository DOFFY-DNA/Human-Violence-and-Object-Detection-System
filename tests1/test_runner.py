"""
tests/test_runner.py
Aggregates and runs all test modules. Logs results to logs/test.log.
Run with:  python tests/test_runner.py
"""
import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# ── Setup test logger ─────────────────────────────────────────────────────────
os.makedirs(config.LOGS_DIR, exist_ok=True)
_log_path = os.path.join(config.LOGS_DIR, "test.log")
logging.basicConfig(
    filename=_log_path,
    filemode="a",
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger("test_runner")


# ── Module registry ───────────────────────────────────────────────────────────
def _get_modules():
    from tests import (
        test_login, test_camera, test_detection,
        test_email, test_database, test_threading, test_gui,
    )
    return [
        ("Login & Auth",    test_login),
        ("Camera",          test_camera),
        ("YOLO Detection",  test_detection),
        ("Email Service",   test_email),
        ("Database",        test_database),
        ("Threading",       test_threading),
        ("GUI",             test_gui),
    ]


# ── Core runner ───────────────────────────────────────────────────────────────
def run_all() -> dict:
    """
    Returns:
      { module_name: [(test_name, status, time_ms), ...] }
    """
    all_results = {}
    _logger.info("=" * 60)
    _logger.info("TEST RUN STARTED")
    _logger.info("=" * 60)

    for mod_name, mod in _get_modules():
        _logger.info(f"\n--- Module: {mod_name} ---")
        try:
            results = mod.run_tests()
        except Exception as e:
            _logger.error(f"Module {mod_name} crashed: {e}")
            results = [(f"{mod_name} module", f"FAIL: {e}", 0)]

        all_results[mod_name] = results
        for name, status, ms in results:
            level = logging.INFO if "PASS" in status else (
                    logging.WARNING if "SKIP" in status else logging.ERROR)
            _logger.log(level, f"  [{status}] {name} ({ms}ms)")

    _log_summary(all_results)
    return all_results


def _log_summary(all_results: dict):
    total = passed = failed = skipped = 0
    for results in all_results.values():
        for _, status, _ in results:
            total += 1
            if "PASS"  in status: passed  += 1
            elif "SKIP" in status: skipped += 1
            else:                  failed  += 1
    _logger.info("\n" + "=" * 60)
    _logger.info(f"SUMMARY: Total={total} | Passed={passed} | Failed={failed} | Skipped={skipped}")
    _logger.info("=" * 60)


def print_results(all_results: dict):
    PASS  = "\033[92m"
    FAIL  = "\033[91m"
    SKIP  = "\033[93m"
    RESET = "\033[0m"

    total = passed = failed = skipped = 0

    for mod_name, results in all_results.items():
        print(f"\n{'─'*55}")
        print(f"  MODULE: {mod_name}")
        print(f"{'─'*55}")
        for name, status, ms in results:
            total += 1
            if "PASS" in status:
                clr = PASS; passed += 1
            elif "SKIP" in status:
                clr = SKIP; skipped += 1
            else:
                clr = FAIL; failed += 1
            print(f"  {clr}[{status[:4]}]{RESET} {name:<40} {ms:>8.2f}ms")

    print(f"\n{'═'*55}")
    print(f"  TOTAL: {total}  |  "
          f"{PASS}PASS: {passed}{RESET}  |  "
          f"{FAIL}FAIL: {failed}{RESET}  |  "
          f"{SKIP}SKIP: {skipped}{RESET}")
    print(f"{'═'*55}")
    print(f"  Log saved → {_log_path}")


def export_report(all_results: dict, path: str = None):
    if not path:
        path = os.path.join(config.LOGS_DIR, "test_report.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"AI Surveillance System — Test Report\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        total = passed = failed = skipped = 0
        for mod_name, results in all_results.items():
            f.write(f"MODULE: {mod_name}\n")
            f.write("-" * 40 + "\n")
            for name, status, ms in results:
                f.write(f"  [{status[:4]}] {name:<38} {ms:.2f}ms\n")
                total += 1
                if "PASS" in status:  passed  += 1
                elif "SKIP" in status: skipped += 1
                else:                  failed  += 1
            f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}\n")
    print(f"\n  Report exported → {path}")
    return path


if __name__ == "__main__":
    results = run_all()
    print_results(results)
    export_report(results)
