"""
config.py – Central configuration for the AI Surveillance System.
Edit EMAIL_* fields before running.
"""
import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR   = os.path.join(BASE_DIR, "models")
YOLO_MODEL     = os.path.join(MODEL_DIR, "best.pt")
#VIOLENCE_MODEL = os.path.join(MODEL_DIR, "new_violence_model_finetuned_rwf.pth")

DB_PATH        = os.path.join(BASE_DIR, "database", "surveillance.db")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
ALERTS_DIR     = os.path.join(BASE_DIR, "alerts")
LOGS_DIR       = os.path.join(BASE_DIR, "logs")

# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0

# ─── Detection Thresholds ─────────────────────────────────────────────────────
YOLO_CONF_THRESHOLD      = 0.80   # Minimum YOLO confidence to consider a detection
VIOLENCE_CONF_THRESHOLD  = 0.80   # Minimum violence confidence
HRM_FRAMES_REQUIRED      = 3      # Consecutive frames needed for HRM confirmation
HRM_IOU_THRESHOLD        = 0.70   # BBox stability IOU threshold
VIOLENCE_WINDOW_FRAMES   = 16     # Frames fed to violence model

# ─── Recording ────────────────────────────────────────────────────────────────
CLIP_DURATION_SEC   = 5
VIDEO_FPS           = 20
VIDEO_WIDTH         = 640
VIDEO_HEIGHT        = 480

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_ENABLED   = True
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
EMAIL_SENDER    = "SENDER EMAIL"        # ← Change this
EMAIL_PASSWORD  = "PASSWORD"      # ← Change this (Gmail App Password)
EMAIL_RECEIVER  = "RECEIVER EMAIL"    # ← Change this
EMAIL_SUBJECT   = "CRITICAL ALERT: Knife and Violence Detected"

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE            = os.path.join(LOGS_DIR, "app.log")
LOG_FILE_KNIFE      = os.path.join(LOGS_DIR, "object_detection.log")
LOG_FILE_VIOLENCE   = os.path.join(LOGS_DIR, "violence_detection.log")
LOG_MAX_BYTES       = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT    = 3

# ─── GUI ──────────────────────────────────────────────────────────────────────
APP_TITLE   = "AI Surveillance System – Knife & Violence Detection"
PANEL_W     = 640
PANEL_H     = 480
THEME_BG    = "#1a1a2e"
THEME_FG    = "#e0e0e0"
ACCENT      = "#e94560"
ACCENT2     = "#0f3460"
FONT_MAIN   = ("Segoe UI", 11)
FONT_TITLE  = ("Segoe UI", 15, "bold")
FONT_MONO   = ("Consolas", 10)

# ─── Ensure dirs exist ────────────────────────────────────────────────────────
for _d in (RECORDINGS_DIR, ALERTS_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)
