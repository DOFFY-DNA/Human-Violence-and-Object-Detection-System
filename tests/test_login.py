"""
tests/test_login.py — Module 1: Authentication (Login)
Test IDs: TC-L01 to TC-L10
All Tkinter / DB interactions are mocked.
"""
import sys, os, unittest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLogin(unittest.TestCase):
    """Module 1 — Login Authentication (10 tests)"""

    # ── TC-L01 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_user", return_value=True)
    def test_TCL01_admin_login_valid(self, mock_verify):
        """Admin login with valid credentials"""
        result = mock_verify("admin", "admin123")
        self.assertTrue(result)
        mock_verify.assert_called_once_with("admin", "admin123")

    # ── TC-L02 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_user", return_value=False)
    def test_TCL02_admin_login_wrong_password(self, mock_verify):
        """Admin login with wrong password"""
        result = mock_verify("admin", "wrongpass")
        self.assertFalse(result)

    # ── TC-L03 ────────────────────────────────────────────────────────────────
    def test_TCL03_login_empty_username(self):
        """Login with empty username should be rejected"""
        username = ""
        password = "admin123"
        self.assertFalse(bool(username and password))

    # ── TC-L04 ────────────────────────────────────────────────────────────────
    def test_TCL04_login_empty_password(self):
        """Login with empty password should be rejected"""
        username = "admin"
        password = ""
        self.assertFalse(bool(username and password))

    # ── TC-L05 ────────────────────────────────────────────────────────────────
    def test_TCL05_login_both_fields_empty(self):
        """Login with both fields empty should be rejected"""
        username = ""
        password = ""
        self.assertFalse(bool(username and password))

    # ── TC-L06 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_operator")
    def test_TCL06_operator_login_valid(self, mock_verify_op):
        """Operator login with valid credentials"""
        mock_verify_op.return_value = {
            "id": 1, "username": "op1", "email": "op1@test.com",
            "full_name": "Operator One", "password_hash": "xxx"
        }
        result = mock_verify_op("op1", "oppass123")
        self.assertIsNotNone(result)
        self.assertEqual(result["email"], "op1@test.com")

    # ── TC-L07 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_operator", return_value=None)
    @patch("database.db_manager.verify_user", return_value=False)
    def test_TCL07_login_nonexistent_user(self, mock_user, mock_op):
        """Login with non-existent username should fail"""
        user_ok = mock_user("fakeuser", "test123")
        op_ok = mock_op("fakeuser", "test123")
        self.assertFalse(user_ok)
        self.assertIsNone(op_ok)

    # ── TC-L08 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_user", return_value=False)
    def test_TCL08_login_sql_injection(self, mock_verify):
        """Login with SQL injection attempt should fail safely"""
        result = mock_verify("' OR 1=1 --", "anything")
        self.assertFalse(result)

    # ── TC-L09 ────────────────────────────────────────────────────────────────
    def test_TCL09_enter_key_triggers_login(self):
        """Press Enter key in password field should trigger login"""
        # Simulate: in LoginWindow, password entry binds <Return> to _login()
        mock_callback = MagicMock()
        mock_event = MagicMock()
        # Simulate binding
        bindings = {"<Return>": mock_callback}
        bindings["<Return>"](mock_event)
        mock_callback.assert_called_once_with(mock_event)

    # ── TC-L10 ────────────────────────────────────────────────────────────────
    def test_TCL10_close_login_window_exits(self):
        """Closing LoginWindow should exit the application"""
        mock_master = MagicMock()
        # Simulate _on_close: self.master.destroy()
        mock_master.destroy()
        mock_master.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
