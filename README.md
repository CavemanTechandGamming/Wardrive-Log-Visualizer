# Wardrive Log Visualizer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-lightgrey.svg)](https://github.com/CavemanTechandGamming/Wardrive-Log-Visualizer/releases)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/CavemanTechandGamming/Wardrive-Log-Visualizer/releases)

Desktop tool to **ingest wardrive logs**, **merge them into one combined log**, and **plot the sightings as points**. It is a **coordinate plot** of what you logged — not a Google Maps–style street or satellite map.

*(Main-window screenshot will go here once captured — `docs/images/main-window.png`.)*

---

## Features

- **Ingest** WiGLE CSV 1.6 exports (including **Biscuit**), with WIFI, BLE, LTE, and NR rows
- **Merge** multiple runs into one log — every logged row stays; combined order is by **FirstSeen**
- **Plot map** from logged GPS coordinates only (no Google Maps, no street tiles, no satellite basemap)
- **Zoom** (scroll), **pan** (drag), **click** a point for its fields; **Previous** / **Next** or arrow keys walk the log
- **Drop** CSVs on the left square (or use **Add logs**); per-file on/off toggles; **×** removes a file from the list
- **Legend filters** — click WIFI / BLE / LTE / NR to hide or show that type (gray when off); Save still keeps every row
- **Save / export** — File → **Combine** (merge + save), **Clean** (blacklist; writes `{name} CLEAN.csv` only when rows were removed), **Clean and Combine** (merge then blacklist; ` CLEAN` in the name only when rows were removed). Row-cap → `Part N` (with ` CLEAN` last when cleaned).
- **Row-cap split** — File → **Split CSV**; Dropzone automation may auto-split oversized day files. Map Add/drop does **not** auto-split.
- **Unique vs samples** on the legend, file list, and status (unique = distinct MAC+Type; samples = every row)
- **Settings** (General · **Blacklist** · WiGLE · WDGWars · About) — Dropzone/Cleared folders, pulse, SSID/MAC blacklist (`blacklist.xml`), keys, activity log
- **Automation** — pulse Dropzone → Cleared by FirstSeen day; blacklist strip; `.csv.done`; same-day merge; Process Dropzone / open folders from the menu
- **Activity log** — plain-English `logs/activity.log` beside the app install
- **Planned:** upload to **WiGLE** / **WDGWars** (keys already live in Settings)

Alpha `0.0.5` — run from source until a GitHub Release is published (packaging scripts and Actions are in the repo).

---

## Download

Releases are not published yet (alpha `0.0.5`). When they exist:

1. Open this repository’s **[Releases](https://github.com/CavemanTechandGamming/Wardrive-Log-Visualizer/releases)** page.
2. Download the file for your OS:
   - **Windows portable** — `…-windows-portable.zip` (extract and run the `.exe`)
   - **Windows installer** — `…-windows-setup.exe` (run the Setup wizard)
   - **Mac** — `…-mac-apple-silicon.tar.gz` or `…-mac-intel.tar.gz`
   - **Linux** — `…-<distro>.tar.gz` (e.g. `…-ubuntu.tar.gz`)
3. Extract if needed, then run **Wardrive Log Visualizer**.

Until then, run from source (see [CONTRIBUTING.md](CONTRIBUTING.md)).

---

## How to use

1. **Drop** a CSV onto the square on the left, or use **File → Add logs**. Loaded files appear under the square. Toggle a file off to hide it from the map without removing it; toggle it back on to load it again. **×** on the right drops it from the list entirely. **File → Clear log** unloads everything.
2. The app **merges** the files that are on, keeps every logged row, and stitches them by **FirstSeen**. Points are drawn from those coordinates. Adding another log refits the map around everything loaded so far.
3. **Scroll** to zoom toward the cursor. **Drag** to move the map. **Click** a point to read its fields. **Previous**, **Next**, or the arrow keys move through the visible log. **View → Fit map** frames every point again; **View → Center** pans to the selection. Click a type in the legend (**WIFI**, **BLE**, **LTE**, **NR**) to hide or show it — gray means off.
4. **File → Combine** merges and saves. **Clean** blacklists each enabled file and writes `{name} CLEAN.csv` only when something was removed (no hits → skip that file; multiple hits → pick a folder). **Clean and Combine** merges first, then blacklists — always saves the merge; appends ` CLEAN` only when rows were removed. Over the line cap on combine paths → `Part N` files.
5. **File → Split CSV** splits by the Settings line cap — map import never auto-splits.
6. **Settings** holds Dropzone/Cleared folders, pulse interval, **Blacklist**, keys, and activity log helpers. **Automation → Process Dropzone** runs one inbox pass immediately.

---

## Tips

- Prefer **WiGLE CSV 1.6** when sharing or uploading — it is the shared format for WiGLE and WDGWars CSV ingest.
- Keep real capture files out of the repo; use a local folder and gitignored paths.
- Counts match the CSV. An on-device app may show a higher “seen” total if it filters personal devices from the export.
- If a file fails to parse, the status line names it. The logs that loaded stay on the map.
- Drag-and-drop needs `tkinterdnd2` (installed by `scripts/setup_env`). **Add logs** works without it.
- Local files next to the app (not on GitHub): `settings.xml`, `blacklist.xml`, `logs/activity.log`.
- Inbox / Dropzone only picks up top-level `*.csv` files. After a successful pass, sources become `*.csv.done`. Cleared outputs use `Wardriving Log {Month} {DayOrdinal} {Year}.csv` (and `Part N` if split) — no `CLEAN` word on automation titles. Blacklist still strips matching rows into Cleared. File → Clean / Clean and Combine append ` CLEAN` only when the blacklist actually removed rows.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

Want to build from source or send a pull request? See [CONTRIBUTING.md](CONTRIBUTING.md).
