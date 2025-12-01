from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from controller.models import ControllerLogEntry


import logging
logger = logging.getLogger(__name__)


# Default location for the controller log JSONL file
DEFAULT_LOG_PATH = Path("log") / "controller_log.jsonl"


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
    log_path: Optional[Path] = None,
) -> ControllerLogEntry:
    """
    Build a ControllerLogEntry and append it as a JSON line to the log file.

    - Log file is JSONL at log/controller_log.jsonl (by default).
    - Decimals and dates are serialized to strings.
    """
    if log_path is None:
        log_path = DEFAULT_LOG_PATH

    if context is None:
        context = {}

    entry = ControllerLogEntry(
        id=str(uuid4()),
        run_id=run_id,
        user_id=user_id,
        timestamp=datetime.utcnow(),
        level=level,
        source=source,
        message=message,
        context=context,
    )

    # Ensure parent directory exists (e.g. "log/")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = asdict(entry)
    line = json.dumps(entry_dict, default=_json_default)

    logger.debug(
        "Appending ControllerLogEntry to %s at %s",
        log_path,
        entry.timestamp.isoformat(),
    )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    return entry
