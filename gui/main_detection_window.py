"""
gui/main_detection_window.py
──────────────────────────────────────────────────────────────────────────────
Dual-panel detection window with 8 concurrent threads:
  Thread 1 – CameraCapture
  Thread 2 – VideoPlayback
  Thread 3 – YOLODetection
  Thread 4 – ViolenceDetection
  Thread 5 – HRMValidation
  Thread 6 – RecordingThread   (inside RecordingService)
  Thread 7 – EmailAlertThread  (inside email_service)
  Thread 8 – GUI Update        (via root.after polling)
──────────────────────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import queue
import time
import cv2
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger
from utils.helpers import cv2_to_imagetk, blank_frame, timestamp_display
from database import db_manager
from gui.widgets import (styled_button, status_label, section_label,
                         video_canvas, panel_frame, AlertBanner)
from services.recording_service import RecordingService
from services.alert_service import AlertService

logger = get_logger("main_detection_window")


class MainDetectionWindow(tk.Toplevel):
    """Main dual-panel detection window."""

    GUI_POLL_MS   = 33   # ~30 fps GUI refresh
    MAX_Q_SIZE    = 8    # keep queues small to avoid lag

    def __init__(self, master):
        super().__init__(master)
        self.title(config.APP_TITLE)
        self.configure(bg=config.THEME_BG)
        self.state("zoomed")                 # start maximised
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── State ──────────────────────────────────────────────────────────
        self._running          = False
        self._video_path: str  = ""

        # ── Queues (thread pipelines) ──────────────────────────────────────
        self._cam_q          = queue.Queue(maxsize=self.MAX_Q_SIZE)  # raw cam → YOLO
        self._cam_display_q  = queue.Queue(maxsize=2)                # raw cam → GUI (tiny, always fresh)
        self._vid_q          = queue.Queue(maxsize=self.MAX_Q_SIZE)  # raw video frames
        self._yolo_q         = queue.Queue(maxsize=self.MAX_Q_SIZE)  # annotated → HRM only
        self._viol_q         = queue.Queue(maxsize=self.MAX_Q_SIZE)  # annotated violence frames
        self._hrm_q          = queue.Queue(maxsize=self.MAX_Q_SIZE)  # HRM results → GUI right panel

        # Last YOLO annotated frame – GUI overlays this on raw cam frames
        self._last_annotated_cam = None
        self._last_annotated_lock = threading.Lock()

        # ── AI models (loaded lazily in threads) ───────────────────────────
        self._yolo_det    = None
        self._viol_det    = None
        self._hrm_knife   = None
        self._hrm_viol    = None
        self._models_ready: threading.Event = threading.Event()

        # ── Services ──────────────────────────────────────────────────────
        self._rec_svc    = RecordingService()
        self._alert_svc  = AlertService(
            recording_service=self._rec_svc,
            email_sent_callback=self._on_email_result,
        )

        # ── Status tracking ────────────────────────────────────────────────
        self._knife_conf  = 0.0
        self._viol_conf   = 0.0
        self._knife_label = "Scanning..."
        self._viol_label  = "Scanning..."
        self._fps_cam     = 0.0
        self._fps_vid     = 0.0
        self._email_status = ""

        # ── Build GUI ─────────────────────────────────────────────────────
        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════════
    # GUI BUILD
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self, bg=config.ACCENT, height=44)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)
        tk.Label(title_bar,
                 text="🛡  AI Surveillance – Knife & Violence Detection",
                 bg=config.ACCENT, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(expand=True)

        # Alert banner
        self._alert_banner = AlertBanner(self)
        self._alert_banner.pack(fill="x")

        # ── Two video panels ────────────────────────────────────────────────
        panels_outer = tk.Frame(self, bg=config.THEME_BG)
        panels_outer.pack(fill="both", expand=True, padx=8, pady=4)

        # LEFT panel
        left_frame = panel_frame(panels_outer)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        section_label(left_frame, "🔪  Knife Detection  [Live Webcam]").pack(fill="x")
        self._left_canvas = video_canvas(left_frame, config.PANEL_W, config.PANEL_H)
        self._left_canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._left_status = tk.StringVar(value="Webcam not started")
        self._left_info   = tk.StringVar(value="")
        status_label(left_frame, textvariable=self._left_status).pack(fill="x", padx=6)
        status_label(left_frame, textvariable=self._left_info,
                     fg=config.ACCENT).pack(fill="x", padx=6)

        # RIGHT panel
        right_frame = panel_frame(panels_outer)
        right_frame.pack(side="right", fill="both", expand=True, padx=(4, 0))
        section_label(right_frame, "⚡  Violence Detection  [Uploaded Video]").pack(fill="x")
        self._right_canvas = video_canvas(right_frame, config.PANEL_W, config.PANEL_H)
        self._right_canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self._right_status = tk.StringVar(value="No video loaded")
        self._right_info   = tk.StringVar(value="")
        status_label(right_frame, textvariable=self._right_status).pack(fill="x", padx=6)
        status_label(right_frame, textvariable=self._right_info,
                     fg=config.ACCENT).pack(fill="x", padx=6)

        # ── Control bar ─────────────────────────────────────────────────────
        ctrl = tk.Frame(self, bg=config.ACCENT2, height=58)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        styled_button(ctrl, "▶  START",        self.start,        config.ACCENT,   14).pack(side="left",  padx=10, pady=10)
        styled_button(ctrl, "⏹  STOP",         self.stop,         "#8b0000",       12).pack(side="left",  padx=4,  pady=10)
        styled_button(ctrl, "📂  Upload Video", self.upload_video, "#1a6030",       16).pack(side="left",  padx=4,  pady=10)
        styled_button(ctrl, "✖  Close",         self._on_close,    "#555577",       12).pack(side="right", padx=10, pady=10)

        self._video_label_var = tk.StringVar(value="No video loaded")
        tk.Label(ctrl, textvariable=self._video_label_var,
                 bg=config.ACCENT2, fg="#a0c0e0",
                 font=("Segoe UI", 9)).pack(side="left", padx=8)

        # ── Status bar ──────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(self, textvariable=self._status_var,
                 bg="#0d0d1a", fg="#80a0c0",
                 font=config.FONT_MONO, anchor="w", padx=10).pack(
                     fill="x", side="bottom", ipady=3)

        # Show blank frames
        self._show_blank_left("Webcam feed – press START")
        self._show_blank_right("Upload video – press START")

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════
    def upload_video(self):
        path = filedialog.askopenfilename(
            title="Select Violence Detection Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                       ("All files", "*.*")]
        )
        if path:
            self._video_path = path
            fname = os.path.basename(path)
            self._video_label_var.set(f"📹  {fname}")
            self._right_status.set(f"Loaded: {fname}")
            self._show_blank_right(f"Video ready: {fname}\nPress START to play")
            logger.info(f"Video selected: {path}")

    def start(self):
        if self._running:
            logger.warning("Already running")
            return
        if not self._video_path:
            messagebox.showwarning(
                "Video Required",
                "Please select a violence video before starting detection.\n\n"
                "Click 'Upload Video' to browse."
            )
            return
        self._running = True
        self._alert_svc.reset()
        if self._hrm_knife:
            self._hrm_knife.reset()
        if self._hrm_viol:
            self._hrm_viol.reset()
        self._status_var.set("Starting threads…")
        self._start_threads()
        self._gui_update_loop()

    def stop(self):
        self._running = False
        self._status_var.set("Stopped.")
        self._right_status.set("Stopped.")
        self._left_status.set("Stopped.")
        self._alert_banner.hide()
        logger.info("Detection stopped by user.")

    # ══════════════════════════════════════════════════════════════════════════
    # THREADING
    # ══════════════════════════════════════════════════════════════════════════
    def _start_threads(self):
        threads = [
            threading.Thread(target=self._thread_load_models,
                             name="ModelLoader", daemon=True),
        ]
        for t in threads:
            t.start()

    def _thread_load_models(self):
        """Load AI models, then spawn the remaining worker threads."""
        try:
            from ai_models.yolo_detector  import YOLODetector
            from ai_models.violence_detector import ViolenceDetector
            from ai_models.hrm_validator   import HRMValidator

            self._yolo_det  = YOLODetector()
            self._viol_det  = ViolenceDetector()
            self._hrm_knife = HRMValidator(mode="knife")
            self._hrm_viol  = HRMValidator(mode="violence")

            self._yolo_det.load()
            self._viol_det.load()
            self._models_ready.set()
            logger.info("All models loaded. Starting worker threads.")
        except Exception as e:
            logger.error(f"Model loading failed: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror(
                "Model Error", f"Failed to load AI models:\n{e}"))
            self._running = False
            return

        worker_threads = [
            threading.Thread(target=self._thread_camera_capture,
                             name="CameraCapture",   daemon=True),
            threading.Thread(target=self._thread_video_playback,
                             name="VideoPlayback",   daemon=True),
            threading.Thread(target=self._thread_yolo_detection,
                             name="YOLODetection",   daemon=True),
            threading.Thread(target=self._thread_violence_detection,
                             name="ViolenceDetection", daemon=True),
            threading.Thread(target=self._thread_hrm_validation,
                             name="HRMValidation",   daemon=True),
        ]
        for t in worker_threads:
            t.start()

    # Thread 1 – Camera Capture
    def _thread_camera_capture(self):
        self._models_ready.wait()
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not cap.isOpened():
            logger.warning(f"Cannot open camera index {config.CAMERA_INDEX}")
            self.after(0, lambda: self._left_status.set("Camera not available"))
            return
        cap.set(cv2.CAP_PROP_FPS, 30)
        logger.info("Camera capture thread started")
        t_prev = time.time()
        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            now = time.time()
            self._fps_cam = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now

            def _q_put(q, item):
                """Drop oldest item if queue is full, then push new item."""
                try:
                    q.put_nowait(item)
                except queue.Full:
                    try: q.get_nowait()
                    except queue.Empty: pass
                    try: q.put_nowait(item)
                    except queue.Full: pass

            _q_put(self._cam_q, frame)            # → YOLO detection
            _q_put(self._cam_display_q, frame)    # → GUI display (raw, always live)
        cap.release()
        logger.info("Camera capture thread stopped")

    # Thread 2 – Video Playback
    def _thread_video_playback(self):
        self._models_ready.wait()
        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {self._video_path}")
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_delay = 1.0 / fps
        logger.info(f"Video playback thread started (FPS={fps:.1f})")
        t_prev = time.time()
        while self._running:
            t_start = time.time()
            ret, frame = cap.read()
            if not ret:
                # Loop the video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            now = time.time()
            self._fps_vid = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now
            try:
                self._vid_q.put_nowait(frame)
            except queue.Full:
                try:
                    self._vid_q.get_nowait()
                    self._vid_q.put_nowait(frame)
                except queue.Empty:
                    pass
            elapsed = time.time() - t_start
            sleep_t  = frame_delay - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)
        cap.release()
        logger.info("Video playback thread stopped")

    # Thread 3 – YOLO Detection
    def _thread_yolo_detection(self):
        self._models_ready.wait()
        logger.info("YOLO detection thread started")
        while self._running:
            try:
                frame = self._cam_q.get(timeout=0.5)
            except queue.Empty:
                continue
            result = self._yolo_det.detect(frame)

            # Store annotated frame so the GUI can overlay it on live raw frames
            with self._last_annotated_lock:
                self._last_annotated_cam = result.get("annotated_frame", frame)

            # _yolo_q is consumed ONLY by HRM – GUI no longer competes here
            try:
                self._yolo_q.put_nowait((frame, result))
            except queue.Full:
                try:
                    self._yolo_q.get_nowait()
                    self._yolo_q.put_nowait((frame, result))
                except queue.Empty:
                    pass
        logger.info("YOLO detection thread stopped")

    # Thread 4 – Violence Detection
    def _thread_violence_detection(self):
        self._models_ready.wait()
        logger.info("Violence detection thread started")
        while self._running:
            try:
                frame = self._vid_q.get(timeout=0.5)
            except queue.Empty:
                continue
            result = self._viol_det.predict(frame)
            # Feed frame into recording service always (recorder picks up on demand)
            self._rec_svc.enqueue_frame(frame)
            try:
                self._viol_q.put_nowait((frame, result))
            except queue.Full:
                try:
                    self._viol_q.get_nowait()
                    self._viol_q.put_nowait((frame, result))
                except queue.Empty:
                    pass
        logger.info("Violence detection thread stopped")

    # Thread 5 – HRM Validation
    def _thread_hrm_validation(self):
        self._models_ready.wait()
        logger.info("HRM validation thread started")
        while self._running:
            k_done = v_done = False

            # Knife HRM
            try:
                frame, det_result = self._yolo_q.get_nowait()
                hrm_k = self._hrm_knife.validate_knife(det_result)
                self._knife_conf  = det_result.get("max_confidence", 0.0)
                self._knife_label = (
                    f"🔴 KNIFE {self._knife_conf:.0%}" if det_result.get("knife_detected")
                    else "🟢 Safe"
                )
                if hrm_k.get("confirmed"):
                    self._alert_svc.handle_knife_detection(
                        frame, hrm_k,
                        db_log_fn=lambda p, t, c: db_manager.log_snapshot(p, t, c)
                    )
                    db_manager.log_detection("knife", "knife",
                                             hrm_k["confidence"],
                                             status="confirmed")
                k_done = True
            except queue.Empty:
                pass

            # Violence HRM
            try:
                frame, viol_result = self._viol_q.get_nowait()
                hrm_v = self._hrm_viol.validate_violence(viol_result)
                self._viol_conf  = viol_result.get("confidence", 0.0)
                self._viol_label = (
                    f"🔴 VIOLENCE {self._viol_conf:.0%}"
                    if viol_result.get("violence_detected")
                    else f"🟢 Non-Violence {1-self._viol_conf:.0%}"
                )
                try:
                    self._hrm_q.put_nowait((frame, viol_result, hrm_v))
                except queue.Full:
                    try:
                        self._hrm_q.get_nowait()
                        self._hrm_q.put_nowait((frame, viol_result, hrm_v))
                    except queue.Empty:
                        pass
                if hrm_v.get("confirmed"):
                    self._alert_svc.handle_violence_detection(
                        frame, hrm_v,
                        db_log_fn=lambda p, t, c: db_manager.log_snapshot(p, t, c)
                    )
                    db_manager.log_detection("violence", "violence",
                                             hrm_v["confidence"],
                                             status="confirmed")
                v_done = True
            except queue.Empty:
                pass

            if not k_done and not v_done:
                time.sleep(0.01)
        logger.info("HRM validation thread stopped")

    # Thread 8 – GUI Update (via tkinter .after() polling)
    def _gui_update_loop(self):
        if not self._running:
            return

        # ── Left panel (knife) – read RAW cam frame at 30fps, overlay last detection
        try:
            raw_frame = self._cam_display_q.get_nowait()
            # Use the latest annotated frame if available, otherwise show raw
            with self._last_annotated_lock:
                display_frame = (self._last_annotated_cam
                                 if self._last_annotated_cam is not None
                                 else raw_frame)
            self._render_to_canvas(self._left_canvas, display_frame)
            fps_txt = f"FPS: {self._fps_cam:.1f}  |  {self._knife_label}"
            self._left_status.set(fps_txt)
            if self._knife_conf > 0.0:
                self._left_info.set(f"Confidence: {self._knife_conf:.1%}")
            else:
                self._left_info.set("")
        except queue.Empty:
            pass

        # ── Right panel (violence) ───────────────────────────────────────
        try:
            frame, viol_result, hrm_v = self._hrm_q.get_nowait()
            annotated = viol_result.get("annotated_frame", frame)
            self._render_to_canvas(self._right_canvas, annotated)
            fps_txt = f"FPS: {self._fps_vid:.1f}  |  {self._viol_label}"
            self._right_status.set(fps_txt)
            if viol_result.get("violence_detected"):
                self._right_info.set(
                    f"Confidence: {self._viol_conf:.1%}  |  HRM: {'✓' if hrm_v.get('confirmed') else '…'}"
                )
                if hrm_v.get("confirmed"):
                    self._alert_banner.show()
            else:
                self._right_info.set(f"Confidence: {1-self._viol_conf:.1%}")
                self._alert_banner.hide()
        except queue.Empty:
            pass

        # ── Status bar ───────────────────────────────────────────────────
        now = timestamp_display()
        rec_tag = " [REC●]" if self._rec_svc.is_recording else ""
        self._status_var.set(
            f"{now}{rec_tag}  |  Cam: {self._fps_cam:.1f} fps  |  "
            f"Vid: {self._fps_vid:.1f} fps  |  {self._email_status}"
        )

        self.after(self.GUI_POLL_MS, self._gui_update_loop)

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _render_to_canvas(self, canvas: tk.Canvas, frame):
        w = canvas.winfo_width()  or config.PANEL_W
        h = canvas.winfo_height() or config.PANEL_H
        try:
            photo = cv2_to_imagetk(frame, w, h)
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=photo)
            canvas._photo = photo          # prevent GC
        except Exception as e:
            logger.warning(f"Canvas render error: {e}")

    def _show_blank_left(self, text=""):
        frame = blank_frame(config.PANEL_W, config.PANEL_H, text)
        self._render_to_canvas(self._left_canvas, frame)

    def _show_blank_right(self, text=""):
        frame = blank_frame(config.PANEL_W, config.PANEL_H, text)
        self._render_to_canvas(self._right_canvas, frame)

    def _on_email_result(self, success: bool, message: str):
        self._email_status = f"Email {'✓ Sent' if success else '✗ Failed'}"
        logger.info(f"Email callback: {message}")

    def _on_close(self):
        self.stop()
        self.destroy()
