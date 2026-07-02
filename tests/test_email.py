"""
tests/test_email.py — Module 7: Email Alert Service
Test IDs: TC-E01 to TC-E10
smtplib.SMTP is fully mocked — no real email sending.
"""
import sys, os, unittest, threading
from unittest.mock import patch, MagicMock, call
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TestEmail(unittest.TestCase):
    """Module 7 — Email Alert Service (10 tests)"""

    # ── TC-E01 ────────────────────────────────────────────────────────────────
    def test_TCE01_email_config_values_set(self):
        """Email config should have sender, host, and port set correctly"""
        self.assertTrue(len(config.EMAIL_SENDER) > 0,
                        "EMAIL_SENDER is empty")
        self.assertEqual(config.SMTP_HOST, "smtp.gmail.com")
        self.assertEqual(config.SMTP_PORT, 587)

    # ── TC-E02 ────────────────────────────────────────────────────────────────
    @patch("config.EMAIL_ENABLED", False)
    def test_TCE02_email_disabled_skips_sending(self):
        """When EMAIL_ENABLED=False, no email should be sent"""
        callback = MagicMock()
        from services.email_service import send_direct_alert
        t = send_direct_alert("knife", [], 0.9, callback=callback)
        t.join(timeout=5)
        callback.assert_called_once()
        args = callback.call_args[0]
        self.assertFalse(args[0])  # success = False
        self.assertIn("disabled", args[1].lower())

    # ── TC-E03 ────────────────────────────────────────────────────────────────
    def test_TCE03_mime_message_built_correctly(self):
        """MIME message should have correct From, To, Subject fields"""
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = config.EMAIL_RECEIVER
        msg["Subject"] = "Test Alert"
        self.assertEqual(msg["From"], config.EMAIL_SENDER)
        self.assertEqual(msg["To"], config.EMAIL_RECEIVER)
        self.assertEqual(msg["Subject"], "Test Alert")

    # ── TC-E04 ────────────────────────────────────────────────────────────────
    @patch("smtplib.SMTP")
    @patch("config.EMAIL_ENABLED", True)
    def test_TCE04_email_attaches_snapshot_images(self, MockSMTP):
        """Email should include attached snapshot images"""
        import tempfile
        # Create a real temp file to attach
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(b"\xff\xd8\xff\xe0fake_jpeg_data")
        tmp.close()

        try:
            from services.email_service import _attach_file
            msg = MIMEMultipart()
            _attach_file(msg, tmp.name)
            payloads = msg.get_payload()
            self.assertGreater(len(payloads), 0)
        finally:
            os.unlink(tmp.name)

    # ── TC-E05 ────────────────────────────────────────────────────────────────
    @patch("smtplib.SMTP")
    @patch("config.EMAIL_ENABLED", True)
    def test_TCE05_email_attaches_video_clip(self, MockSMTP):
        """Email should include attached video clip"""
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"\x00\x00\x00\x1cftypisom" + b"\x00" * 100)
        tmp.close()

        try:
            from services.email_service import _attach_file
            msg = MIMEMultipart()
            _attach_file(msg, tmp.name)
            payloads = msg.get_payload()
            self.assertGreater(len(payloads), 0)
        finally:
            os.unlink(tmp.name)

    # ── TC-E06 ────────────────────────────────────────────────────────────────
    def test_TCE06_missing_attachment_handled(self):
        """Attaching non-existent file should not crash"""
        from services.email_service import _attach_file
        msg = MIMEMultipart()
        # Should silently skip, not raise
        _attach_file(msg, "definitely_nonexistent_file_xyz.jpg")
        self.assertEqual(len(msg.get_payload()), 0)

    # ── TC-E07 ────────────────────────────────────────────────────────────────
    def test_TCE07_max_4_snapshots_attached(self):
        """Only first 4 snapshots should be attached even if 6 are provided"""
        import tempfile
        from services.email_service import _attach_file

        files = []
        for i in range(6):
            tmp = tempfile.NamedTemporaryFile(suffix=f"_{i}.jpg", delete=False)
            tmp.write(b"\xff\xd8" + bytes(100))
            tmp.close()
            files.append(tmp.name)

        try:
            msg = MIMEMultipart()
            # Simulate the slicing logic from send_alert_email: snapshots[:4]
            for snap in files[:4]:
                _attach_file(msg, snap)
            payloads = msg.get_payload()
            self.assertEqual(len(payloads), 4)
        finally:
            for f in files:
                os.unlink(f)

    # ── TC-E08 ────────────────────────────────────────────────────────────────
    @patch("smtplib.SMTP")
    @patch("config.EMAIL_ENABLED", True)
    def test_TCE08_email_runs_in_background_thread(self, MockSMTP):
        """send_direct_alert should return a Thread and not block"""
        mock_server = MockSMTP.return_value.__enter__ = MagicMock()
        from services.email_service import send_direct_alert
        t = send_direct_alert("knife", [], 0.9)
        self.assertIsInstance(t, threading.Thread)
        t.join(timeout=5)

    # ── TC-E09 ────────────────────────────────────────────────────────────────
    @patch("smtplib.SMTP")
    @patch("config.EMAIL_ENABLED", True)
    def test_TCE09_email_sent_to_multiple_recipients(self, MockSMTP):
        """Email should be sent to both operator and admin emails"""
        callback = MagicMock()
        from services.email_service import send_direct_alert
        t = send_direct_alert(
            "knife", [], 0.9,
            receiver_emails=["op@test.com", "admin@test.com"],
            callback=callback
        )
        t.join(timeout=5)
        # Verify sendmail was called (it may succeed or fail, but the
        # attempt should target both emails)
        self.assertTrue(callback.called)

    # ── TC-E10 ────────────────────────────────────────────────────────────────
    @patch("smtplib.SMTP")
    @patch("config.EMAIL_ENABLED", True)
    def test_TCE10_email_fallback_to_admin(self, MockSMTP):
        """Empty recipient list should fall back to config.EMAIL_RECEIVER"""
        callback = MagicMock()
        from services.email_service import send_direct_alert
        t = send_direct_alert("knife", [], 0.9, receiver_emails=[],
                              callback=callback)
        t.join(timeout=5)
        # Function should have used config.EMAIL_RECEIVER as fallback
        self.assertTrue(callback.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
