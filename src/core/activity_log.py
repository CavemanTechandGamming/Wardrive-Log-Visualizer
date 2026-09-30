"""Plain-English activity log next to the app install.

The file lives under ``logs/activity.log`` beside the portable install (or the
project root when run from source). Lines are meant for a person to read — not
stack traces.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "activity.log"


def install_root() -> Path:
    """Folder that holds the app (exe directory, or repo root from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/core/activity_log.py → repo / install root is parents[2]
    return Path(__file__).resolve().parents[2]


def activity_log_path() -> Path:
    return install_root() / LOG_DIR_NAME / LOG_FILE_NAME


def _local_stamp() -> str:
    now = datetime.now()
    hour = now.hour % 12 or 12
    return f"{now.year:04d}-{now.month:02d}-{now.day:02d} {hour}:{now.minute:02d} {now.strftime('%p')}"


def log_activity(message: str) -> None:
    """Append one human-readable line with a local timestamp."""
    text = message.strip()
    if not text:
        return
    line = f"{_local_stamp()} — {text}\n"
    path = activity_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
    except OSError:
        # Never break the UI because the log file could not be written.
        return


def clear_activity_log() -> bool:
    """Erase the activity log file. Returns True if it worked."""
    path = activity_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return True
    except OSError:
        return False


def open_activity_log() -> bool:
    """Open the activity log in the system default viewer. Creates it if missing."""
    import os
    import subprocess

    path = activity_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():
            path.write_text("", encoding="utf-8")
    except OSError:
        return False
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except OSError:
        return False
