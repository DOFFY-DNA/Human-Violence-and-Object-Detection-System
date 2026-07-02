"""gui/login_window.py – Login window with Register option for operators."""
import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database import db_manager
from gui.widgets import styled_button


class LoginWindow(tk.Toplevel):
    """
    Login window for both Admin and Operators.
    - Admin: username='admin', stored in 'users' table
    - Operator: registered via RegistrationWindow, stored in 'operators' table

    on_success(username, email, role) is called on successful login.
    """

    def __init__(self, master, on_success):
        super().__init__(master)
        self.title("Project System – Login")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(bg=config.THEME_BG)
        self._on_success = on_success
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 420) // 2
        y = (sh - 520) // 2
        self.geometry(f"420x520+{x}+{y}")

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=config.ACCENT2, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🛡  Project System",
                 bg=config.ACCENT2, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(expand=True)
        tk.Label(header, text="Knife & Violence Detection",
                 bg=config.ACCENT2, fg="#a0b4c8",
                 font=("Segoe UI", 9)).pack(pady=(0, 10))

        # Form
        form = tk.Frame(self, bg=config.THEME_BG, padx=40)
        form.pack(fill="both", expand=True, pady=20)

        tk.Label(form, text="Username", bg=config.THEME_BG,
                 fg=config.THEME_FG, font=config.FONT_MAIN,
                 anchor="w").pack(fill="x", pady=(20, 2))
        self._user_var = tk.StringVar(value="")
        self._user_entry = tk.Entry(form, textvariable=self._user_var,
                                    font=config.FONT_MAIN,
                                    bg="#2a2a4a", fg="white",
                                    insertbackground="white",
                                    relief="flat", bd=0)
        self._user_entry.pack(fill="x", ipady=8)

        tk.Label(form, text="Password", bg=config.THEME_BG,
                 fg=config.THEME_FG, font=config.FONT_MAIN,
                 anchor="w").pack(fill="x", pady=(14, 2))
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(form, textvariable=self._pass_var,
                                     show="●", font=config.FONT_MAIN,
                                     bg="#2a2a4a", fg="white",
                                     insertbackground="white",
                                     relief="flat", bd=0)
        self._pass_entry.pack(fill="x", ipady=8)
        self._pass_entry.bind("<Return>", lambda e: self._login())

        self._status = tk.Label(form, text="", bg=config.THEME_BG,
                                 fg=config.ACCENT, font=("Segoe UI", 9))
        self._status.pack(pady=8)

        # LOGIN button
        styled_button(form, "LOGIN", self._login,
                      color=config.ACCENT, width=20).pack(expand=True, pady=(0, 6))

        # Divider
        tk.Label(form, text="─────────  or  ─────────",
                 bg=config.THEME_BG, fg="#3a4060",
                 font=("Segoe UI", 8)).pack(pady=4)

        # REGISTER button
        styled_button(form, "📋  REGISTER AS OPERATOR", self._open_register,
                      color="#1a5090", width=20).pack(expand=True)

        tk.Label(form, text="Admin default: admin / admin123",
                 bg=config.THEME_BG, fg="#556080",
                 font=("Segoe UI", 8)).pack(pady=(14, 0))

    # ──────────────────────────────────────────────────────────────────────────
    def _login(self):
        username = self._user_var.get().strip()
        password = self._pass_var.get()
        if not username or not password:
            self._status.config(text="Please enter both fields.")
            return

        # 1. Check admin table first
        if db_manager.verify_user(username, password):
            # Admin login — use default admin email
            self._on_success(username, config.EMAIL_RECEIVER, "admin")
            self.destroy()
            return

        # 2. Check operators table
        op = db_manager.verify_operator(username, password)
        if op:
            # Operator login — use their registered email
            self._on_success(username, op["email"], "operator")
            self.destroy()
            return

        self._status.config(text="Invalid username or password.")
        self._pass_var.set("")

    def _open_register(self):
        from gui.register_window import RegistrationWindow
        RegistrationWindow(self)

    def _on_close(self):
        self.master.destroy()
