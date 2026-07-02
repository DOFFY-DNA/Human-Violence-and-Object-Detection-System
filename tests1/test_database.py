"""
tests/test_database.py
Tests for all db_manager functions: init, insert, fetch, integrity.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from database import db_manager

_TEST_OP = "dbtest_op_777"


def _cleanup():
    try:
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM operators WHERE username=?", (_TEST_OP,))
        conn.commit(); conn.close()
    except Exception:
        pass


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_db_file_exists():
    import config
    assert os.path.exists(config.DB_PATH), "Database file not found"

def test_get_connection():
    conn = db_manager.get_connection()
    assert conn is not None
    conn.close()

def test_tables_exist():
    conn = db_manager.get_connection()
    tables = {row[0] for row in
              conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    for t in ["users", "operators", "detections", "snapshots"]:
        assert t in tables, f"Table '{t}' missing"

def test_register_operator_inserts_row():
    _cleanup()
    ok, err = db_manager.register_operator(
        "DB Test Op", "Male", "9000000001",
        _TEST_OP, "DbPass@123", "dbtest@gmail.com"
    )
    assert ok is True, err
    conn = db_manager.get_connection()
    row = conn.execute("SELECT username FROM operators WHERE username=?",
                       (_TEST_OP,)).fetchone()
    conn.close()
    assert row is not None
    _cleanup()

def test_log_detection_inserts_row():
    before = len(db_manager.fetch_detections())
    db_manager.log_detection("knife", "knife", 0.88, status="test")
    after  = len(db_manager.fetch_detections())
    assert after == before + 1

def test_fetch_detections_returns_list():
    result = db_manager.fetch_detections()
    assert isinstance(result, list)

def test_log_snapshot_inserts_row():
    before = len(db_manager.fetch_snapshots())
    db_manager.log_snapshot("/fake/path/snap.jpg", "knife", 0.91)
    after  = len(db_manager.fetch_snapshots())
    assert after == before + 1

def test_fetch_snapshots_returns_list():
    result = db_manager.fetch_snapshots()
    assert isinstance(result, list)

def test_operator_password_is_hashed():
    """Stored password_hash must not equal plain text."""
    _cleanup()
    db_manager.register_operator(
        "Hash Test", "Female", "9000000002",
        _TEST_OP, "PlainPass@1", "hash@gmail.com"
    )
    conn = db_manager.get_connection()
    row = conn.execute("SELECT password_hash FROM operators WHERE username=?",
                       (_TEST_OP,)).fetchone()
    conn.close()
    assert row is not None
    assert row[0] != "PlainPass@1", "Password stored as plain text!"
    _cleanup()

def test_verify_operator_returns_none_for_wrong_password():
    _cleanup()
    db_manager.register_operator(
        "Verify Test", "Male", "9000000003",
        _TEST_OP, "RealPass@1", "verify@gmail.com"
    )
    result = db_manager.verify_operator(_TEST_OP, "WrongPass")
    assert result is None
    _cleanup()

def test_fetch_recordings_returns_list():
    result = db_manager.fetch_recordings()
    assert isinstance(result, list)


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    tests = [
        ("DB File Exists",            test_db_file_exists),
        ("Get Connection",            test_get_connection),
        ("Tables Exist",              test_tables_exist),
        ("Register Operator Inserts", test_register_operator_inserts_row),
        ("Log Detection Inserts",     test_log_detection_inserts_row),
        ("Fetch Detections List",     test_fetch_detections_returns_list),
        ("Log Snapshot Inserts",      test_log_snapshot_inserts_row),
        ("Fetch Snapshots List",      test_fetch_snapshots_returns_list),
        ("Password Is Hashed",        test_operator_password_is_hashed),
        ("Wrong Password Returns None",test_verify_operator_returns_none_for_wrong_password),
        ("Fetch Recordings List",     test_fetch_recordings_returns_list),
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
