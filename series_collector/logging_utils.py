"""Local-only application logging and diagnostic reports."""

from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from series_collector import __version__


LOGGER_NAME = "series_collector"


def default_log_path() -> Path:
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Logs"
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / "Serien-Sammler" / "app.log"


def configure_logging(log_file: Optional[Path] = None) -> Path:
    path = (log_file or default_log_path()).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    resolved = str(path.resolve())
    if not any(isinstance(handler, RotatingFileHandler) and handler.baseFilename == resolved for handler in logger.handlers):
        handler = RotatingFileHandler(path, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.info("Serien-Sammler %s started on %s", __version__, platform.platform())
    return path


def save_diagnostic_report(destination: Path, log_path: Optional[Path] = None) -> None:
    source = log_path or default_log_path()
    try:
        log_text = source.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        log_text = f"Log unavailable: {error}"
    header = [
        "Serien-Sammler diagnostic report",
        f"Created: {datetime.now(timezone.utc).isoformat()}",
        f"Version: {__version__}",
        f"Python: {platform.python_version()}",
        f"System: {platform.platform()}",
        f"Log file: {source}",
        "Telemetry: disabled",
        "",
        "--- Application log ---",
    ]
    destination.write_text("\n".join(header) + "\n" + log_text, encoding="utf-8")
