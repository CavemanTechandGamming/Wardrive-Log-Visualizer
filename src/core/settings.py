"""Local app settings stored as XML beside the install.

Never commit ``settings.xml`` — it can hold API keys. The file lives next to
the portable exe (or the project root when run from source).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from src.core.activity_log import install_root
from src.core.wigle_csv import DEFAULT_MAX_LINES_PER_PART, MIN_MAX_LINES_PER_PART

SETTINGS_FILE_NAME = "settings.xml"

# Inbox pulse: default 1 minute; floor 10 seconds; ceiling 1 hour.
DEFAULT_INBOX_PULSE_SECONDS = 60
MIN_INBOX_PULSE_SECONDS = 10
MAX_INBOX_PULSE_SECONDS = 60 * 60

_HMS = re.compile(r"^(\d{1,2}):(\d{1,2}):(\d{1,2})$")


@dataclass
class AppSettings:
    """Values the Settings window edits. Secrets stay on disk only."""

    wigle_api_name: str = ""
    wigle_api_token: str = ""
    wdgwars_api_key: str = ""
    raw_logs_folder: str = ""
    combined_logs_folder: str = ""
    max_lines_per_part: int = DEFAULT_MAX_LINES_PER_PART
    inbox_pulse_seconds: int = DEFAULT_INBOX_PULSE_SECONDS


def settings_path() -> Path:
    return install_root() / SETTINGS_FILE_NAME


def load_settings() -> AppSettings:
    path = settings_path()
    if not path.is_file():
        return AppSettings()
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError):
        return AppSettings()
    root = tree.getroot()
    pulse_text = _text(root, "inbox/pulse_hhmmss").strip()
    if pulse_text:
        try:
            pulse = parse_hhmmss(pulse_text)
        except ValueError:
            pulse = DEFAULT_INBOX_PULSE_SECONDS
    else:
        pulse = _int(
            root, "inbox/pulse_seconds", DEFAULT_INBOX_PULSE_SECONDS, clamp=False
        )
        pulse = clamp_inbox_pulse_seconds(pulse)
    return AppSettings(
        wigle_api_name=_text(root, "wigle/api_name"),
        wigle_api_token=_text(root, "wigle/api_token"),
        wdgwars_api_key=_text(root, "wdgwars/api_key"),
        raw_logs_folder=_text(root, "folders/raw_logs"),
        combined_logs_folder=_text(root, "folders/combined_logs"),
        max_lines_per_part=_int(
            root, "split/max_lines_per_part", DEFAULT_MAX_LINES_PER_PART
        ),
        inbox_pulse_seconds=pulse,
    )


def save_settings(settings: AppSettings) -> None:
    pulse = clamp_inbox_pulse_seconds(settings.inbox_pulse_seconds)
    root = ET.Element("settings")
    wigle = ET.SubElement(root, "wigle")
    ET.SubElement(wigle, "api_name").text = settings.wigle_api_name
    ET.SubElement(wigle, "api_token").text = settings.wigle_api_token
    wdg = ET.SubElement(root, "wdgwars")
    ET.SubElement(wdg, "api_key").text = settings.wdgwars_api_key
    folders = ET.SubElement(root, "folders")
    ET.SubElement(folders, "raw_logs").text = settings.raw_logs_folder
    ET.SubElement(folders, "combined_logs").text = settings.combined_logs_folder
    split = ET.SubElement(root, "split")
    ET.SubElement(split, "max_lines_per_part").text = str(
        clamp_max_lines_per_part(settings.max_lines_per_part)
    )
    inbox = ET.SubElement(root, "inbox")
    ET.SubElement(inbox, "pulse_hhmmss").text = format_hhmmss(pulse)
    ET.SubElement(inbox, "pulse_seconds").text = str(pulse)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def clamp_max_lines_per_part(value: int) -> int:
    """Keep the hard line cap at least meta + header + one data row."""
    return max(MIN_MAX_LINES_PER_PART, value)


def clamp_inbox_pulse_seconds(value: int) -> int:
    """Keep the inbox pulse between 10 seconds and 1 hour."""
    return min(MAX_INBOX_PULSE_SECONDS, max(MIN_INBOX_PULSE_SECONDS, value))


def format_hhmmss(total_seconds: int) -> str:
    """Format clamped seconds as ``HH:MM:SS``."""
    seconds = clamp_inbox_pulse_seconds(total_seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_hhmmss(text: str) -> int:
    """Parse ``H:MM:SS`` / ``HH:MM:SS`` into clamped seconds."""
    match = _HMS.fullmatch(text.strip())
    if not match:
        raise ValueError("Use HH:MM:SS (hours:minutes:seconds).")
    hours = int(match.group(1), 10)
    minutes = int(match.group(2), 10)
    secs = int(match.group(3), 10)
    if minutes > 59 or secs > 59:
        raise ValueError("Minutes and seconds must be 0–59.")
    total = hours * 3600 + minutes * 60 + secs
    if total < MIN_INBOX_PULSE_SECONDS:
        raise ValueError(
            f"Minimum pulse is {format_hhmmss(MIN_INBOX_PULSE_SECONDS)}."
        )
    if total > MAX_INBOX_PULSE_SECONDS:
        raise ValueError(
            f"Maximum pulse is {format_hhmmss(MAX_INBOX_PULSE_SECONDS)}."
        )
    return total


def _text(root: ET.Element, path: str) -> str:
    node = root.find(path)
    if node is None or node.text is None:
        return ""
    return node.text


def _int(
    root: ET.Element,
    path: str,
    default: int,
    *,
    clamp: bool = True,
) -> int:
    text = _text(root, path).strip()
    if not text:
        return default
    try:
        value = int(text, 10)
    except ValueError:
        return default
    if clamp:
        return clamp_max_lines_per_part(value)
    return value
