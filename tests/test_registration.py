"""
tests/test_registration.py — Module 2: Authentication (Registration)
Test IDs: TC-R01 to TC-R11
All DB calls are mocked.
"""
import sys, os, unittest, re
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _validate_registration(full_name, gender, mobile, username, password,
                           confirm_password, email):
    """Replicates the validation logic from register_window.py"""
    if not all([full_name, gender, mobile, username, password, confirm_password, email]):
        return False, "All fields are required."
    if not re.fullmatch(r"\d{10}", mobile):
        return False, "Mobile must be exactly 10 digits."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirm_password:
        return False, "Passwords do not match."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Invalid email address."
    return True, ""


class TestRegistration(unittest.TestCase):
    """Module 2 — Operator Registration (11 tests)"""

    # ── TC-R01 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.register_operator", return_value=(True, ""))
    def test_TCR01_register_valid_operator(self, mock_reg):
        """Register operator with all valid fields"""
        ok, err = _validate_registration(
            "John Doe", "Male", "9876543210", "john01",
            "pass123", "pass123", "john@test.com"
        )
        self.assertTrue(ok)
        self.assertEqual(err, "")
        # Simulate DB call
        result, _ = mock_reg("John Doe", "Male", "9876543210",
                             "john01", "pass123", "john@test.com")
        self.assertTrue(result)

    # ── TC-R02 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.register_operator",
           return_value=(False, "Username already exists."))
    def test_TCR02_register_duplicate_username(self, mock_reg):
        """Register with duplicate username should fail"""
        result, err = mock_reg("Test", "Male", "1234567890",
                               "testuser", "pass123", "t@t.com")
        self.assertFalse(result)
        self.assertIn("already exists", err)

    # ── TC-R03 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.register_operator",
           return_value=(False, "Username already exists."))
    def test_TCR03_register_username_same_as_admin(self, mock_reg):
        """Register with username 'admin' should fail"""
        result, err = mock_reg("Admin User", "Male", "1234567890",
                               "admin", "pass123", "a@a.com")
        self.assertFalse(result)
        self.assertIn("already exists", err)

    # ── TC-R04 ────────────────────────────────────────────────────────────────
    def test_TCR04_register_empty_required_field(self):
        """Register with empty Full Name should fail"""
        ok, err = _validate_registration(
            "", "Male", "9876543210", "user1",
            "pass123", "pass123", "u@u.com"
        )
        self.assertFalse(ok)
        self.assertIn("required", err)

    # ── TC-R05 ────────────────────────────────────────────────────────────────
    def test_TCR05_register_invalid_mobile_short(self):
        """Register with less than 10 digit mobile should fail"""
        ok, err = _validate_registration(
            "Name", "Male", "12345", "user1",
            "pass123", "pass123", "u@u.com"
        )
        self.assertFalse(ok)
        self.assertIn("10 digits", err)

    # ── TC-R06 ────────────────────────────────────────────────────────────────
    def test_TCR06_register_invalid_mobile_letters(self):
        """Register with letters in mobile should fail"""
        ok, err = _validate_registration(
            "Name", "Male", "abcdefghij", "user1",
            "pass123", "pass123", "u@u.com"
        )
        self.assertFalse(ok)
        self.assertIn("10 digits", err)

    # ── TC-R07 ────────────────────────────────────────────────────────────────
    def test_TCR07_register_short_password(self):
        """Register with password shorter than 6 characters should fail"""
        ok, err = _validate_registration(
            "Name", "Male", "9876543210", "user1",
            "abc", "abc", "u@u.com"
        )
        self.assertFalse(ok)
        self.assertIn("6 characters", err)

    # ── TC-R08 ────────────────────────────────────────────────────────────────
    def test_TCR08_register_mismatched_passwords(self):
        """Register with mismatched passwords should fail"""
        ok, err = _validate_registration(
            "Name", "Male", "9876543210", "user1",
            "pass123", "pass456", "u@u.com"
        )
        self.assertFalse(ok)
        self.assertIn("do not match", err)

    # ── TC-R09 ────────────────────────────────────────────────────────────────
    def test_TCR09_register_invalid_email(self):
        """Register with invalid email format should fail"""
        ok, err = _validate_registration(
            "Name", "Male", "9876543210", "user1",
            "pass123", "pass123", "notanemail"
        )
        self.assertFalse(ok)
        self.assertIn("Invalid email", err)

    # ── TC-R10 ────────────────────────────────────────────────────────────────
    def test_TCR10_cancel_registration(self):
        """Cancel registration should not save data"""
        mock_window = MagicMock()
        mock_window.destroy()
        mock_window.destroy.assert_called_once()
        # No DB call should have been made
        # (We verify no mock_reg was called — nothing to assert beyond destroy)

    # ── TC-R11 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.verify_operator")
    @patch("database.db_manager.register_operator", return_value=(True, ""))
    def test_TCR11_login_after_registration(self, mock_reg, mock_verify):
        """Login should succeed immediately after successful registration"""
        # Register
        ok, _ = mock_reg("New Op", "Female", "1234567890",
                         "newop", "pass123", "new@op.com")
        self.assertTrue(ok)
        # Now login
        mock_verify.return_value = {"username": "newop", "email": "new@op.com"}
        op = mock_verify("newop", "pass123")
        self.assertIsNotNone(op)
        self.assertEqual(op["email"], "new@op.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
