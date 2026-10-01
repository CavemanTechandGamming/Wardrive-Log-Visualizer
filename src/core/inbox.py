"""Batch inbox: pulse Raw → Combined by FirstSeen calendar day.

Pending sources are ``*.csv`` only. Finished sources are renamed to
``*.csv.done`` so the next pulse skips them by extension, not by name.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from src.core.blacklist import apply_blacklist
from src.core.wigle_csv import (
    Observation,
    WigleCsvError,
    WigleLog,
    merge_logs,
    read_wigle_csv,
    wardriving_day_stem,
    write_split_parts,
)


@dataclass(frozen=True)
class InboxResult:
    """Outcome of one inbox pass."""

    pending: int = 0
    processed_sources: tuple[Path, ...] = ()
    written: tuple[Path, ...] = ()
    marked_done: tuple[Path, ...] = ()
    errors: tuple[str, ...] = ()
    skipped_empty: bool = False
    excluded_by_blacklist: int = 0

    @property
    def did_work(self) -> bool:
        return bool(
            self.processed_sources
            or self.written
            or self.errors
            or self.excluded_by_blacklist
        )


def list_pending_csv(raw_dir: str | Path) -> list[Path]:
    """Top-level ``*.csv`` files only (``*.csv.done`` uses suffix ``.done``)."""
    root = Path(raw_dir)
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    )


def mark_csv_done(path: Path) -> Path:
    """Rename ``name.csv`` → ``name.csv.done``. Raises if the target exists."""
    if path.suffix.lower() != ".csv":
        raise WigleCsvError(f"Not a .csv file: {path.name}")
    done = path.with_name(path.name + ".done")
    if done.exists():
        raise WigleCsvError(f"Already exists: {done.name}")
    path.rename(done)
    return done


def group_observations_by_day(
    observations: tuple[Observation, ...],
) -> dict[date, list[Observation]]:
    """Bucket rows by FirstSeen calendar date (midnight boundary)."""
    by_day: dict[date, list[Observation]] = defaultdict(list)
    for row in observations:
        day = datetime.strptime(row.first_seen, "%Y-%m-%d %H:%M:%S").date()
        by_day[day].append(row)
    return dict(by_day)


def existing_day_paths(combined_dir: Path, day: date) -> list[Path]:
    """Combined outputs for one calendar day (plain + Part N)."""
    if not combined_dir.is_dir():
        return []
    prefix = wardriving_day_stem(day)
    found: list[Path] = []
    for path in combined_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".csv":
            continue
        stem = path.name[: -len(".csv")]
        if stem == prefix or stem.startswith(prefix + " Part "):
            found.append(path)
    return sorted(found)


def process_inbox(
    raw_dir: str | Path,
    combined_dir: str | Path,
    max_lines: int,
) -> InboxResult:
    """Read pending Raw CSVs, write Combined day files, mark sources done.

    Silent by design — callers log ``InboxResult`` to the activity log.
    Failed reads are left as ``.csv`` so a later pulse can retry.
    Sources are marked ``.csv.done`` only when at least one Combined file was
    written, or when every pending file was empty of rows.
    """
    raw = Path(raw_dir)
    combined = Path(combined_dir)
    pending = list_pending_csv(raw)
    if not pending:
        return InboxResult(pending=0, skipped_empty=True)
    if not combined.exists():
        combined.mkdir(parents=True, exist_ok=True)
    elif not combined.is_dir():
        return InboxResult(
            pending=len(pending),
            errors=(f"Combined path is not a folder: {combined}",),
        )

    errors: list[str] = []
    loaded: list[tuple[Path, WigleLog]] = []
    for path in pending:
        try:
            loaded.append((path, read_wigle_csv(path)))
        except (OSError, WigleCsvError) as exc:
            errors.append(f"Could not read {path.name}: {exc}")

    if not loaded:
        return InboxResult(pending=len(pending), errors=tuple(errors))

    meta = loaded[0][1].meta
    all_rows: list[Observation] = []
    for _path, log in loaded:
        all_rows.extend(log.observations)

    written: list[Path] = []
    excluded_total = 0
    if all_rows:
        by_day = group_observations_by_day(tuple(all_rows))
        for day in sorted(by_day):
            day_rows = tuple(
                sorted(by_day[day], key=lambda row: row.first_seen)
            )
            day_log = WigleLog(meta=meta, observations=day_rows)
            existing = existing_day_paths(combined, day)
            if existing:
                try:
                    prior = tuple(read_wigle_csv(path) for path in existing)
                    day_log = merge_logs((*prior, day_log))
                except (OSError, WigleCsvError) as exc:
                    errors.append(
                        f"Could not merge existing day {day.isoformat()}: {exc}"
                    )
                    continue
            day_log, excluded = apply_blacklist(day_log)
            excluded_total += excluded
            if not day_log.observations:
                # All rows filtered — leave any existing Combined day files alone.
                continue
            if existing:
                unlink_failed = False
                for path in existing:
                    try:
                        path.unlink()
                    except OSError as exc:
                        errors.append(f"Could not replace {path.name}: {exc}")
                        unlink_failed = True
                if unlink_failed:
                    continue
            try:
                parts = write_split_parts(day_log, combined, max_lines)
            except (OSError, WigleCsvError) as exc:
                errors.append(f"Could not write day {day.isoformat()}: {exc}")
                continue
            written.extend(parts)

    mark_sources = bool(written) or not all_rows or (
        bool(all_rows) and excluded_total > 0 and not written and not errors
    )
    marked_done: list[Path] = []
    if mark_sources:
        for path, _log in loaded:
            try:
                marked_done.append(mark_csv_done(path))
            except (OSError, WigleCsvError) as exc:
                errors.append(f"Could not mark done {path.name}: {exc}")

    return InboxResult(
        pending=len(pending),
        processed_sources=tuple(path for path, _ in loaded),
        written=tuple(written),
        marked_done=tuple(marked_done),
        errors=tuple(errors),
        excluded_by_blacklist=excluded_total,
    )


def summarize_inbox_result(result: InboxResult) -> str:
    """One-line activity / status summary."""
    if result.skipped_empty and not result.errors:
        return "Dropzone pulse — nothing pending."
    parts: list[str] = []
    if result.written:
        names = ", ".join(path.name for path in result.written)
        parts.append(f"wrote {len(result.written)} ({names})")
    if result.excluded_by_blacklist:
        parts.append(f"excluded {result.excluded_by_blacklist} by blacklist")
    if result.marked_done:
        parts.append(f"marked {len(result.marked_done)} done")
    if result.errors:
        parts.append(f"{len(result.errors)} error(s)")
    if not parts:
        return (
            f"Dropzone pulse — {result.pending} pending, no output"
            + (f" ({result.errors[0]})" if result.errors else ".")
        )
    return "Dropzone: " + "; ".join(parts) + "."
