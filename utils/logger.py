"""utils/logger.py – Rotating file + console logger.
Provides:
  get_logger(name)        → general app logger → logs/app.log
  get_event_logger(type)  → event-specific logger
                             knife    → logs/object_detection.log
                             violence → logs/violence_detection.log
"""
import logging
import logging.handlers
import os
import sys


def get_logger(name: str = "surveillance") -> logging.Logger:
    import config
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (rotating)
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def get_event_logger(event_type: str) -> logging.Logger:
    """
    Returns a dedicated logger for 'knife' or 'violence' events.
    Writes only to its own log file (no console spam).
    """
    import config
    name_map = {
        "knife":    ("evt_knife",    config.LOG_FILE_KNIFE),
        "violence": ("evt_violence", config.LOG_FILE_VIOLENCE),
        "both":     ("evt_knife",    config.LOG_FILE_KNIFE),   # "both" also written to knife log
    }
    logger_name, log_path = name_map.get(event_type, ("evt_knife", config.LOG_FILE_KNIFE))

    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False   # don't bubble up to root logger

    fmt = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
