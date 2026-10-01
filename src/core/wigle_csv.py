"""WiGLE CSV 1.6 read and write.

Biscuit companion exports use this file shape (locked 2026-09-30 from real pulls).
WiGLE and WDGWars CSV ingest expect the same ``WigleWifi-1.6`` layout.

Format reference: https://api.wigle.net/csvFormat.html

A file is two preamble lines, then data rows:

1. Meta, kept verbatim: ``WigleWifi-1.6`` plus comma-separated ``key=value`` fields.
   Biscuit adds device fields and ``star``, ``body``, ``subBody``.
2. The 14 column names in ``WIGLE_1_6_COLUMNS``.
3. One observation per row. ``Type`` from Biscuit includes ``WIFI``, ``BLE``,
   ``LTE``, and ``NR``. Other non-empty types are kept. ``MAC`` is a hardware
   address or, for cell rows, an opaque id such as ``310000_00000_1``.
   Empty SSID, AuthMode, RCOIs, and MfgrId are valid. Values are stored as
   text so a write round-trips the columns.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

# Column header line for WiGLE CSV 1.6 (after the WigleWifi-1.6 meta row).
WIGLE_1_6_COLUMNS: tuple[str, ...] = (
    "MAC",
    "SSID",
    "AuthMode",
    "FirstSeen",
    "Channel",
    "Frequency",
    "RSSI",
    "CurrentLatitude",
    "CurrentLongitude",
    "AltitudeMeters",
    "AccuracyMeters",
    "RCOIs",
    "MfgrId",
    "Type",
)

WIGLE_1_6_META_PREFIX = "WigleWifi-1.6"

# Hard line-cap split (locked B): every part file counts meta + column header + data.
PREAMBLE_LINES = 2
DEFAULT_MAX_LINES_PER_PART = 100_000
MIN_MAX_LINES_PER_PART = 3  # meta + header + at least one data row

_FIRST_SEEN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
_INT_INDEXES = (4, 5, 6)
_FLOAT_INDEXES = (7, 8, 9, 10)


class WigleCsvError(ValueError):
    """A file is not a usable WiGLE CSV 1.6 log."""


@dataclass(frozen=True)
class Observation:
    """One data row. Fields stay strings so writing does not reshape numbers."""

    mac: str
    ssid: str
    auth_mode: str
    first_seen: str
    channel: str
    frequency: str
    rssi: str
    latitude: str
    longitude: str
    altitude_meters: str
    accuracy_meters: str
    rcois: str
    mfgr_id: str
    obs_type: str

    def as_row(self) -> tuple[str, ...]:
        return (
            self.mac,
            self.ssid,
            self.auth_mode,
            self.first_seen,
            self.channel,
            self.frequency,
            self.rssi,
            self.latitude,
            self.longitude,
            self.altitude_meters,
            self.accuracy_meters,
            self.rcois,
            self.mfgr_id,
            self.obs_type,
        )


@dataclass(frozen=True)
class WigleLog:
    """A parsed log. ``meta`` is the first line, without a trailing newline."""

    meta: str
    observations: tuple[Observation, ...]

    def meta_fields(self) -> dict[str, str]:
        """``key=value`` pairs after the ``WigleWifi-1.6`` token."""
        fields: dict[str, str] = {}
        parts = self.meta.split(",")
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            fields[key] = value
        return fields


def read_wigle_csv(path: str | Path) -> WigleLog:
    """Read a WiGLE CSV 1.6 file from disk."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return parse_wigle_csv(text)


def parse_wigle_csv(text: str) -> WigleLog:
    """Parse WiGLE CSV 1.6 text into a log."""
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.strip():
        raise WigleCsvError("File is empty.")

    lines_needed = text.split("\n", 2)
    if len(lines_needed) < 2:
        raise WigleCsvError("File needs a meta line and a column line.")

    meta = lines_needed[0].rstrip("\r")
    header_line = lines_needed[1].rstrip("\r")
    rest = lines_needed[2] if len(lines_needed) == 3 else ""

    if not meta.startswith(WIGLE_1_6_META_PREFIX):
        raise WigleCsvError(
            f"First line must start with {WIGLE_1_6_META_PREFIX}."
        )
    if meta.split(",", 1)[0] != WIGLE_1_6_META_PREFIX:
        raise WigleCsvError(
            f"First field must be {WIGLE_1_6_META_PREFIX}."
        )

    header = _single_row(header_line, line_number=2)
    if tuple(header) != WIGLE_1_6_COLUMNS:
        raise WigleCsvError(
            "Column line must be the WiGLE CSV 1.6 header: "
            + ",".join(WIGLE_1_6_COLUMNS)
        )

    observations: list[Observation] = []
    reader = csv.reader(io.StringIO(rest))
    for offset, row in enumerate(reader):
        line_number = offset + 3
        if row == [] or (len(row) == 1 and row[0] == ""):
            continue
        observations.append(_observation(row, line_number))

    return WigleLog(meta=meta, observations=tuple(observations))


def format_wigle_csv(log: WigleLog) -> str:
    """Serialize a log to WiGLE CSV 1.6 text, using LF line endings."""
    if not log.meta.startswith(WIGLE_1_6_META_PREFIX):
        raise WigleCsvError(
            f"Meta line must start with {WIGLE_1_6_META_PREFIX}."
        )
    buffer = io.StringIO()
    buffer.write(log.meta)
    buffer.write("\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(WIGLE_1_6_COLUMNS)
    for observation in log.observations:
        writer.writerow(observation.as_row())
    return buffer.getvalue()


def write_wigle_csv(path: str | Path, log: WigleLog) -> None:
    """Write a log to disk as WiGLE CSV 1.6."""
    Path(path).write_text(format_wigle_csv(log), encoding="utf-8", newline="\n")


def merge_logs(logs: Sequence[WigleLog]) -> WigleLog:
    """Combine logs and order every row by ``FirstSeen``.

    Each logged sighting stays. The same MAC at a later time is a new row.
    Rows with the same timestamp keep the order they were added. The combined
    file uses the first log's meta line so there is still one ``WigleWifi-1.6``
    header.
    """
    if not logs:
        raise WigleCsvError("Nothing to merge.")
    observations: list[Observation] = []
    for log in logs:
        observations.extend(log.observations)
    observations.sort(key=lambda row: row.first_seen)
    return WigleLog(meta=logs[0].meta, observations=tuple(observations))


def merge_wigle_files(paths: Sequence[str | Path]) -> WigleLog:
    """Read each WiGLE CSV 1.6 path and merge the rows by timestamp."""
    if not paths:
        raise WigleCsvError("Nothing to merge.")
    return merge_logs(tuple(read_wigle_csv(path) for path in paths))


def max_data_rows_for_line_cap(max_lines: int) -> int:
    """How many observation rows fit under a total-line hard cap (option B)."""
    if max_lines < MIN_MAX_LINES_PER_PART:
        raise WigleCsvError(
            f"Max lines per part must be at least {MIN_MAX_LINES_PER_PART} "
            "(meta + column header + one data row)."
        )
    return max_lines - PREAMBLE_LINES


def needs_row_cap_split(log: WigleLog, max_lines: int) -> bool:
    """True when the log would exceed ``max_lines`` including preamble."""
    return len(log.observations) > max_data_rows_for_line_cap(max_lines)


def split_log(log: WigleLog, max_lines: int) -> tuple[WigleLog, ...]:
    """Split a log into parts that each stay within the hard line cap.

    Every part keeps the same meta line and a full column header (written by
    ``format_wigle_csv``). Rows are never cut mid-observation. If the log
    already fits, returns a one-element tuple with the same log.
    """
    if not log.observations:
        raise WigleCsvError("Nothing to split — the log has no rows.")
    max_data = max_data_rows_for_line_cap(max_lines)
    if len(log.observations) <= max_data:
        return (log,)
    parts: list[WigleLog] = []
    observations = log.observations
    for start in range(0, len(observations), max_data):
        chunk = observations[start : start + max_data]
        parts.append(WigleLog(meta=log.meta, observations=chunk))
    return tuple(parts)


def write_split_parts(
    log: WigleLog,
    directory: str | Path,
    max_lines: int,
    *,
    cleaned: bool = False,
) -> tuple[Path, ...]:
    """Write row-cap parts into ``directory`` using locked Wardriving Log names.

    Multi-part outputs always get `` Part N``. A single fitting part is written
    without a part suffix. When ``cleaned`` is true, `` CLEAN`` is appended
    after any Part token (e.g. ``… Part 1 CLEAN.csv``).
    """
    parts = split_log(log, max_lines)
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    multi = len(parts) > 1
    for index, part_log in enumerate(parts, start=1):
        name = default_combined_csv_name(
            part_log,
            part=index if multi else None,
            cleaned=cleaned,
        )
        path = out_dir / name
        write_wigle_csv(path, part_log)
        written.append(path)
    return tuple(written)


def default_combined_csv_name(
    log: WigleLog,
    *,
    part: int | None = None,
    cleaned: bool = False,
) -> str:
    """Suggest a Save As basename from the earliest and latest FirstSeen.

    One calendar day::

        Wardriving Log September 30th 2026.csv

    Multiple days (interim span until a dedicated span form is locked)::

        Wardriving Log September 30th 2026 - October 1st 2026.csv

    Row-cap split parts (optional ``part``)::

        Wardriving Log September 30th 2026 Part 1.csv

    Cleaned File → Clean / Clean and Combine (optional ``cleaned``)::

        Wardriving Log September 30th 2026 CLEAN.csv
        Wardriving Log September 30th 2026 Part 1 CLEAN.csv

    Uses min and max ``FirstSeen`` among every row in the log (string order
    matches chronological order for ``YYYY-MM-DD HH:MM:SS``).
    """
    if not log.observations:
        raise WigleCsvError("Nothing to name — the log has no rows.")
    times = [row.first_seen for row in log.observations]
    first = datetime.strptime(min(times), "%Y-%m-%d %H:%M:%S")
    last = datetime.strptime(max(times), "%Y-%m-%d %H:%M:%S")
    start = _pretty_capture_day(first)
    if first.date() == last.date():
        base = f"Wardriving Log {start}"
    else:
        base = f"Wardriving Log {start} - {_pretty_capture_day(last)}"
    if part is not None:
        if part < 1:
            raise WigleCsvError("Part number must be 1 or greater.")
        base = f"{base} Part {part}"
    if cleaned:
        base = f"{base} CLEAN"
    return f"{base}.csv"


def cleaned_input_csv_name(source_name: str) -> str:
    """Append `` CLEAN`` before ``.csv`` for File → Clean single-input saves."""
    path = Path(source_name)
    stem = path.stem
    if stem.endswith(" CLEAN"):
        return f"{stem}.csv"
    return f"{stem} CLEAN.csv"


@dataclass(frozen=True)
class CountSummary:
    """Sample rows vs distinct devices (MAC + Type)."""

    samples: int
    unique: int

    def label(self) -> str:
        return f"{self.unique} unique · {self.samples} samples"


def count_observations(observations: Sequence[Observation]) -> CountSummary:
    """Count every row and distinct ``(MAC, Type)`` pairs."""
    unique = {(row.mac, row.obs_type) for row in observations}
    return CountSummary(samples=len(observations), unique=len(unique))


def counts_by_type(
    observations: Sequence[Observation],
) -> dict[str, CountSummary]:
    """Per-Type sample and unique counts. Missing types are omitted."""
    by_type: dict[str, list[Observation]] = {}
    for row in observations:
        by_type.setdefault(row.obs_type, []).append(row)
    return {
        obs_type: count_observations(rows) for obs_type, rows in by_type.items()
    }


def _pretty_capture_day(when: datetime) -> str:
    """Month DayOrdinal Year — no weekday (locked output naming 2026-10-01)."""
    return f"{when.strftime('%B')} {_ordinal_day(when.day)} {when.year}"


def wardriving_day_stem(day: date) -> str:
    """Basename without ``.csv`` for one calendar day's combined output."""
    when = datetime(day.year, day.month, day.day)
    return f"Wardriving Log {_pretty_capture_day(when)}"


def _ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _single_row(line: str, line_number: int) -> list[str]:
    rows = list(csv.reader(io.StringIO(line)))
    if len(rows) != 1:
        raise WigleCsvError(f"Line {line_number} is not a single CSV row.")
    return rows[0]


def _observation(row: list[str], line_number: int) -> Observation:
    if len(row) != len(WIGLE_1_6_COLUMNS):
        raise WigleCsvError(
            f"Line {line_number} has {len(row)} columns; "
            f"expected {len(WIGLE_1_6_COLUMNS)}."
        )
    if row[0] == "":
        raise WigleCsvError(f"Line {line_number} is missing MAC.")
    if not _FIRST_SEEN.fullmatch(row[3]):
        raise WigleCsvError(
            f"Line {line_number} FirstSeen must be YYYY-MM-DD HH:MM:SS."
        )
    if row[13] == "":
        raise WigleCsvError(f"Line {line_number} is missing Type.")
    for index in _INT_INDEXES:
        _require_int(row[index], WIGLE_1_6_COLUMNS[index], line_number)
    for index in _FLOAT_INDEXES:
        _require_float(row[index], WIGLE_1_6_COLUMNS[index], line_number)
    return Observation(
        mac=row[0],
        ssid=row[1],
        auth_mode=row[2],
        first_seen=row[3],
        channel=row[4],
        frequency=row[5],
        rssi=row[6],
        latitude=row[7],
        longitude=row[8],
        altitude_meters=row[9],
        accuracy_meters=row[10],
        rcois=row[11],
        mfgr_id=row[12],
        obs_type=row[13],
    )


def _require_int(value: str, name: str, line_number: int) -> None:
    try:
        if value == "" or any(ch in value for ch in ".eE"):
            raise ValueError
        int(value, 10)
    except ValueError:
        raise WigleCsvError(
            f"Line {line_number} {name} must be a whole number."
        ) from None


def _require_float(value: str, name: str, line_number: int) -> None:
    try:
        if value.strip() == "":
            raise ValueError
        float(value)
    except ValueError:
        raise WigleCsvError(
            f"Line {line_number} {name} must be a number."
        ) from None
