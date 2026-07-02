"""gui/register_window.py – Operator self-registration form."""
import tkinter as tk
from tkinter import messagebox, ttk
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database import db_manager
from gui.widgets import styled_button


class RegistrationWindow(tk.Toplevel):
    """
    Self-registration form for new operators.
    Fields: Full Name, Gender, Mobile, Username, Password,
            Confirm Password, Email
    """

    def __init__(self, master):
        super().__init__(master)
        self.title("Operator Registration")
        self.geometry("460x680")
        self.resizable(False, False)
        self.configure(bg=config.THEME_BG)
        self.grab_set()          # modal
        self._build_ui()
        self._center()

    # ──────────────────────────────────────────────────────────────────────────
    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"460x680+{(sw-460)//2}+{(sh-680)//2}")

    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=config.ACCENT2, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Operator Registration",
                 bg=config.ACCENT2, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(expand=True)

        # Scrollable form area
        form = tk.Frame(self, bg=config.THEME_BG, padx=36)
        form.pack(fill="both", expand=True, pady=10)

        def field(label, var, show="", widget_type="entry"):
            tk.Label(form, text=label, bg=config.THEME_BG,
                     fg=config.THEME_FG, font=("Segoe UI", 9),
                     anchor="w").pack(fill="x", pady=(6, 1))
            if widget_type == "combo":
                w = ttk.Combobox(form, textvariable=var,
                                 values=["Male", "Female", "Other"],
                                 state="readonly", font=config.FONT_MAIN)
            else:
                w = tk.Entry(form, textvariable=var, show=show,
                             font=config.FONT_MAIN,
                             bg="#2a2a4a", fg="white",
                             insertbackground="white",
                             relief="flat", bd=0)
            w.pack(fill="x", ipady=6)
            return w

        self._name_var   = tk.StringVar()
        self._gender_var = tk.StringVar(value="Male")
        self._mob_var    = tk.StringVar()
        self._user_var   = tk.StringVar()
        self._pass_var   = tk.StringVar()
        self._cpass_var  = tk.StringVar()
        self._email_var  = tk.StringVar()

        field("Full Name *",         self._name_var)
        field("Gender *",            self._gender_var, widget_type="combo")
        field("Mobile Number *",     self._mob_var)
        field("Username *",          self._user_var)
        field("Password *",          self._pass_var,  show="●")
        field("Confirm Password *",  self._cpass_var, show="●")
        field("Email Address *",     self._email_var)

        # Status label
        self._status = tk.Label(form, text="", bg=config.THEME_BG,
                                fg="#ff6060", font=("Segoe UI", 9),
                                wraplength=380)
        self._status.pack(pady=(10, 0))

        # Buttons
        btn_row = tk.Frame(form, bg=config.THEME_BG)
        btn_row.pack(pady=12)
        styled_button(btn_row, "✔  REGISTER", self._submit,
                      config.ACCENT, 16).pack(side="left", padx=6)
        styled_button(btn_row, "✖  Cancel", self.destroy,
                      "#555577", 14).pack(side="left", padx=6)

    # ──────────────────────────────────────────────────────────────────────────
    def _submit(self):
        full_name = self._name_var.get().strip()
        gender    = self._gender_var.get().strip()
        mobile    = self._mob_var.get().strip()
        username  = self._user_var.get().strip()
        password  = self._pass_var.get()
        cpassword = self._cpass_var.get()
        email     = self._email_var.get().strip()

        # Validation
        if not all([full_name, gender, mobile, username, password, cpassword, email]):
            self._status.config(text="❌ All fields are required.")
            return
        if not re.fullmatch(r"\d{10}", mobile):
            self._status.config(text="❌ Mobile must be exactly 10 digits.")
            return
        if len(password) < 6:
            self._status.config(text="❌ Password must be at least 6 characters.")
            return
        if password != cpassword:
            self._status.config(text="❌ Passwords do not match.")
            return
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            self._status.config(text="❌ Invalid email address.")
            return

        success, err = db_manager.register_operator(
            full_name, gender, mobile, username, password, email
        )
        if success:
            messagebox.showinfo(
                "Registration Successful",
                f"✅ Operator '{username}' registered!\nYou can now log in.",
                parent=self
            )
            self.destroy()
        else:
            self._status.config(text=f"❌ {err}")
