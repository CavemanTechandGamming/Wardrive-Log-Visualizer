"""Local app settings stored as XML beside the install.

Never commit ``settings.xml`` — it can hold API keys. The file lives next to
the portable exe (or the project root when run from source).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from src.core.activity_log import install_root

SETTINGS_FILE_NAME = "settings.xml"


@dataclass
class AppSettings:
    """Values the Settings window edits. Secrets stay on disk only."""

    wigle_api_name: str = ""
    wigle_api_token: str = ""
    wdgwars_api_key: str = ""
    raw_logs_folder: str = ""
    combined_logs_folder: str = ""


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
    return AppSettings(
        wigle_api_name=_text(root, "wigle/api_name"),
        wigle_api_token=_text(root, "wigle/api_token"),
        wdgwars_api_key=_text(root, "wdgwars/api_key"),
        raw_logs_folder=_text(root, "folders/raw_logs"),
        combined_logs_folder=_text(root, "folders/combined_logs"),
    )


def save_settings(settings: AppSettings) -> None:
    root = ET.Element("settings")
    wigle = ET.SubElement(root, "wigle")
    ET.SubElement(wigle, "api_name").text = settings.wigle_api_name
    ET.SubElement(wigle, "api_token").text = settings.wigle_api_token
    wdg = ET.SubElement(root, "wdgwars")
    ET.SubElement(wdg, "api_key").text = settings.wdgwars_api_key
    folders = ET.SubElement(root, "folders")
    ET.SubElement(folders, "raw_logs").text = settings.raw_logs_folder
    ET.SubElement(folders, "combined_logs").text = settings.combined_logs_folder
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _text(root: ET.Element, path: str) -> str:
    node = root.find(path)
    if node is None or node.text is None:
        return ""
    return node.text
