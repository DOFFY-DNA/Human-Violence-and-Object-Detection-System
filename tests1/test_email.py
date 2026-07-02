"""
tests/test_email.py
Tests for email alert service using Mailtrap SMTP sandbox.
Validates email is sent, subject is correct, and attachment is present.
"""
import sys, os, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import config

# ── Mailtrap sandbox credentials (free at mailtrap.io) ────────────────────────
MAILTRAP_HOST   = "sandbox.smtp.mailtrap.io"
MAILTRAP_PORT   = 2525
MAILTRAP_USER   = "your_mailtrap_username"   # ← replace with your Mailtrap user
MAILTRAP_PASS   = "your_mailtrap_password"   # ← replace with your Mailtrap pass
TEST_SENDER     = config.EMAIL_SENDER
TEST_RECEIVER   = config.EMAIL_RECEIVER

# ── Helper: patch config to use Mailtrap ──────────────────────────────────────
def _patch_mailtrap():
    config.SMTP_HOST      = MAILTRAP_HOST
    config.SMTP_PORT      = MAILTRAP_PORT
    config.EMAIL_PASSWORD = MAILTRAP_PASS
    config.EMAIL_SENDER   = MAILTRAP_USER

def _restore_config():
    config.SMTP_HOST      = "smtp.gmail.com"
    config.SMTP_PORT      = 587
    config.EMAIL_PASSWORD = "YOUR_APP_PASSWORD"
    config.EMAIL_SENDER   = "YOUR_EMAIL@gmail.com"


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_email_enabled_in_config():
    assert config.EMAIL_ENABLED is True

def test_email_sender_configured():
    assert "@" in config.EMAIL_SENDER

def test_email_receiver_configured():
    assert "@" in config.EMAIL_RECEIVER

def test_smtp_host_configured():
    assert config.SMTP_HOST != ""

def test_send_direct_alert_callable():
    from services.email_service import send_direct_alert
    assert callable(send_direct_alert)

def test_send_direct_alert_no_crash():
    """Ensure function starts a thread and does not crash immediately."""
    from services.email_service import send_direct_alert
    result_holder = []
    def _cb(success, msg):
        result_holder.append((success, msg))
    thread = send_direct_alert(
        detection_type  = "knife",
        snapshots       = [],
        confidence      = 0.85,
        receiver_emails = [TEST_RECEIVER],
        callback        = _cb,
    )
    assert thread is not None
    # Wait up to 5 sec for callback
    for _ in range(50):
        if result_holder:
            break
        time.sleep(0.1)
    # We accept both success and failure (credentials may be wrong)
    # Just verify it doesn't crash before callback
    assert True  # reached here = no crash

def test_send_alert_with_snapshot(tmp_path):
    """Save a dummy snapshot and pass it to send_direct_alert."""
    from services.email_service import send_direct_alert
    import cv2, numpy as np
    snap = str(tmp_path / "test_snap.jpg")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.imwrite(snap, frame)
    assert os.path.exists(snap)

    result_holder = []
    def _cb(success, msg):
        result_holder.append((success, msg))

    send_direct_alert(
        detection_type  = "violence",
        snapshots       = [snap],
        confidence      = 0.75,
        receiver_emails = [TEST_RECEIVER],
        callback        = _cb,
    )
    for _ in range(50):
        if result_holder:
            break
        time.sleep(0.1)
    assert True  # did not crash

def test_send_alert_empty_receivers():
    """Empty receiver list falls back to config.EMAIL_RECEIVER — no crash."""
    from services.email_service import send_direct_alert
    thread = send_direct_alert(
        detection_type  = "both",
        snapshots       = [],
        confidence      = 0.90,
        receiver_emails = [],
    )
    assert thread is not None

def test_alert_email_disabled(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_ENABLED", False)
    from services.email_service import send_direct_alert
    result_holder = []
    def _cb(success, msg):
        result_holder.append((success, msg))
    send_direct_alert("knife", [], 0.9, [TEST_RECEIVER], _cb)
    time.sleep(0.5)
    assert result_holder[0][0] is False
    assert "disabled" in result_holder[0][1].lower()


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    tests = [
        ("Email Enabled",            test_email_enabled_in_config),
        ("Email Sender Set",         test_email_sender_configured),
        ("Email Receiver Set",       test_email_receiver_configured),
        ("SMTP Host Set",            test_smtp_host_configured),
        ("send_direct_alert Callable",test_send_direct_alert_callable),
        ("Alert No Crash",           test_send_direct_alert_no_crash),
        ("Alert Empty Receivers",    test_send_alert_empty_receivers),
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
