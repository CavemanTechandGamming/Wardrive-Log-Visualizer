"""Local SSID / MAC blacklist — kept beside settings.xml, never committed.

Matching is case-sensitive and exact (locked 2026-10-01). A row is dropped
when its SSID is on the list or its MAC matches (separators stripped for MAC
compare only; letter case is preserved).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from src.core.activity_log import install_root
from src.core.wigle_csv import Observation, WigleLog

BLACKLIST_FILE_NAME = "blacklist.xml"


@dataclass
class Blacklist:
    """Local exclude lists. Empty lists mean no filtering."""

    ssids: list[str] = field(default_factory=list)
    macs: list[str] = field(default_factory=list)


def blacklist_path() -> Path:
    return install_root() / BLACKLIST_FILE_NAME


def normalize_mac(mac: str) -> str:
    """Strip common separators; keep letter case (case-sensitive match)."""
    return "".join(ch for ch in mac.strip() if ch not in ":-. ")


def load_blacklist() -> Blacklist:
    path = blacklist_path()
    if not path.is_file():
        return Blacklist()
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError):
        return Blacklist()
    root = tree.getroot()
    ssids: list[str] = []
    for node in root.findall("ssids/ssid"):
        if node.text is not None and node.text != "":
            ssids.append(node.text)
    macs: list[str] = []
    for node in root.findall("macs/mac"):
        if node.text is not None and node.text.strip() != "":
            macs.append(normalize_mac(node.text))
    # Preserve order; drop exact duplicate entries.
    return Blacklist(
        ssids=_unique_keep_order(ssids),
        macs=_unique_keep_order(macs),
    )


def save_blacklist(blacklist: Blacklist) -> None:
    root = ET.Element("blacklist")
    ssids_el = ET.SubElement(root, "ssids")
    for ssid in _unique_keep_order(blacklist.ssids):
        if ssid == "":
            continue
        ET.SubElement(ssids_el, "ssid").text = ssid
    macs_el = ET.SubElement(root, "macs")
    normalized = [normalize_mac(m) for m in blacklist.macs]
    for mac in _unique_keep_order(normalized):
        if mac == "":
            continue
        ET.SubElement(macs_el, "mac").text = mac
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    path = blacklist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def row_is_blacklisted(row: Observation, blacklist: Blacklist) -> bool:
    """True when SSID or MAC hits the list (case-sensitive exact)."""
    if row.ssid in blacklist.ssids:
        return True
    mac_key = normalize_mac(row.mac)
    if mac_key and mac_key in blacklist.macs:
        return True
    return False


def apply_blacklist(
    log: WigleLog,
    blacklist: Blacklist | None = None,
) -> tuple[WigleLog, int]:
    """Return a copy with blacklisted rows removed, plus how many were dropped.

    Empty blacklist → original log and ``0``.
    """
    rules = blacklist if blacklist is not None else load_blacklist()
    if not rules.ssids and not rules.macs:
        return log, 0
    kept: list[Observation] = []
    excluded = 0
    for row in log.observations:
        if row_is_blacklisted(row, rules):
            excluded += 1
        else:
            kept.append(row)
    if excluded == 0:
        return log, 0
    return WigleLog(meta=log.meta, observations=tuple(kept)), excluded


def _unique_keep_order(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
