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
- **Save combined CSV** with a suggested name from the earliest and latest FirstSeen (`Wardrive Log Wednesday September 30th 2026.csv`, or a start–end span across calendar days)
- **Unique vs samples** on the legend, file list, and status (unique = distinct MAC+Type; samples = every row)
- **Settings** (General · WiGLE · WDGWars · About) for API keys, raw/combined folders, and open/clear the activity log — stored in local `settings.xml`
- **Activity log** — plain-English `logs/activity.log` beside the app install
- **Planned:** upload combined CSVs to **WiGLE** and **WDGWars** from the app (keys already live in Settings)

Alpha `0.0.2` — run from source until a GitHub Release is published (packaging scripts and Actions are in the repo).

---

## Download

Releases are not published yet (alpha `0.0.2`). When they exist:

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

1. **Drop** a CSV onto the square on the left, or use **Add logs**. Loaded files appear under the square. Toggle a file off to hide it from the map without removing it; toggle it back on to load it again. **×** on the right drops it from the list entirely.
2. The app **merges** the files that are on, keeps every logged row, and stitches them by **FirstSeen**. Points are drawn from those coordinates. Adding another log refits the map around everything loaded so far.
3. **Scroll** to zoom toward the cursor. **Drag** to move the map. **Click** a point to read its fields. **Previous**, **Next**, or the arrow keys move through the visible log. **Fit** frames every point again. Click a type in the legend (**WIFI**, **BLE**, **LTE**, **NR**) to hide or show it — gray means off.
4. **Save combined CSV** when you want a file WiGLE or WDGWars can take. Rename in the dialog if you want.
5. **Settings** holds keys and folders for later upload/batch work, plus open/clear for the activity log.

---

## Tips

- Prefer **WiGLE CSV 1.6** when sharing or uploading — it is the shared format for WiGLE and WDGWars CSV ingest.
- Keep real capture files out of the repo; use a local folder and gitignored paths.
- Counts match the CSV. An on-device app may show a higher “seen” total if it filters personal devices from the export.
- If a file fails to parse, the status line names it. The logs that loaded stay on the map.
- Drag-and-drop needs `tkinterdnd2` (installed by `scripts/setup_env`). **Add logs** works without it.
- Local files next to the app (not on GitHub): `settings.xml`, `logs/activity.log`.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contributing

Want to build from source or send a pull request? See [CONTRIBUTING.md](CONTRIBUTING.md).
