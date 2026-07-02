"""
services/email_service.py
SMTP email alert service. Sends email with knife snapshots,
violence snapshots, and a 5-second recorded video clip.
Email is sent ONLY when both knife AND violence are confirmed.
"""
import os
import sys
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("email_service")


def _attach_file(msg: MIMEMultipart, filepath: str):
    if not filepath or not os.path.isfile(filepath):
        return
    with open(filepath, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(filepath)}"',
    )
    msg.attach(part)


def send_alert_email(
    knife_snapshots: list,
    violence_snapshots: list,
    video_clip_path: str,
    detection_info: dict,
    callback=None,
):
    """
    Build and send the alert email with all attachments.
    Runs in a background thread to avoid blocking the GUI.
    """
    def _send():
        if not config.EMAIL_ENABLED:
            logger.info("Email disabled in config; skipping.")
            if callback:
                callback(False, "Email disabled")
            return

        try:
            msg = MIMEMultipart()
            msg["From"]    = config.EMAIL_SENDER
            msg["To"]      = config.EMAIL_RECEIVER
            msg["Subject"] = config.EMAIL_SUBJECT

            body = f"""
CRITICAL SECURITY ALERT
========================
Both KNIFE and VIOLENCE detected simultaneously!

Detection Time  : {detection_info.get('timestamp', 'N/A')}
Knife Confidence: {detection_info.get('knife_confidence', 0):.1%}
Violence Confidence: {detection_info.get('violence_confidence', 0):.1%}
Knife Status    : {detection_info.get('knife_status', 'Confirmed')}
Violence Status : {detection_info.get('violence_status', 'Confirmed')}

Attachments:
  - {len(knife_snapshots)} Knife snapshot(s)
  - {len(violence_snapshots)} Violence snapshot(s)
  - 1 Violence video clip (5 seconds)

This is an automated alert from the AI Surveillance System.
Please review the attachments immediately.
"""
            msg.attach(MIMEText(body, "plain"))

            # Attach snapshots
            for snap in knife_snapshots[:4]:
                _attach_file(msg, snap)
            for snap in violence_snapshots[:4]:
                _attach_file(msg, snap)

            # Attach video clip
            _attach_file(msg, video_clip_path)

            # Send via SMTP TLS
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
                server.sendmail(
                    config.EMAIL_SENDER,
                    config.EMAIL_RECEIVER,
                    msg.as_string(),
                )
            logger.info(f"Alert email sent to {config.EMAIL_RECEIVER}")
            if callback:
                callback(True, "Email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            if callback:
                callback(False, str(e))

    t = threading.Thread(target=_send, name="EmailAlertThread", daemon=True)
    t.start()
    return t


def send_direct_alert(
    detection_type: str,           # "knife", "violence", or "both"
    snapshots: list,               # list of snapshot file paths
    confidence: float = 0.0,
    receiver_emails: list = None,  # list of emails to send to
    callback=None,
):
    """
    Send an alert email for ANY single detection (knife, violence, or both).
    Sends to all addresses in receiver_emails.
    Runs in a background thread.
    """
    if receiver_emails is None:
        receiver_emails = []
    # Filter empty strings; always include admin fallback if list is empty
    targets = [e for e in receiver_emails if e]
    if not targets:
        targets = [config.EMAIL_RECEIVER]
    def _send():
        if not config.EMAIL_ENABLED:
            logger.info("Email disabled in config; skipping.")
            if callback:
                callback(False, "Email disabled")
            return
        try:
            label_map = {
                "knife":    "⚠️ KNIFE / Object Detected",
                "violence": "⚠️ VIOLENCE Detected",
                "both":     "🚨 KNIFE + VIOLENCE Detected",
            }
            subject = label_map.get(detection_type, "⚠️ Security Alert")

            msg = MIMEMultipart()
            msg["From"]    = config.EMAIL_SENDER
            msg["To"]      = ", ".join(targets)
            msg["Subject"] = subject

            from utils.helpers import timestamp_display
            body = f"""
SECURITY ALERT — AI Surveillance System
========================================
Detection Type : {detection_type.upper()}
Time           : {timestamp_display()}

{snapshots and f'{len(snapshots)} snapshot(s) attached.' or 'No snapshots attached.'}

This is an automated alert. Please review immediately.
"""
            msg.attach(MIMEText(body, "plain"))
            for snap in snapshots[:4]:
                _attach_file(msg, snap)

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
                server.sendmail(config.EMAIL_SENDER, targets, msg.as_string())

            logger.info(f"Direct alert email sent ({detection_type}) → {targets}")
            if callback:
                callback(True, "Email sent")
        except Exception as e:
            logger.error(f"Direct alert email failed: {e}", exc_info=True)
            if callback:
                callback(False, str(e))

    t = threading.Thread(target=_send, name="DirectAlertThread", daemon=True)
    t.start()
    return t
