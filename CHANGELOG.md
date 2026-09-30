# Changelog

All notable changes to Wardrive Log Visualizer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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
