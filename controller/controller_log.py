from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from controller.models import ControllerLogEntry


import logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Path Logic (Updated for Docker)
# ---------------------------------------------------------------------
if os.getenv("APP_HOME"):
    BASE_DIR = Path(os.getenv("APP_HOME"))
else:
    # Fallback to relative 'log' folder in CWD if env var not set
    BASE_DIR = Path(".")

# Default location for the controller log JSONL file
DEFAULT_LOG_PATH = BASE_DIR / "log" / "controller_log.jsonl"


def _json_default(obj: Any) -> Any:
    """
    Serializer for types that are not JSON-serializable by default.

    - Decimal -> str
    - date/datetime -> ISO string
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


def append_log_entry(
    *,
    message: str,
    level: str = "INFO",
    source: str = "controller",
    run_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    log_path: Path = DEFAULT_LOG_PATH,
) -> None:
    """
    Appends a structured log entry to the JSONL log file.
    """
    entry = ControllerLogEntry(
        entry_id=str(uuid4()),
        timestamp=datetime.now(),
        level=level.upper(),
        source=source,
        message=message,
        run_id=run_id,
        user_id=user_id,
        context=context or {},
    )

    # Ensure parent directory exists
    if not log_path.parent.exists():
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create log directory {log_path.parent}: {e}")
            return

    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), default=_json_default) + "\n")
    except OSError as e:
        logger.error(f"Failed to write to controller log at {log_path}: {e}")
