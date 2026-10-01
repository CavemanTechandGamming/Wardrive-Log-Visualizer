# Known issues — Wardrive Log Visualizer

These are **acknowledged limitations** the maintainers intend to improve. They set expectations and help avoid duplicate bug reports. For supported scope, see the [README](README.md).

---

| # | Issue | What's going on |
|---|--------|------------------|
| **1** | **No published release builds yet** | Packaging scripts and Actions workflows exist (`scripts/build_app.*`, **Build** / **Build and Release**). Downloadable GitHub Releases are not published until a release workflow is run. Until then, run from source. |
| **2** | **Plot map only — not Google Maps** | The view is a coordinate plot of logged GPS points. There are no street or satellite tiles. |
| **3** | **Batch inbox and uploads not built yet** | Manual combine, **Split CSV**, and row-cap auto-split on Add/drop ship in `0.0.3`. Day-based **batch inbox** (Raw → Combined) and **upload to WiGLE / WDGWars** are still planned (API keys already live in Settings). |
