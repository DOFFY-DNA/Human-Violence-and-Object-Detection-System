"""
gui/Integration.py
──────────────────────────────────────────────────────────────────────────────
Single-window, single-webcam, dual-YOLO live detection.

  ONE camera feed → both best.pt (knife) and best2.pt (violence) detect
  simultaneously → their bounding boxes are merged on ONE display frame.

Threading pipeline:
  Thread 1 – CameraCapture  : reads webcam → raw_q
  Thread 2 – KnifeModel     : best.pt  inference on latest frame
  Thread 3 – ViolenceModel  : best2.pt inference on latest frame
  Thread 4 – GUI (after)    : merges both results onto raw frame → canvas
──────────────────────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time
import cv2
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import cv2_to_imagetk, blank_frame, timestamp_str, ensure_dir
from gui.widgets import styled_button, status_label, section_label, video_canvas, AlertBanner
from database import db_manager
from services.email_service import send_direct_alert

logger = get_logger("integration")
from utils.logger   import get_event_logger
from utils.profiler import profiler as _profiler
_knife_evt_log    = get_event_logger("knife")
_violence_evt_log = get_event_logger("violence")

# ─── Safe-copy helper (apostrophe-safe .pt path for ultralytics) ───────────
_TEMP_DIR = ""

def _safe_copy(src: str) -> str:
    global _TEMP_DIR
    if not _TEMP_DIR:
        _TEMP_DIR = tempfile.mkdtemp(prefix="surv_int_")
    dst = os.path.join(_TEMP_DIR, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return dst


KNIFE_MODEL_PATH    = os.path.join(config.BASE_DIR, "models", "best.pt")
VIOLENCE_MODEL_PATH = os.path.join(config.BASE_DIR, "models", "best2.pt")
KNIFE_CONF          = 0.55
VIOLENCE_CONF       = 0.55


class IntegrationWindow(tk.Toplevel):
    """
    One Tkinter window / one camera / both YOLO models.
    Both sets of bounding boxes are drawn on the same displayed frame.
    """
    GUI_POLL_MS = 33   # ~30 fps

    def __init__(self, master, operator_email: str = "", role: str = "admin"):
        super().__init__(master)
        self.title("AI Surveillance – Live Detection")
        self.configure(bg=config.THEME_BG)
        self.geometry("860x620")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build recipient list based on role:
        #   operator → [operator_email, admin_email]  (both get alert)
        #   admin    → [admin_email]                   (only admin)
        admin_email = config.EMAIL_RECEIVER
        if role == "operator" and operator_email:
            self._alert_emails = [operator_email, admin_email]
        else:
            self._alert_emails = [admin_email]

        self._running = False

        # Latest raw frame from camera (shared between both detector threads)
        self._latest_raw   = None
        self._raw_lock     = threading.Lock()

        # Latest results from each detector (boxes list from ultralytics)
        self._knife_boxes  = []   # list of ultralytics Box objects
        self._viol_boxes   = []
        self._knife_names  = {}   # class id → name
        self._viol_names   = {}
        self._res_lock     = threading.Lock()

        # FPS
        self._fps_cam   = 0.0
        self._fps_knife = 0.0
        self._fps_viol  = 0.0

        # Models
        self._knife_model  = None
        self._viol_model   = None
        self._models_ready = threading.Event()

        # ── Alert cooldown & per-session email cap ──────────────────────────
        # Each key = "knife" / "violence" / "both", value = last sent timestamp
        self._alert_cooldown: dict   = {}   # type → last sent time
        self._alert_interval         = 60   # seconds between emails per type
        self._alert_lock             = threading.Lock()
        self._email_status           = ""
        # Max 2 emails per detection type per session (knife=2, violence=2)
        self._email_count: dict      = {}   # type → number sent this session
        self._email_max              = 2    # hard cap per type per session

        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self, bg=config.ACCENT, height=44)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar,
                 text="🛡  Surveillance –  Live Detection",
                 bg=config.ACCENT, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(expand=True)

        # Alert banner
        self._alert_banner = AlertBanner(self)
        self._alert_banner.pack(fill="x")

        # Single video canvas
        self._canvas = video_canvas(self, config.PANEL_W, config.PANEL_H)
        self._canvas.pack(fill="both", expand=True, padx=10, pady=(6, 2))

        # Legend row
        legend = tk.Frame(self, bg=config.THEME_BG)
        legend.pack(fill="x", padx=10)
        tk.Label(legend, text="🟢 Knife (best.pt)   🔴 Violence (best2.pt)   🔵 Non-Violence (best2.pt)",
                 bg=config.THEME_BG, fg="#a0c0e0",
                 font=("Segoe UI", 9)).pack(side="left")

        # Status
        self._status_var = tk.StringVar(value="Ready. Click START.")
        tk.Label(self, textvariable=self._status_var,
                 bg="#0d0d1a", fg="#80a0c0",
                 font=config.FONT_MONO, anchor="w", padx=10
                 ).pack(fill="x", ipady=3)

        # Controls
        ctrl = tk.Frame(self, bg=config.ACCENT2, height=52)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)
        styled_button(ctrl, "▶  START", self.start,     config.ACCENT, 14).pack(side="left", padx=10, pady=8)
        styled_button(ctrl, "⏹  STOP",  self.stop,      "#8b0000",     12).pack(side="left", padx=4,  pady=8)
        styled_button(ctrl, "✖  Close", self._on_close, "#555577",     12).pack(side="right", padx=10, pady=8)

        self._render(blank_frame(config.PANEL_W, config.PANEL_H, "Press START"))

    # ══════════════════════════════════════════════════════════════════════════
    def start(self):
        if self._running:
            return
        self._running = True
        self._status_var.set("Loading models…")
        threading.Thread(target=self._thread_load_models,
                         name="ModelLoader", daemon=True).start()
        self._gui_poll()

    def stop(self):
        self._running = False
        self._status_var.set("Stopped.")
        self._alert_banner.hide()

    # ══════════════════════════════════════════════════════════════════════════
    # THREADS
    # ══════════════════════════════════════════════════════════════════════════
    def _thread_load_models(self):
        try:
            from ultralytics import YOLO
            logger.info("Loading knife model (best.pt)…")
            self._knife_model = YOLO(_safe_copy(KNIFE_MODEL_PATH))
            self._knife_names = self._knife_model.names
            logger.info("Loading violence model (best2.pt)…")
            self._viol_model  = YOLO(_safe_copy(VIOLENCE_MODEL_PATH))
            self._viol_names  = self._viol_model.names
            self._models_ready.set()
            self.after(0, lambda: self._status_var.set("Models ready – webcam starting…"))
            logger.info("Both models loaded.")
        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Model Error", str(e)))
            self._running = False
            return

        for name, target in [
            ("Camera",    self._thread_camera),
            ("Knife",     self._thread_knife),
            ("Violence",  self._thread_violence),
        ]:
            threading.Thread(target=target, name=name, daemon=True).start()

    # Thread 1 – Camera (stores latest frame in shared variable)
    def _thread_camera(self):
        self._models_ready.wait()
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not cap.isOpened():
            self.after(0, lambda: self._status_var.set("❌ Cannot open camera"))
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        t_prev = time.time()
        while self._running:
            with _profiler.measure("camera_read"):
                ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue
            now = time.time()
            self._fps_cam = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now
            with self._raw_lock:
                self._latest_raw = frame
        cap.release()

    # Thread 2 – Knife model (best.pt) — polls latest raw frame
    def _thread_knife(self):
        self._models_ready.wait()
        t_prev = time.time()
        while self._running:
            with self._raw_lock:
                frame = self._latest_raw
            if frame is None:
                time.sleep(0.01)
                continue
            try:
                with _profiler.measure("knife_inference"):
                    res = self._knife_model.predict(frame, conf=KNIFE_CONF, verbose=False)
                boxes = res[0].boxes
                with self._res_lock:
                    self._knife_boxes = boxes if boxes is not None else []
                if boxes and len(boxes) > 0:
                    top_conf = float(boxes.conf[0])
                    self.after(0, self._alert_banner.show)
                    self._trigger_alert("knife", frame, top_conf)
                    db_manager.log_detection("knife", "knife", top_conf, status="detected")
                    _knife_evt_log.info(
                        f"OBJECT DETECTED | conf={top_conf:.1%} | frame saved")
            except Exception as e:
                logger.warning(f"Knife inference: {e}")
            now = time.time()
            self._fps_knife = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now

    # Thread 3 – Violence model (best2.pt) — polls latest raw frame
    def _thread_violence(self):
        self._models_ready.wait()
        t_prev = time.time()
        while self._running:
            with self._raw_lock:
                frame = self._latest_raw
            if frame is None:
                time.sleep(0.01)
                continue
            try:
                with _profiler.measure("violence_inference"):
                    res = self._viol_model.predict(frame, conf=VIOLENCE_CONF, verbose=False)
                boxes = res[0].boxes
                with self._res_lock:
                    self._viol_boxes = boxes if boxes is not None else []
                if boxes and len(boxes) > 0:
                    # Only alert on actual violence (not non-violence class)
                    viol_detected = any(
                        "non" not in self._viol_names.get(int(b.cls[0]), "").lower()
                        for b in boxes
                    )
                    if viol_detected:
                        top_conf = float(boxes.conf[0])
                        self.after(0, self._alert_banner.show)
                        self._trigger_alert("violence", frame, top_conf)
                        db_manager.log_detection("violence", "violence", top_conf, status="detected")
                        _violence_evt_log.info(
                            f"VIOLENCE DETECTED | conf={top_conf:.1%} | frame saved")
                    else:
                        self.after(0, self._alert_banner.hide)
                else:
                    self.after(0, self._alert_banner.hide)
            except Exception as e:
                logger.warning(f"Violence inference: {e}")
            now = time.time()
            self._fps_viol = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now

    # ──────────────────────────────────────────────────────────────────────────
    def _trigger_alert(self, det_type: str, frame, confidence: float):
        """
        Send an email alert for the given detection type ("knife" or "violence").
        Respects a per-type cooldown of self._alert_interval seconds.
        Also checks if both knife+violence are currently active → sends "both" alert.
        """
        now = time.time()
        with self._alert_lock:
            # Check if both are detected simultaneously
            knife_active = len(self._knife_boxes) > 0 if hasattr(self._knife_boxes, '__len__') else False
            viol_active  = len(self._viol_boxes)  > 0 if hasattr(self._viol_boxes,  '__len__') else False

            if knife_active and viol_active:
                alert_key = "both"
            else:
                alert_key = det_type

            last_sent = self._alert_cooldown.get(alert_key, 0)
            if now - last_sent < self._alert_interval:
                return   # still in cooldown

            # Enforce per-session max-2 email cap per type
            if self._email_count.get(alert_key, 0) >= self._email_max:
                return   # already sent max emails for this type this session

            self._alert_cooldown[alert_key] = now
            self._email_count[alert_key] = self._email_count.get(alert_key, 0) + 1

        # Save snapshot to disk AND record in database
        snapshots = []
        try:
            ensure_dir(config.ALERTS_DIR)
            snap_path = os.path.join(
                config.ALERTS_DIR, f"{alert_key}_{timestamp_str()}.jpg")
            with _profiler.measure("snapshot_save"):
                cv2.imwrite(snap_path, frame)
            snapshots = [snap_path]
            db_manager.log_snapshot(snap_path, alert_key, confidence)
            logger.info(f"Snapshot saved + logged: {snap_path}")
        except Exception as e:
            logger.warning(f"Snapshot failed: {e}")

        # Send email in background
        def _cb(success, msg):
            status = "✅ Email sent" if success else f"❌ Email failed: {msg}"
            self._email_status = status
            logger.info(f"Alert email [{alert_key}]: {status}")

        send_direct_alert(
            detection_type  = alert_key,
            snapshots       = snapshots,
            confidence      = confidence,
            receiver_emails = self._alert_emails,   # operator + admin or admin only
            callback        = _cb,
        )
        logger.warning(f"Alert triggered: {alert_key.upper()} | conf={confidence:.0%} → {self._alert_emails}")

    # ══════════════════════════════════════════════════════════════════════════
    # GUI POLL — merge boxes from both models onto one frame
    # ══════════════════════════════════════════════════════════════════════════
    def _gui_poll(self):
        if not self._running:
            return

        with self._raw_lock:
            frame = self._latest_raw

        if frame is not None:
            display = frame.copy()

            with self._res_lock:
                knife_boxes = self._knife_boxes
                viol_boxes  = self._viol_boxes

            # Draw knife detections in GREEN
            if knife_boxes is not None:
                for box in knife_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf  = float(box.conf[0])
                    cls   = int(box.cls[0])
                    label = f"{self._knife_names.get(cls, 'obj')}  {conf:.0%}"
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 200, 0), 2)
                    cv2.putText(display, label, (x1, max(y1 - 6, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 2)

            # Draw violence/non-violence detections — RED = violence, BLUE = non-violence
            if viol_boxes is not None:
                for box in viol_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf  = float(box.conf[0])
                    cls   = int(box.cls[0])
                    label = f"{self._viol_names.get(cls, 'violence')}  {conf:.0%}"
                    # Blue for non-violence, Red for violence
                    is_nonviolence = "non" in label.lower()
                    color = (220, 80, 0) if is_nonviolence else (0, 0, 220)
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(display, label, (x1, max(y1 - 6, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            # FPS overlay (top-right corner)
            fps_text = (f"Cam {self._fps_cam:.0f}fps | "
                        f"Knife {self._fps_knife:.0f}fps | "
                        f"Violence {self._fps_viol:.0f}fps")
            cv2.putText(display, fps_text, (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

            with _profiler.measure("gui_render"):
                self._render(display)

        self._status_var.set(
            f"▶ Running  |  Cam: {self._fps_cam:.1f} fps  |  "
            f"Knife: {self._fps_knife:.1f} fps  |  "
            f"Violence: {self._fps_viol:.1f} fps"
            + (f"  |  {self._email_status}" if self._email_status else "")
        )
        self.after(self.GUI_POLL_MS, self._gui_poll)

    # ══════════════════════════════════════════════════════════════════════════
    def _render(self, frame):
        w = self._canvas.winfo_width()  or config.PANEL_W
        h = self._canvas.winfo_height() or config.PANEL_H
        try:
            photo = cv2_to_imagetk(frame, w, h)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            self._canvas._photo = photo
        except Exception as e:
            logger.warning(f"Render error: {e}")

    def _on_close(self):
        self.stop()
        self.destroy()
