"""Central logging setup for local and Linux deployments."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = BACKEND_ROOT / "logs"
DEFAULT_LOG_FILE = "app.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 7
DEFAULT_LOG_LEVEL = "INFO"


def _get_int_env(name: str, default: int) -> int:
    """Read a positive integer from environment variables."""
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def get_log_file_path() -> Path:
    """Return the configured application log file path."""
    log_dir = os.getenv("APP_LOG_DIR")
    if log_dir:
        log_dir_path = Path(log_dir)
        if not log_dir_path.is_absolute():
            log_dir_path = BACKEND_ROOT / log_dir_path
    else:
        log_dir_path = DEFAULT_LOG_DIR

    log_file = os.getenv("APP_LOG_FILE", DEFAULT_LOG_FILE)
    return log_dir_path / log_file


def configure_logging() -> Path:
    """Configure rotating file logging and return the active log path."""
    log_file_path = get_log_file_path()
    root_logger = logging.getLogger()

    if getattr(root_logger, "_booksource_logging_configured", False):
        return log_file_path

    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    level_name = os.getenv("APP_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=_get_int_env("APP_LOG_MAX_BYTES", DEFAULT_MAX_BYTES),
        backupCount=_get_int_env("APP_LOG_BACKUP_COUNT", DEFAULT_BACKUP_COUNT),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    file_handler._booksource_file_handler = True
    root_logger.addHandler(file_handler)

    if os.getenv("APP_LOG_CONSOLE", "true").lower() in {"1", "true", "yes", "on"}:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        console_handler._booksource_console_handler = True
        root_logger.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    root_logger._booksource_logging_configured = True
    logging.getLogger(__name__).info("日志系统已启动: %s", log_file_path)
    return log_file_path


def get_logger(name: str) -> logging.Logger:
    """Return a named logger after application logging is configured."""
    configure_logging()
    return logging.getLogger(name)
