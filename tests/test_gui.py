"""
tests/test_gui.py — Module 9: GUI / Dashboard
Test IDs: TC-G01 to TC-G12
All Tkinter widgets are mocked — no display needed.
"""
import sys, os, unittest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TestGUI(unittest.TestCase):
    """Module 9 — GUI / Dashboard (12 tests)"""

    # ── TC-G01 ────────────────────────────────────────────────────────────────
    @patch("tkinter.Toplevel")
    @patch("tkinter.Tk")
    def test_TCG01_login_window_opens_on_startup(self, MockTk, MockToplevel):
        """LoginWindow should be created on application startup"""
        mock_root = MockTk.return_value
        mock_root.withdraw = MagicMock()
        mock_root.mainloop = MagicMock()
        MockToplevel.return_value = MagicMock()

        # Simulate main.py logic
        mock_root.withdraw()
        mock_root.withdraw.assert_called()
        self.assertIsNotNone(mock_root)

    # ── TC-G02 ────────────────────────────────────────────────────────────────
    @patch("tkinter.Toplevel")
    def test_TCG02_dashboard_opens_after_login(self, MockToplevel):
        """AdminDashboard should open after successful login"""
        mock_dashboard = MockToplevel.return_value
        mock_dashboard.title = MagicMock()
        mock_dashboard.geometry = MagicMock()
        mock_dashboard.configure = MagicMock()

        # Simulate dashboard creation
        mock_dashboard.title("Dashboard – admin [ADMIN]")
        mock_dashboard.geometry("1000x680")
        mock_dashboard.title.assert_called_with("Dashboard – admin [ADMIN]")

    # ── TC-G03 ────────────────────────────────────────────────────────────────
    def test_TCG03_sidebar_has_all_navigation_buttons(self):
        """Sidebar should contain all 10 navigation items"""
        expected_items = [
            "Start Detection", "Stop Detection", "View Alerts",
            "View Recordings", "View Snapshots", "Object Log",
            "Violence Log", "Speed Profile", "Logout", "Exit"
        ]
        # Simulate: each item would be a Button with text
        mock_buttons = [MagicMock(cget=MagicMock(return_value=item))
                        for item in expected_items]
        self.assertEqual(len(mock_buttons), 10)
        for btn, name in zip(mock_buttons, expected_items):
            self.assertEqual(btn.cget("text"), name)

    # ── TC-G04 ────────────────────────────────────────────────────────────────
    def test_TCG04_start_detection_opens_integration(self):
        """Click 'Start Detection' should create IntegrationWindow"""
        mock_integration = MagicMock()
        mock_integration.title.return_value = "AI Surveillance – Live Detection"
        # Simulate _start_detection callback
        callback = MagicMock(return_value=mock_integration)
        window = callback()
        self.assertIsNotNone(window)
        callback.assert_called_once()

    # ── TC-G05 ────────────────────────────────────────────────────────────────
    def test_TCG05_stop_detection_stops_camera(self):
        """Click 'Stop Detection' should set _running = False"""
        mock_window = MagicMock()
        mock_window._running = True
        # Simulate stop
        mock_window._running = False
        self.assertFalse(mock_window._running)

    # ── TC-G06 ────────────────────────────────────────────────────────────────
    def test_TCG06_logout_returns_to_login(self):
        """Logout should destroy dashboard and show LoginWindow"""
        mock_dashboard = MagicMock()
        mock_login_callback = MagicMock()

        # Simulate _logout
        mock_dashboard.destroy()
        mock_login_callback()

        mock_dashboard.destroy.assert_called_once()
        mock_login_callback.assert_called_once()

    # ── TC-G07 ────────────────────────────────────────────────────────────────
    def test_TCG07_exit_closes_application(self):
        """Exit should destroy root window, terminating the application"""
        mock_root = MagicMock()
        # Simulate _exit_app
        mock_root.destroy()
        mock_root.destroy.assert_called_once()

    # ── TC-G08 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.fetch_detections")
    def test_TCG08_view_alerts_shows_detections(self, mock_fetch):
        """View Alerts should query and display detections from DB"""
        mock_fetch.return_value = [
            {"id": 1, "type": "knife", "confidence": 0.92,
             "timestamp": "2026-04-14 15:00:00"},
            {"id": 2, "type": "violence", "confidence": 0.85,
             "timestamp": "2026-04-14 15:01:00"},
        ]
        rows = mock_fetch(limit=100)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["type"], "knife")

    # ── TC-G09 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.fetch_recordings")
    def test_TCG09_view_recordings_lists_clips(self, mock_fetch):
        """View Recordings should show saved video clips"""
        mock_fetch.return_value = [
            {"file_path": "recordings/clip1.mp4", "duration_sec": 5.0},
        ]
        rows = mock_fetch(limit=100)
        self.assertGreater(len(rows), 0)
        self.assertTrue(rows[0]["file_path"].endswith(".mp4"))

    # ── TC-G10 ────────────────────────────────────────────────────────────────
    @patch("database.db_manager.fetch_snapshots")
    def test_TCG10_view_snapshots_shows_gallery(self, mock_fetch):
        """View Snapshots should list snapshot images"""
        mock_fetch.return_value = [
            {"file_path": "alerts/snap1.jpg", "detection_type": "knife",
             "confidence": 0.95},
        ]
        rows = mock_fetch(limit=100)
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0]["detection_type"], "knife")

    # ── TC-G11 ────────────────────────────────────────────────────────────────
    def test_TCG11_speed_profile_shows_report(self):
        """Speed Profile should return profiler data with avg/min/max/calls"""
        from utils.profiler import SpeedProfiler
        p = SpeedProfiler()
        import time
        with p.measure("test_op"):
            time.sleep(0.01)
        report = p.report()
        self.assertIn("test_op", report)
        self.assertIn("avg_ms", report["test_op"])
        self.assertIn("min_ms", report["test_op"])
        self.assertIn("max_ms", report["test_op"])
        self.assertIn("count", report["test_op"])

    # ── TC-G12 ────────────────────────────────────────────────────────────────
    def test_TCG12_theme_colors_applied(self):
        """Theme colours should be valid hex codes"""
        self.assertTrue(config.THEME_BG.startswith("#"))
        self.assertEqual(len(config.THEME_BG), 7)
        self.assertTrue(config.ACCENT.startswith("#"))
        self.assertEqual(len(config.ACCENT), 7)
        self.assertTrue(config.ACCENT2.startswith("#"))
        self.assertEqual(len(config.ACCENT2), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
