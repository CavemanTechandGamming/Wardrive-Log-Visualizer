# Known issues — Wardrive Log Visualizer

These are **acknowledged limitations** the maintainers intend to improve. They set expectations and help avoid duplicate bug reports. For supported scope, see the [README](README.md).

---

| # | Issue | What's going on |
|---|--------|------------------|
| **1** | **No packaged releases yet** | Run from source (`scripts/run_app.bat` or `python -m src`) until portable / installer builds exist. |
| **2** | **Plot map only — not Google Maps** | The view is a coordinate plot of logged GPS points. There are no street or satellite tiles. |
| **3** | **Batch inbox and uploads not built yet** | Day-split auto-combine and WiGLE / WDGWars upload are planned. **Settings** already stores keys and folders in local `settings.xml` (tabs: General, WiGLE, WDGWars, About). |
