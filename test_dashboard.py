"""
test_dashboard.py
Full Tkinter Test Dashboard for AI Surveillance System.
─────────────────────────────────────────────────────────────────────────────
Features:
  ● Run All Tests / individual module buttons
  ● Live results table with PASS (green) / FAIL (red) / SKIP (yellow)
  ● Execution time per test
  ● Summary: Total / Passed / Failed / Skipped
  ● GPU usage via nvidia-smi (subprocess)
  ● RAM usage via psutil
  ● Export report to text file
  ● Threading so UI never freezes
─────────────────────────────────────────────────────────────────────────────
Run: python test_dashboard.py
"""
import sys, os, time, threading, subprocess, platform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import config

# ── Color palette ─────────────────────────────────────────────────────────────
BG      = "#0d0d1a"
SIDEBAR = "#0f3460"
ACCENT  = "#e94560"
PANEL   = "#1a1a2e"
FG      = "#e0e0e0"
GREEN   = "#00c850"
RED     = "#ff4444"
YELLOW  = "#ffcc00"
BLUE    = "#4a9eff"
MONO    = ("Consolas", 10)
TITLE   = ("Segoe UI", 13, "bold")
BODY    = ("Segoe UI", 10)


# ── GPU + RAM helpers ─────────────────────────────────────────────────────────
def _gpu_stats() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            timeout=5, stderr=subprocess.DEVNULL
        ).decode().strip()
        parts = [p.strip() for p in out.split(",")]
        return (f"GPU: {parts[0]}%  |  "
                f"VRAM: {parts[1]}/{parts[2]} MiB  |  "
                f"Temp: {parts[3]}°C")
    except Exception:
        return "GPU: nvidia-smi not available"

def _ram_stats() -> str:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return (f"RAM: {vm.used//1024//1024} MB used / "
                f"{vm.total//1024//1024} MB total  "
                f"({vm.percent}%)")
    except ImportError:
        return "RAM: psutil not installed (pip install psutil)"
    except Exception as e:
        return f"RAM: {e}"


# ── Dashboard Window ──────────────────────────────────────────────────────────
class TestDashboard(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("AI Surveillance – Test Dashboard")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._results_store = {}   # module → [(name, status, ms)]
        self._running       = False
        self._build_ui()
        self._refresh_sys_stats()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"1100x700+{(sw-1100)//2}+{(sh-700)//2}")

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Left sidebar
        sidebar = tk.Frame(self, bg=SIDEBAR, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🧪", bg=SIDEBAR, fg=FG,
                 font=("Segoe UI", 30)).pack(pady=(20, 0))
        tk.Label(sidebar, text="Test Dashboard", bg=SIDEBAR, fg=FG,
                 font=("Segoe UI", 12, "bold")).pack(pady=(0, 4))
        tk.Label(sidebar, text="AI Surveillance System", bg=SIDEBAR, fg="#607090",
                 font=("Segoe UI", 8)).pack(pady=(0, 16))

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10)

        # Module buttons
        modules = [
            ("🔑 Login & Auth",      "Login & Auth"),
            ("📷 Camera",            "Camera"),
            ("🤖 YOLO Detection",    "YOLO Detection"),
            ("📧 Email Service",     "Email Service"),
            ("🗄  Database",         "Database"),
            ("🔀 Threading",         "Threading"),
            ("🖥  GUI",              "GUI"),
        ]
        for label, mod_key in modules:
            btn = tk.Button(sidebar, text=label,
                            command=lambda k=mod_key: self._run_module(k),
                            bg=SIDEBAR, fg=FG, activebackground="#1a4580",
                            activeforeground=FG, relief="flat",
                            font=("Segoe UI", 10), anchor="w",
                            padx=14, pady=8, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#1a4580"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=SIDEBAR))

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10, pady=10)

        tk.Button(sidebar, text="▶  Run All Tests",
                  command=self._run_all,
                  bg=ACCENT, fg="white", activebackground="#c73650",
                  relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=14, pady=10, cursor="hand2").pack(fill="x", padx=10, pady=2)
        tk.Button(sidebar, text="💾  Export Report",
                  command=self._export_report,
                  bg="#555577", fg="white", activebackground="#777799",
                  relief="flat", font=("Segoe UI", 10),
                  padx=14, pady=8, cursor="hand2").pack(fill="x", padx=10, pady=2)
        tk.Button(sidebar, text="🗑  Clear Results",
                  command=self._clear_results,
                  bg="#333355", fg="white", activebackground="#555577",
                  relief="flat", font=("Segoe UI", 10),
                  padx=14, pady=8, cursor="hand2").pack(fill="x", padx=10, pady=2)

        # Right main area
        main = tk.Frame(self, bg=BG)
        main.pack(side="right", fill="both", expand=True)

        # Title bar
        title_bar = tk.Frame(main, bg=ACCENT, height=44)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="AI Surveillance System — Test Dashboard",
                 bg=ACCENT, fg="white", font=TITLE).pack(expand=True)

        # System stats bar
        self._stats_var = tk.StringVar(value="Loading system stats…")
        tk.Label(main, textvariable=self._stats_var,
                 bg="#080814", fg=BLUE, font=MONO,
                 anchor="w", padx=10).pack(fill="x", ipady=3)

        # Results tree
        tree_frame = tk.Frame(main, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        style = ttk.Style()
        style.configure("Dash.Treeview",
                         background=PANEL, foreground=FG,
                         fieldbackground=PANEL, rowheight=24,
                         font=MONO)
        style.configure("Dash.Treeview.Heading",
                         background=SIDEBAR, foreground=FG,
                         font=("Segoe UI", 10, "bold"))
        style.map("Dash.Treeview",
                  background=[("selected", "#2a2a5a")],
                  foreground=[("selected", "white")])

        cols = ("Module", "Test Name", "Status", "Time (ms)")
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                   show="headings", style="Dash.Treeview")
        self._tree.heading("Module",    text="Module")
        self._tree.heading("Test Name", text="Test Name")
        self._tree.heading("Status",    text="Status")
        self._tree.heading("Time (ms)", text="Time (ms)")
        self._tree.column("Module",    width=130, anchor="w")
        self._tree.column("Test Name", width=340, anchor="w")
        self._tree.column("Status",    width=120, anchor="center")
        self._tree.column("Time (ms)", width=90,  anchor="center")

        # Color tags
        self._tree.tag_configure("PASS", foreground=GREEN)
        self._tree.tag_configure("FAIL", foreground=RED)
        self._tree.tag_configure("SKIP", foreground=YELLOW)

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        # Summary bar
        sum_bar = tk.Frame(main, bg="#080814", height=36)
        sum_bar.pack(fill="x", side="bottom")
        sum_bar.pack_propagate(False)
        self._sum_var = tk.StringVar(value="Run tests to see summary.")
        tk.Label(sum_bar, textvariable=self._sum_var,
                 bg="#080814", fg=FG, font=MONO,
                 anchor="w", padx=10).pack(fill="both", expand=True)

        # Status bar
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(main, textvariable=self._status_var,
                 bg=PANEL, fg="#80a0c0", font=MONO,
                 anchor="w", padx=10).pack(fill="x", side="bottom", ipady=3)

    # ── System stats ──────────────────────────────────────────────────────────
    def _refresh_sys_stats(self):
        def _fetch():
            gpu = _gpu_stats()
            ram = _ram_stats()
            self.after(0, lambda: self._stats_var.set(f"{gpu}   |   {ram}"))
        threading.Thread(target=_fetch, daemon=True).start()
        self.after(5000, self._refresh_sys_stats)

    # ── Run all tests ─────────────────────────────────────────────────────────
    def _run_all(self):
        if self._running:
            return
        self._running = True
        self._status_var.set("⏳ Running all tests…")
        threading.Thread(target=self._run_all_worker, daemon=True).start()

    def _run_all_worker(self):
        try:
            from tests.test_runner import run_all
            all_results = run_all()
            self.after(0, lambda: self._display_results(all_results))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._running = False
            self.after(0, lambda: self._status_var.set("✅ All tests complete."))

    # ── Run single module ─────────────────────────────────────────────────────
    def _run_module(self, module_key: str):
        if self._running:
            return
        self._running = True
        self._status_var.set(f"⏳ Running: {module_key}…")

        def _worker():
            mod_map = {
                "Login & Auth":   "tests.test_login",
                "Camera":         "tests.test_camera",
                "YOLO Detection": "tests.test_detection",
                "Email Service":  "tests.test_email",
                "Database":       "tests.test_database",
                "Threading":      "tests.test_threading",
                "GUI":            "tests.test_gui",
            }
            try:
                import importlib
                mod = importlib.import_module(mod_map[module_key])
                results = mod.run_tests()
                self.after(0, lambda: self._display_results({module_key: results}))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self._running = False
                self.after(0, lambda: self._status_var.set(f"✅ {module_key} done."))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Display results ───────────────────────────────────────────────────────
    def _display_results(self, all_results: dict):
        for mod_name, results in all_results.items():
            self._results_store[mod_name] = results

        # Rebuild tree
        for item in self._tree.get_children():
            self._tree.delete(item)

        total = passed = failed = skipped = 0
        for mod_name, results in self._results_store.items():
            for name, status, ms in results:
                total += 1
                if "PASS"  in status: passed  += 1; tag = "PASS"
                elif "SKIP" in status: skipped += 1; tag = "SKIP"
                else:                  failed  += 1; tag = "FAIL"
                short_status = status[:4] if len(status) >= 4 else status
                self._tree.insert("", "end",
                                  values=(mod_name, name, short_status, f"{ms:.2f}"),
                                  tags=(tag,))

        self._sum_var.set(
            f"  Total: {total}   |   "
            f"✅ Passed: {passed}   |   "
            f"❌ Failed: {failed}   |   "
            f"⚠ Skipped: {skipped}"
        )

    # ── Export report ─────────────────────────────────────────────────────────
    def _export_report(self):
        if not self._results_store:
            messagebox.showinfo("Export", "No results to export. Run tests first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="test_report.txt",
            title="Save Test Report"
        )
        if not path:
            return
        try:
            from tests.test_runner import export_report
            export_report(self._results_store, path)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ── Clear results ─────────────────────────────────────────────────────────
    def _clear_results(self):
        self._results_store.clear()
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._sum_var.set("Results cleared.")
        self._status_var.set("Ready.")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = TestDashboard()
    app.mainloop()
