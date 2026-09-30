# App icons

| File | Role |
|------|------|
| `wardrive-log-visualizer-icon.png` | Master square PNG (512×512) |
| `wardrive-log-visualizer-icon-256.png` | 256×256 for the window and packaging |
| `WardriveLogVisualizer.ico` | Windows `.ico` (title bar, portable exe, Setup) |
| `wardrive-log-visualizer-icon-source.png` | Same art as the master PNG |

Rebuild the `.ico` from the master PNG:

```bat
python scripts\generate_windows_ico.py --input assets\wardrive-log-visualizer-icon.png --output assets\WardriveLogVisualizer.ico
```
