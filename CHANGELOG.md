# Changelog

All notable changes to Wardrive Log Visualizer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [0.0.4] - 2026-10-01

### Added

- **Batch inbox** (Raw → Combined): a silent pulse checks the Raw folder for new `.csv` files, combines them by **FirstSeen** calendar day, applies the row-cap split when needed, and renames finished sources to `.csv.done` (ignore by extension only — not by filename). Later drops on the **same day** merge into the existing Combined day file(s) and rewrite one clean set.
- Settings → General: **inbox pulse interval** as `HH:MM:SS` (default `00:01:00`; minimum `00:00:10`; maximum `01:00:00`).
- **Process inbox** toolbar button for an immediate pass (same logic as the pulse).

## [0.0.3] - 2026-10-01

### Added

- Hard **row-cap split** (option B): each part file stays within a total line budget of meta + column header + data (default **100,000** lines → **99,998** data rows). Shared by manual **Split CSV**, **Save combined**, and auto-split on Add/drop.
- Settings → General: **max lines per split part** — typed field + slider; persisted in `settings.xml`.

### Changed

- Save As / split part names use `Wardriving Log {Month} {DayOrdinal} {Year}.csv` (no weekday); multi-day span drops weekdays too. Optional `Part N` suffix for split parts.

## [0.0.2] - 2026-09-30

### Added

- Human-readable activity log at `logs/activity.log` beside the app install (start, load, toggle, remove, save, read errors).
- Click WIFI / BLE / LTE / NR in the legend to hide or show that type on the plot (gray when off). Save combined still keeps every row.
- Settings window (tabs: **General** · **WiGLE** · **WDGWars** · **About**): keys, raw/combined folders, open/clear activity log, app info. Saved as local `settings.xml` (gitignored).
- **×** on each loaded-file row removes that log from the list (toggle still only hides it).
- App icon under `assets/` (window, portable exe, and Setup).
- Local build scripts and GitHub Actions workflows for multi-platform **Build** and **Build and Release**.

## [0.0.1] - 2026-09-30

### Added

- First public alpha of **Wardrive Log Visualizer** (MIT).
- Read and write WiGLE CSV 1.6, including Biscuit exports with WIFI, BLE, LTE, and NR rows.
- Merge multiple logs into one CSV, keeping every logged row and ordering by FirstSeen.
- Coordinate **plot** map (not Google Maps / street tiles): scroll zoom, drag pan, click for fields, Previous / Next and arrow keys.
- Left drop square for CSV files; loaded-file list with on/off toggles.
- Save combined CSV with a suggested name from earliest/latest FirstSeen (`Wardrive Log …`), editable before save.
- Unique vs samples counts on the legend, file list, and status line.
