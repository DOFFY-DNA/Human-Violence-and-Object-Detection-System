"""
gui/admin_dashboard.py – Admin Dashboard window.
Contains sidebar navigation and launches the dual-panel detection window.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, threading
from PIL import Image, ImageTk
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from database import db_manager
from gui.widgets import styled_button, section_label


class AdminDashboard(tk.Toplevel):
    def __init__(self, master, username: str, operator_email: str,
                 role: str, on_logout):
        super().__init__(master)
        self.title(f"Dashboard  –  {username}  [{role.upper()}]")
        self.geometry("1000x680")
        self.minsize(900, 600)
        self.configure(bg=config.THEME_BG)
        self._username       = username
        self._operator_email = operator_email   # email for this session's alerts
        self._role           = role
        self._on_logout      = on_logout
        self._det_window     = None
        self.protocol("WM_DELETE_WINDOW", self._exit_app)
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"1000x680+{(sw-1000)//2}+{(sh-680)//2}")

    # ──────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=config.ACCENT2, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🛡", bg=config.ACCENT2, fg="white",
                 font=("Segoe UI", 28)).pack(pady=(24, 0))
        tk.Label(sidebar, text="Project System", bg=config.ACCENT2, fg="white",
                 font=("Segoe UI", 11, "bold")).pack()
        tk.Label(sidebar, text=f"👤 {self._username}", bg=config.ACCENT2,
                 fg="#a0b4c8", font=("Segoe UI", 9)).pack(pady=(2, 0))
        tk.Label(sidebar, text=f"✉ {self._operator_email}", bg=config.ACCENT2,
                 fg="#607090", font=("Segoe UI", 8),
                 wraplength=180).pack(pady=(0, 16))

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=12)

        nav_items = [
            ("▶  Start Detection",   self._start_detection),
            ("⏹  Stop Detection",    self._stop_detection),
            ("🔔  View Alerts",      self._view_alerts),
            ("🎬  View Recordings",  self._view_recordings),
            ("📸  View Snapshots",   self._view_snapshots),
            ("📄  Object Log",       self._view_object_log),
            ("📄  Violence Log",     self._view_violence_log),
            ("⏱  Speed Profile",    self._view_speed_profile),
        ]
        for label, cmd in nav_items:
            btn = tk.Button(sidebar, text=label, command=cmd,
                            bg=config.ACCENT2, fg="white",
                            activebackground="#1a4580", activeforeground="white",
                            relief="flat", font=("Segoe UI", 10),
                            anchor="w", padx=16, pady=10, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#1a4580"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=config.ACCENT2))

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=12, pady=10)
        styled_button(sidebar, "⬅ Logout",  self._logout,  "#555577", width=16).pack(pady=4)
        styled_button(sidebar, "✖  Exit",   self._exit_app, "#8b0000", width=16).pack(pady=4)

        # ── Main area ─────────────────────────────────────────────────────────
        main_area = tk.Frame(self, bg=config.THEME_BG)
        main_area.pack(side="right", fill="both", expand=True)

        # Title bar
        title_bar = tk.Frame(main_area, bg=config.ACCENT, height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="Project-Based on Harmful Object & Violence Detection",
                 bg=config.ACCENT, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(expand=True)

        # Welcome panel
        self._welcome_frame = tk.Frame(main_area, bg=config.THEME_BG)
        self._welcome_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self._build_welcome(self._welcome_frame)

        # Status bar
        self._status_var = tk.StringVar(value="Ready. Click 'Start Detection' to begin.")
        status_bar = tk.Label(main_area, textvariable=self._status_var,
                              bg="#0d0d1a", fg="#80a0c0",
                              font=config.FONT_MONO, anchor="w", padx=12)
        status_bar.pack(fill="x", side="bottom", ipady=4)

    def _build_welcome(self, parent):
        cards = [
            ("🎥", "Object+Violence Detection", "Live Webcam Feed", "Knife & Violence (best.pt + best2.pt)"),
            ("📧", "Email Alert",               "Dual Detection",   "Knife + Violence Required"),
        ]
        tk.Label(parent, text="System Overview", bg=config.THEME_BG,
                 fg="white", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        tk.Label(parent,
                 text="Upload a violence video, then click Start Detection.",
                 bg=config.THEME_BG, fg="#a0b0c0",
                 font=("Segoe UI", 10)).pack(pady=(0, 20))

        grid = tk.Frame(parent, bg=config.THEME_BG)
        grid.pack()
        for i, (icon, title, sub1, sub2) in enumerate(cards):
            card = tk.Frame(grid, bg=config.ACCENT2, padx=16, pady=14,
                            width=200, height=140)
            card.grid(row=0, column=i, padx=10, pady=6)
            card.grid_propagate(False)
            tk.Label(card, text=icon,    bg=config.ACCENT2, fg="white",
                     font=("Segoe UI", 22)).pack()
            tk.Label(card, text=title,   bg=config.ACCENT2, fg="white",
                     font=("Segoe UI", 10, "bold")).pack()
            tk.Label(card, text=sub1,    bg=config.ACCENT2, fg="#a0c0e0",
                     font=("Segoe UI", 8)).pack()
            tk.Label(card, text=sub2,    bg=config.ACCENT2, fg="#a0c0e0",
                     font=("Segoe UI", 8)).pack()

        # Quick-action buttons in welcome
        btn_row = tk.Frame(parent, bg=config.THEME_BG)
        btn_row.pack(pady=24)
        styled_button(btn_row, "▶  Start Detection", self._start_detection,
                      config.ACCENT, 20).pack(side="left", padx=8)
        # Upload Video button removed – detection now uses single webcam only

    # ──────────────────────────────────────────────────────────────────────────
    def _start_detection(self):
        from gui.Integration import IntegrationWindow
        if self._det_window and self._det_window.winfo_exists():
            self._det_window.lift()
            self._det_window.start()
            return
        self._det_window = IntegrationWindow(self,
                                             operator_email=self._operator_email,
                                             role=self._role)
        self._det_window.start()
        self._status_var.set("Detection window opened – both models running on webcam.")

    def _stop_detection(self):
        if self._det_window and self._det_window.winfo_exists():
            self._det_window.stop()
            self._status_var.set("Detection stopped.")
        else:
            messagebox.showinfo("Info", "No active detection session.")

    def _view_speed_profile(self):
        """Open a live-updating speed profiling window."""
        from utils.profiler import profiler as _prof

        win = tk.Toplevel(self)
        win.title("⏱ Speed Profile Report")
        win.geometry("700x420")
        win.configure(bg=config.THEME_BG)

        tk.Label(win, text="⏱  Speed Profile", bg=config.THEME_BG,
                 fg="white", font=config.FONT_TITLE).pack(pady=(10, 2))
        tk.Label(win, text="Timing for each pipeline step (updates every 2 sec)",
                 bg=config.THEME_BG, fg="#80a0c0",
                 font=("Segoe UI", 9)).pack()

        frame = tk.Frame(win, bg=config.THEME_BG)
        frame.pack(fill="both", expand=True, padx=12, pady=8)

        # Header row
        hdr = tk.Frame(frame, bg=config.ACCENT2)
        hdr.pack(fill="x", pady=(0, 4))
        for col, w in [("Operation", 22), ("Avg (ms)", 10),
                       ("Min (ms)", 10), ("Max (ms)", 10), ("Calls", 8)]:
            tk.Label(hdr, text=col, bg=config.ACCENT2, fg="white",
                     font=("Segoe UI", 9, "bold"),
                     width=w, anchor="w").pack(side="left", padx=4, pady=4)

        # Data rows
        row_frames = {}
        ordered = ["camera_read", "knife_inference",
                   "violence_inference", "snapshot_save", "gui_render"]
        colors   = {
            "camera_read":        "#4a9eff",
            "knife_inference":    "#00c850",
            "violence_inference": "#ff4444",
            "snapshot_save":      "#ffaa00",
            "gui_render":         "#cc80ff",
        }
        for key in ordered:
            rf = tk.Frame(frame, bg="#12122a")
            rf.pack(fill="x", pady=1)
            color = colors.get(key, "white")
            label = key.replace("_", " ").title()
            tk.Label(rf, text=label, bg="#12122a", fg=color,
                     font=config.FONT_MONO, width=22, anchor="w").pack(
                         side="left", padx=4, pady=3)
            vars_ = {}
            for col in ["avg_ms", "min_ms", "max_ms", "count"]:
                v = tk.StringVar(value="-")
                vars_[col] = v
                tk.Label(rf, textvariable=v, bg="#12122a", fg="#e0e0e0",
                         font=config.FONT_MONO, width=10,
                         anchor="w").pack(side="left", padx=4)
            row_frames[key] = vars_

        # Reset button
        def _reset():
            _prof.reset()
        styled_button(win, "🔄  Reset Stats", _reset, "#555577", 14).pack(pady=6)

        # Live update loop
        def _refresh():
            if not win.winfo_exists():
                return
            rep = _prof.report()
            for key, vars_ in row_frames.items():
                if key in rep:
                    d = rep[key]
                    vars_["avg_ms"].set(f"{d['avg_ms']:.2f}")
                    vars_["min_ms"].set(f"{d['min_ms']:.2f}")
                    vars_["max_ms"].set(f"{d['max_ms']:.2f}")
                    vars_["count"].set(str(d["count"]))
                else:
                    for v in vars_.values():
                        v.set("-")
            win.after(2000, _refresh)   # refresh every 2 seconds

        _refresh()

    # ────────────────────────────────────────────────────────────────────
    def _view_alerts(self):
        self._show_table("Detections Log", db_manager.fetch_detections(),
                         ["id", "type", "label", "confidence", "status", "timestamp"])

    def _view_recordings(self):
        self._show_table("Recordings", db_manager.fetch_recordings(),
                         ["id", "file_path", "duration_sec", "timestamp"])

    def _view_snapshots(self):
        """Open a snapshot browser — click any row to open the image."""
        snaps = db_manager.fetch_snapshots()
        win = tk.Toplevel(self)
        win.title("View Snapshots")
        win.geometry("860x500")
        win.configure(bg=config.THEME_BG)

        tk.Label(win, text="📸  Snapshots", bg=config.THEME_BG,
                 fg="white", font=config.FONT_TITLE).pack(pady=8)
        tk.Label(win, text="Double-click a row to open the image.",
                 bg=config.THEME_BG, fg="#80a0c0",
                 font=("Segoe UI", 9)).pack()

        columns = ["id", "file_path", "detection_type", "timestamp"]
        frame = tk.Frame(win, bg=config.THEME_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=8)

        style = ttk.Style()
        style.configure("Snap.Treeview",
                         background="#1a1a2e", foreground="white",
                         fieldbackground="#1a1a2e", rowheight=26)
        style.configure("Snap.Treeview.Heading",
                         background=config.ACCENT2, foreground="white")

        tree = ttk.Treeview(frame, columns=columns, show="headings",
                             style="Snap.Treeview")
        tree.heading("id",             text="ID")
        tree.heading("file_path",      text="File Path")
        tree.heading("detection_type", text="Type")
        tree.heading("timestamp",      text="Timestamp")
        tree.column("id",             width=40,  anchor="center")
        tree.column("file_path",      width=420, anchor="w")
        tree.column("detection_type", width=100, anchor="center")
        tree.column("timestamp",      width=160, anchor="center")

        for row in snaps:
            tree.insert("", "end",
                        values=[row.get(c, "") for c in columns],
                        tags=(row.get("file_path", ""),))

        def _open_snapshot(event):
            item = tree.focus()
            if not item:
                return
            vals = tree.item(item, "values")
            if not vals:
                return
            path = vals[1]          # file_path column
            if not os.path.isfile(path):
                messagebox.showwarning("Not Found",
                    f"File not found:\n{path}", parent=win)
                return
            # Open image in new window
            img_win = tk.Toplevel(win)
            img_win.title(os.path.basename(path))
            img_win.configure(bg="black")
            try:
                img  = Image.open(path)
                img.thumbnail((900, 700), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl   = tk.Label(img_win, image=photo, bg="black")
                lbl.image = photo          # keep reference
                lbl.pack(padx=8, pady=8)
                tk.Label(img_win, text=path,
                         bg="black", fg="#80a0c0",
                         font=("Segoe UI", 8)).pack(pady=(0, 6))
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=img_win)

        tree.bind("<Double-1>", _open_snapshot)

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

    # ──────────────────────────────────────────────────────────────────────────
    def _view_object_log(self):
        self._show_log_file("Object Detection Log", config.LOG_FILE_KNIFE)

    def _view_violence_log(self):
        self._show_log_file("Violence Detection Log", config.LOG_FILE_VIOLENCE)

    def _show_log_file(self, title: str, log_path: str):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("860x500")
        win.configure(bg=config.THEME_BG)
        tk.Label(win, text=title, bg=config.THEME_BG,
                 fg="white", font=config.FONT_TITLE).pack(pady=8)
        frame = tk.Frame(win, bg=config.THEME_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        txt = tk.Text(frame, bg="#0d0d1a", fg="#a0e0a0",
                      font=config.FONT_MONO, relief="flat", wrap="none")
        sb_y = ttk.Scrollbar(frame, orient="vertical",   command=txt.yview)
        sb_x = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")
        txt.pack(fill="both", expand=True)
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                txt.insert("end", f.read())
        else:
            txt.insert("end", "No log entries yet.")
        txt.config(state="disabled")

    def _show_table(self, title: str, rows: list, columns: list):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("900x500")
        win.configure(bg=config.THEME_BG)
        tk.Label(win, text=title, bg=config.THEME_BG,
                 fg="white", font=config.FONT_TITLE).pack(pady=8)
        frame = tk.Frame(win, bg=config.THEME_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        style = ttk.Style()
        style.configure("Custom.Treeview",
                         background="#1a1a2e", foreground="white",
                         fieldbackground="#1a1a2e", rowheight=26)
        style.configure("Custom.Treeview.Heading",
                         background=config.ACCENT2, foreground="white")
        tree = ttk.Treeview(frame, columns=columns, show="headings",
                            style="Custom.Treeview")
        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=120, anchor="w")
        for row in rows:
            tree.insert("", "end", values=[row.get(c, "") for c in columns])
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.destroy()
            self._on_logout()

    def _exit_app(self):
        if messagebox.askyesno("Exit", "Exit the application?"):
            self.master.destroy()
