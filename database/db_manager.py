"""database/db_manager.py – SQLite database manager for the surveillance system."""
import sqlite3
import threading
import bcrypt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("db_manager")
_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create tables and seed default admin user."""
    with _lock:
        conn = get_connection()
        c = conn.cursor()

        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'admin',
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS operators (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT    NOT NULL,
            gender        TEXT    NOT NULL,
            mobile        TEXT    NOT NULL,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            email         TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS detections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            type          TEXT,
            label         TEXT,
            confidence    REAL,
            frame_path    TEXT,
            status        TEXT,
            timestamp     TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_id  INTEGER,
            email_to      TEXT,
            sent_at       TEXT,
            status        TEXT    DEFAULT 'pending',
            FOREIGN KEY (detection_id) REFERENCES detections(id)
        );

        CREATE TABLE IF NOT EXISTS recordings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path     TEXT,
            duration_sec  REAL,
            timestamp     TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path     TEXT,
            detection_type TEXT,
            confidence    REAL,
            timestamp     TEXT    DEFAULT (datetime('now'))
        );
        """)
        conn.commit()

        # Seed default admin if not exists
        c.execute("SELECT id FROM users WHERE username = 'admin'")
        if not c.fetchone():
            pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            c.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", pw_hash, "admin")
            )
            conn.commit()
            logger.info("Default admin user seeded (admin / admin123)")
        conn.close()


def verify_user(username: str, password: str) -> bool:
    """Check admin users table only."""
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
    if not row:
        return False
    return bcrypt.checkpw(password.encode(), row["password_hash"].encode())


def verify_operator(username: str, password: str):
    """
    Check operators table.
    Returns operator dict (id, username, email, full_name …) on success, None on failure.
    """
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM operators WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
    if not row:
        return None
    if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return dict(row)
    return None


def register_operator(full_name: str, gender: str, mobile: str,
                      username: str, password: str, email: str) -> tuple:
    """
    Register a new operator.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        # Check username uniqueness across both tables
        c.execute("SELECT id FROM users    WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return False, "Username already exists."
        c.execute("SELECT id FROM operators WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return False, "Username already exists."
        try:
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            c.execute(
                "INSERT INTO operators "
                "(full_name, gender, mobile, username, password_hash, email) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (full_name, gender, mobile, username, pw_hash, email)
            )
            conn.commit()
            logger.info(f"Operator registered: {username} ({email})")
            return True, ""
        except Exception as e:
            logger.error(f"register_operator error: {e}")
            return False, str(e)
        finally:
            conn.close()


def get_operator_email(username: str) -> str:
    """Return the email of a registered operator, or empty string."""
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT email FROM operators WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
    return row["email"] if row else ""


def log_detection(det_type: str, label: str, confidence: float,
                  frame_path: str = "", status: str = "detected") -> int:
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO detections (type, label, confidence, frame_path, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (det_type, label, round(confidence, 4), frame_path, status)
        )
        det_id = c.lastrowid
        conn.commit()
        conn.close()
    return det_id


def log_alert(detection_id: int, email_to: str, status: str = "sent"):
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        from utils.helpers import timestamp_display
        c.execute(
            "INSERT INTO alerts (detection_id, email_to, sent_at, status) VALUES (?,?,?,?)",
            (detection_id, email_to, timestamp_display(), status)
        )
        conn.commit()
        conn.close()


def log_recording(file_path: str, duration_sec: float):
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO recordings (file_path, duration_sec) VALUES (?, ?)",
            (file_path, duration_sec)
        )
        conn.commit()
        conn.close()


def log_snapshot(file_path: str, detection_type: str, confidence: float):
    with _lock:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO snapshots (file_path, detection_type, confidence) VALUES (?,?,?)",
            (file_path, detection_type, round(confidence, 4))
        )
        conn.commit()
        conn.close()


def fetch_detections(limit: int = 100):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def fetch_recordings(limit: int = 100):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM recordings ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def fetch_snapshots(limit: int = 100):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
