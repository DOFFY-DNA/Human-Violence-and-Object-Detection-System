"""
tests/test_login.py
Tests for login and registration logic (db_manager verify/register).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from database import db_manager

# ── Helpers ───────────────────────────────────────────────────────────────────
_TEST_USER = "test_op_999"
_TEST_PASS = "Test@1234"
_TEST_EMAIL = "testop999@gmail.com"

def _cleanup():
    try:
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM operators WHERE username=?", (_TEST_USER,))
        conn.commit(); conn.close()
    except Exception:
        pass


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_admin_login_valid():
    assert db_manager.verify_user("admin", "admin123") is True

def test_admin_login_wrong_password():
    assert db_manager.verify_user("admin", "wrongpass") is False

def test_admin_login_nonexistent():
    assert db_manager.verify_user("nobody", "nopass") is False

def test_operator_registration():
    _cleanup()
    ok, err = db_manager.register_operator(
        "Test Operator", "Male", "9876543210",
        _TEST_USER, _TEST_PASS, _TEST_EMAIL
    )
    assert ok is True, f"Registration failed: {err}"
    _cleanup()

def test_operator_duplicate_username():
    _cleanup()
    db_manager.register_operator(
        "Test Op", "Male", "9876543210",
        _TEST_USER, _TEST_PASS, _TEST_EMAIL
    )
    ok, err = db_manager.register_operator(
        "Test Op2", "Female", "9000000000",
        _TEST_USER, "AnotherPass1", "other@gmail.com"
    )
    assert ok is False
    assert "exists" in err.lower()
    _cleanup()

def test_operator_login_valid():
    _cleanup()
    db_manager.register_operator(
        "Test Op", "Male", "9876543210",
        _TEST_USER, _TEST_PASS, _TEST_EMAIL
    )
    op = db_manager.verify_operator(_TEST_USER, _TEST_PASS)
    assert op is not None
    assert op["email"] == _TEST_EMAIL
    _cleanup()

def test_operator_login_wrong_password():
    _cleanup()
    db_manager.register_operator(
        "Test Op", "Male", "9876543210",
        _TEST_USER, _TEST_PASS, _TEST_EMAIL
    )
    op = db_manager.verify_operator(_TEST_USER, "WrongPass")
    assert op is None
    _cleanup()

def test_get_operator_email():
    _cleanup()
    db_manager.register_operator(
        "Test Op", "Male", "9876543210",
        _TEST_USER, _TEST_PASS, _TEST_EMAIL
    )
    email = db_manager.get_operator_email(_TEST_USER)
    assert email == _TEST_EMAIL
    _cleanup()


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    tests = [
        ("Admin Login Valid",         test_admin_login_valid),
        ("Admin Login Wrong Password",test_admin_login_wrong_password),
        ("Admin Login Nonexistent",   test_admin_login_nonexistent),
        ("Operator Registration",     test_operator_registration),
        ("Operator Duplicate User",   test_operator_duplicate_username),
        ("Operator Login Valid",      test_operator_login_valid),
        ("Operator Login Wrong Pass", test_operator_login_wrong_password),
        ("Get Operator Email",        test_get_operator_email),
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
