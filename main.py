"""
main.py – Entry point for the AI Surveillance System.

Usage:
    python main.py

Flow:
    1. Initialise SQLite database (create tables, seed admin)
    2. Show hidden root Tk window (required by Toplevel)
    3. Open LoginWindow
    4. On successful login → open AdminDashboard
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa – creates dirs on import
from utils.logger import get_logger
from database import db_manager

logger = get_logger("main")


class SurveillanceApp:
    def __init__(self):
        # Hidden master root (keeps mainloop alive)
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.title("AI Surveillance System")
        self._root.protocol("WM_DELETE_WINDOW", self._quit)

        self._dashboard = None

    def run(self):
        logger.info("=== AI Surveillance System Starting ===")

        # Initialise database
        try:
            db_manager.initialize_db()
            logger.info("Database ready.")
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to initialise database:\n{e}")
            return

        # Show login
        self._show_login()
        self._root.mainloop()

    def _show_login(self):
        from gui.login_window import LoginWindow
        LoginWindow(self._root, on_success=self._on_login_success)

    def _on_login_success(self, username: str, email: str, role: str):
        logger.info(f"Login: {username} [{role}] → alert email: {email}")
        self._show_dashboard(username, email, role)

    def _show_dashboard(self, username: str, email: str, role: str):
        from gui.admin_dashboard import AdminDashboard
        if self._dashboard and self._dashboard.winfo_exists():
            self._dashboard.destroy()
        self._dashboard = AdminDashboard(
            self._root,
            username       = username,
            operator_email = email,
            role           = role,
            on_logout      = self._show_login,
        )

    def _quit(self):
        logger.info("Application exiting.")
        self._root.destroy()


if __name__ == "__main__":
    app = SurveillanceApp()
    app.run()
