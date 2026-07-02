"""gui/widgets.py – Reusable styled Tkinter widgets."""
import tkinter as tk
from tkinter import ttk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def styled_button(parent, text, command=None, color=None, width=18, **kwargs):
    bg = color or config.ACCENT
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg="white", activebackground=config.ACCENT2,
        activeforeground="white", relief="flat", bd=0,
        font=("Segoe UI", 10, "bold"), width=width,
        cursor="hand2", padx=8, pady=6, **kwargs
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=config.ACCENT2))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def status_label(parent, text="", fg=None, **kwargs):
    return tk.Label(
        parent, text=text,
        bg=config.THEME_BG, fg=fg or config.THEME_FG,
        font=config.FONT_MONO,
        anchor="w", **kwargs
    )


def section_label(parent, text, **kwargs):
    return tk.Label(
        parent, text=text,
        bg=config.ACCENT2, fg="white",
        font=("Segoe UI", 11, "bold"),
        padx=10, pady=4, anchor="center", **kwargs
    )


def separator(parent, **kwargs):
    return ttk.Separator(parent, orient="horizontal", **kwargs)


def panel_frame(parent, **kwargs):
    return tk.Frame(parent, bg="#0d0d1a",
                    highlightbackground=config.ACCENT2,
                    highlightthickness=2, **kwargs)


def video_canvas(parent, width, height, **kwargs):
    canvas = tk.Canvas(parent, width=width, height=height,
                       bg="#0d0d1a", highlightthickness=0, **kwargs)
    return canvas


class AlertBanner(tk.Label):
    """Flashing alert banner shown when both detections confirmed."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent,
                         text="", bg=config.THEME_BG,
                         fg=config.ACCENT,
                         font=("Segoe UI", 11, "bold"),
                         padx=12, pady=4, **kwargs)
        self._visible = False
        self._flash_job = None

    def show(self, msg="⚠ CRITICAL: KNIFE + VIOLENCE DETECTED"):
        self._visible = True
        self.config(text=msg)
        self._flash()

    def hide(self):
        self._visible = False
        if self._flash_job:
            self.after_cancel(self._flash_job)
        self.config(text="", bg=config.THEME_BG)

    def _flash(self):
        if not self._visible:
            return
        current = self.cget("bg")
        next_bg = config.ACCENT if current == config.THEME_BG else config.THEME_BG
        next_fg = "white" if current == config.THEME_BG else config.ACCENT
        self.config(bg=next_bg, fg=next_fg)
        self._flash_job = self.after(600, self._flash)
