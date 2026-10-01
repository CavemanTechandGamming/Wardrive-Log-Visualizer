"""Main window. The map is drawn from logged coordinates, not a basemap."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import APP_NAME, __version__
from src.core.activity_log import log_activity
from src.core.blacklist import apply_blacklist
from src.core.inbox import process_inbox, summarize_inbox_result
from src.core.plot import (
    MapSpace,
    MapView,
    fit_view,
    hits_near,
    pan_view,
    screen_marks,
    zoom_view,
)
from src.core.settings import load_settings
from src.core.wigle_csv import (
    Observation,
    WigleCsvError,
    WigleLog,
    cleaned_input_csv_name,
    count_observations,
    counts_by_type,
    default_combined_csv_name,
    merge_logs,
    needs_row_cap_split,
    read_wigle_csv,
    write_split_parts,
    write_wigle_csv,
)
from src.ui.settings_window import SettingsWindow

MAP_BG = "#141414"
TYPE_COLORS = {
    "WIFI": "#7eb6ff",
    "BLE": "#e6b35a",
    "LTE": "#7dcea0",
    "NR": "#c39bd3",
}
DEFAULT_COLOR = "#b0b0b0"
LEGEND_OFF_COLOR = "#6a6a6a"
HIT_RADIUS = 12
DRAG_THRESHOLD = 4
LEFT_WIDTH = 240
DROP_SIZE = 120


@dataclass
class LoadedLog:
    """One wardrive file kept in the session. Off means out of the map, still listed."""

    path: Path
    name: str
    log: WigleLog
    enabled: bool = True


class MapApp:
    """Add logs, draw every observation, zoom, pan, and inspect a point."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.entries: list[LoadedLog] = []
        self.view: MapView | None = None
        self.fit_scale = 1.0
        self._user_moved = False
        self._space: MapSpace | None = None
        self._observations: tuple[Observation, ...] = ()
        self._marks: list[tuple[float, float, str]] = []
        self._press: tuple[float, float] | None = None
        self._dragging = False
        self._selected: int | None = None
        self._file_rows: list[ctk.CTkFrame] = []
        self._legend_labels: dict[str, ctk.CTkLabel] = {}
        self._type_enabled: dict[str, bool] = {
            name: True for name in TYPE_COLORS
        }
        self.settings = load_settings()
        self._settings_window: SettingsWindow | None = None
        self._tk_icon = None
        self._inbox_after_id: str | None = None
        self._inbox_busy = False

        root.title(f"{APP_NAME} {__version__}")
        root.geometry("1200x700")
        root.minsize(900, 520)
        self._set_window_icon()
        root.after(0, self._set_window_icon)
        self._build_menubar()

        status_bar = ctk.CTkFrame(root, fg_color="transparent")
        status_bar.pack(fill="x", padx=16, pady=(8, 4))
        self.status = ctk.CTkLabel(
            status_bar,
            text="Drop a log on the left square, or use File → Add logs.",
            anchor="w",
        )
        self.status.pack(fill="x")

        legend = ctk.CTkFrame(root, fg_color="transparent")
        legend.pack(fill="x", padx=16, pady=(0, 8))
        for name, color in TYPE_COLORS.items():
            label = ctk.CTkLabel(
                legend,
                text=f"{name} · 0 unique · 0 samples",
                text_color=color,
                cursor="hand2",
            )
            label.pack(side="left", padx=(0, 16))
            label.bind("<Button-1>", lambda _event, t=name: self._toggle_type(t))
            self._legend_labels[name] = label
        self._refresh_counts(None)

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left = ctk.CTkFrame(body, width=LEFT_WIDTH, fg_color="transparent")
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self.drop_zone = ctk.CTkFrame(
            left,
            width=DROP_SIZE,
            height=DROP_SIZE,
            corner_radius=8,
            fg_color=("#e8e8e8", "#1c1c1c"),
            border_width=2,
            border_color=("#9a9a9a", "#3a3a3a"),
        )
        self.drop_zone.pack(anchor="n", pady=(0, 8))
        self.drop_zone.pack_propagate(False)
        self.drop_label = ctk.CTkLabel(
            self.drop_zone,
            text="Drop\nCSV\nhere",
            text_color=("#4a4a4a", "#b0b0b0"),
            justify="center",
        )
        self.drop_label.pack(expand=True, fill="both", padx=6, pady=6)
        self.drop_zone.bind("<Button-1>", lambda _event: self.add_files())
        self.drop_label.bind("<Button-1>", lambda _event: self.add_files())
        self._enable_drop_zone()

        ctk.CTkLabel(left, text="Loaded logs", anchor="w").pack(fill="x", pady=(4, 4))
        self.file_list = ctk.CTkFrame(left, fg_color="transparent")
        self.file_list.pack(fill="both", expand=True)
        self._empty_files_label = ctk.CTkLabel(
            self.file_list,
            text="No files yet.",
            text_color=("#6a6a6a", "#8a8a8a"),
            anchor="w",
        )
        self._empty_files_label.pack(fill="x")

        self.canvas = tk.Canvas(
            body, bg=MAP_BG, highlightthickness=0, borderwidth=0
        )
        self.canvas.pack(side="left", fill="both", expand=True, padx=(12, 0))

        side = ctk.CTkFrame(body, width=300, fg_color="transparent")
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)

        nav = ctk.CTkFrame(side, fg_color="transparent")
        nav.pack(fill="x")
        ctk.CTkButton(
            nav, text="Previous", width=130, command=lambda: self.step_selection(-1)
        ).pack(side="left")
        ctk.CTkButton(
            nav, text="Next", width=130, command=lambda: self.step_selection(1)
        ).pack(side="right")

        self.position = ctk.CTkLabel(side, text="", anchor="w")
        self.position.pack(fill="x", pady=(8, 4))

        self.detail = ctk.CTkTextbox(side, wrap="word")
        self.detail.pack(fill="both", expand=True)
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self._bind_arrows()

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.canvas.bind("<Button-4>", lambda _event: self.zoom_at_pixel(
            self.canvas.winfo_pointerx() - self.canvas.winfo_rootx(),
            self.canvas.winfo_pointery() - self.canvas.winfo_rooty(),
            120,
        ))
        self.canvas.bind("<Button-5>", lambda _event: self.zoom_at_pixel(
            self.canvas.winfo_pointerx() - self.canvas.winfo_rootx(),
            self.canvas.winfo_pointery() - self.canvas.winfo_rooty(),
            -120,
        ))
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self._last_size = (0, 0)
        self._wheel_bound = False
        log_activity(f"Started {APP_NAME} {__version__}.")
        self._schedule_inbox_pulse(initial_delay_ms=2_000)

    def _asset_path(self, *parts: str) -> Path:
        """Resolve an asset under ``assets/`` (dev) or PyInstaller ``_MEIPASS``."""

        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS).joinpath(*parts)  # type: ignore[attr-defined]
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root.joinpath("assets", *parts)

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon (best-effort)."""

        ico_path = self._asset_path("WardriveLogVisualizer.ico")
        png_path = self._asset_path("wardrive-log-visualizer-icon-256.png")
        if not png_path.exists():
            png_path = self._asset_path("wardrive-log-visualizer-icon.png")

        if sys.platform == "win32" and ico_path.exists():
            try:
                self.root.iconbitmap(default=str(ico_path.resolve()))
            except Exception:
                try:
                    self.root.iconbitmap(str(ico_path.resolve()))
                except Exception:
                    pass

        if not png_path.exists():
            return
        try:
            from PIL import Image, ImageTk
        except Exception:
            return
        try:
            img = Image.open(png_path).convert("RGBA")
            if img.size != (256, 256):
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, tk_img)
            self._tk_icon = tk_img
        except Exception:
            return

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add logs…", command=self.add_files)
        file_menu.add_command(label="Clear log", command=self.clear_log)
        file_menu.add_separator()
        file_menu.add_command(label="Combine…", command=self.combine_logs)
        file_menu.add_command(label="Clean…", command=self.clean_logs)
        file_menu.add_command(
            label="Clean and Combine…", command=self.clean_and_combine
        )
        file_menu.add_command(label="Split CSV…", command=self.split_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Settings…", command=self.open_settings)
        if sys.platform != "darwin":
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        auto_menu = tk.Menu(menubar, tearoff=0)
        auto_menu.add_command(
            label="Process Dropzone", command=self.process_inbox_now
        )
        auto_menu.add_command(
            label="Open Dropzone…", command=self.open_dropzone_folder
        )
        auto_menu.add_command(
            label="Open Cleared…", command=self.open_cleared_folder
        )
        menubar.add_cascade(label="Automation", menu=auto_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Fit map", command=self.fit)
        view_menu.add_command(label="Center", command=self.center_selection)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.configure(menu=menubar)

    def open_settings(self) -> None:
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return
        window = SettingsWindow(self.root)

        def _closed(_event: object = None) -> None:
            self.settings = load_settings()
            self._settings_window = None
            self._schedule_inbox_pulse(initial_delay_ms=500)

        window.bind("<Destroy>", _closed)
        self._settings_window = window

    def _schedule_inbox_pulse(self, *, initial_delay_ms: int | None = None) -> None:
        if self._inbox_after_id is not None:
            try:
                self.root.after_cancel(self._inbox_after_id)
            except Exception:
                pass
            self._inbox_after_id = None
        delay = (
            initial_delay_ms
            if initial_delay_ms is not None
            else max(1, self.settings.inbox_pulse_seconds) * 1_000
        )
        self._inbox_after_id = self.root.after(delay, self._inbox_pulse_tick)

    def _inbox_pulse_tick(self) -> None:
        self._inbox_after_id = None
        self._run_inbox(silent=True)
        self._schedule_inbox_pulse()

    def process_inbox_now(self) -> None:
        self._run_inbox(silent=False)

    def _run_inbox(self, *, silent: bool) -> None:
        if self._inbox_busy:
            return
        raw = self.settings.raw_logs_folder.strip()
        combined = self.settings.combined_logs_folder.strip()
        if not raw or not combined:
            if not silent:
                self.status.configure(
                    text="Set Dropzone and Cleared folders in Settings before automation."
                )
                log_activity("Process Dropzone — folders not set.")
            return
        raw_path = Path(raw)
        if not raw_path.is_dir():
            if not silent:
                message = f"Dropzone folder missing: {raw}"
                self.status.configure(text=message)
                log_activity(message)
            return
        self._inbox_busy = True
        try:
            result = process_inbox(
                raw_path,
                combined,
                self.settings.max_lines_per_part,
            )
        finally:
            self._inbox_busy = False
        if silent and result.skipped_empty and not result.errors:
            return
        summary = summarize_inbox_result(result)
        for error in result.errors:
            log_activity(error)
        log_activity(summary)
        if result.written or result.errors or not silent:
            self.status.configure(text=summary)

    def open_dropzone_folder(self) -> None:
        self._open_settings_folder(
            self.settings.raw_logs_folder.strip(),
            label="Dropzone",
        )

    def open_cleared_folder(self) -> None:
        self._open_settings_folder(
            self.settings.combined_logs_folder.strip(),
            label="Cleared",
        )

    def _open_settings_folder(self, folder: str, *, label: str) -> None:
        if not folder:
            message = f"Set the {label} folder in Settings first."
            self.status.configure(text=message)
            log_activity(message)
            return
        path = Path(folder)
        if not path.is_dir():
            message = f"{label} folder missing: {folder}"
            self.status.configure(text=message)
            log_activity(message)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
            log_activity(f"Opened {label} folder.")
        except OSError as exc:
            message = f"Could not open {label} folder: {exc}"
            self.status.configure(text=message)
            log_activity(message)

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            parent=self.root,
            title="Add wardrive logs",
            filetypes=[("WiGLE CSV", "*.csv"), ("All files", "*.*")],
        )
        if not selected:
            return
        self.ingest_paths(selected)

    def ingest_paths(self, paths: list[str] | tuple[str, ...]) -> None:
        csv_paths = [
            path
            for path in paths
            if Path(path).is_file() and Path(path).suffix.lower() == ".csv"
        ]
        skipped = len(paths) - len(csv_paths)
        if not csv_paths:
            self.status.configure(text="Drop one or more .csv wardrive logs.")
            return
        error = ""
        loaded = 0
        for path in csv_paths:
            try:
                log = read_wigle_csv(path)
            except (OSError, WigleCsvError) as exc:
                error = f"Could not read {Path(path).name}: {exc}"
                log_activity(error)
                break
            file_path = Path(path)
            self.entries.append(
                LoadedLog(
                    path=file_path,
                    name=file_path.name,
                    log=log,
                    enabled=True,
                )
            )
            counts = count_observations(log.observations)
            log_activity(f"Loaded {file_path.name} ({counts.label()}).")
            loaded += 1
        if skipped:
            log_activity(f"Skipped {skipped} non-CSV drop(s).")
        self._rebuild_file_list()
        self._selected = None
        self.position.configure(text="")
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self.fit()
        if error:
            self.status.configure(text=error)
        elif skipped:
            self.status.configure(
                text=f"Loaded {loaded} CSV file(s). Skipped {skipped} non-CSV drop(s)."
            )

    def split_csv(self) -> None:
        """Manually split the active combined log (or a chosen file) by line cap."""
        log = self.combined()
        source_label = "combined session"
        if log is None:
            selected = filedialog.askopenfilename(
                parent=self.root,
                title="Split wardrive log",
                filetypes=[("WiGLE CSV", "*.csv"), ("All files", "*.*")],
            )
            if not selected:
                log_activity("Split CSV — cancelled (no file).")
                return
            try:
                log = read_wigle_csv(selected)
            except (OSError, WigleCsvError) as exc:
                message = f"Could not read {Path(selected).name}: {exc}"
                self.status.configure(text=message)
                log_activity(message)
                return
            source_label = Path(selected).name
        if not log.observations:
            self.status.configure(text="Nothing to split — the log has no rows.")
            return
        max_lines = self.settings.max_lines_per_part
        initial_dir = self.settings.combined_logs_folder.strip() or None
        out_dir = filedialog.askdirectory(
            parent=self.root,
            title="Folder for split parts",
            mustexist=True,
            initialdir=initial_dir,
        )
        if not out_dir:
            log_activity("Split CSV — cancelled (no folder).")
            return
        try:
            paths = write_split_parts(log, out_dir, max_lines)
        except (OSError, WigleCsvError) as exc:
            message = f"Could not split: {exc}"
            self.status.configure(text=message)
            log_activity(message)
            return
        names = ", ".join(path.name for path in paths)
        message = (
            f"Wrote {len(paths)} part(s) from {source_label} "
            f"(max {max_lines:,} lines): {names}"
        )
        self.status.configure(text=message)
        log_activity(message)
        from_disk = source_label != "combined session"
        if from_disk and messagebox.askyesno(
            "Split CSV",
            f"Wrote {len(paths)} file(s).\n\nLoad them into this session?",
            parent=self.root,
        ):
            self.ingest_paths([str(path) for path in paths])

    def _rebuild_file_list(self) -> None:
        for row in self._file_rows:
            row.destroy()
        self._file_rows.clear()
        if not self.entries:
            self._empty_files_label.pack(fill="x")
            return
        self._empty_files_label.pack_forget()
        for index, entry in enumerate(self.entries):
            row = ctk.CTkFrame(self.file_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            remove = ctk.CTkButton(
                row,
                text="×",
                width=28,
                height=28,
                fg_color="transparent",
                hover_color=("#d0d0d0", "#3a3a3a"),
                text_color=("#666666", "#aaaaaa"),
                command=lambda i=index: self._remove_entry(i),
            )
            remove.pack(side="right", padx=(4, 0))
            switch = ctk.CTkSwitch(
                row,
                text="",
                width=36,
                command=lambda i=index: self._toggle_entry(i),
            )
            if entry.enabled:
                switch.select()
            else:
                switch.deselect()
            switch.pack(side="left", padx=(0, 6))
            label = ctk.CTkLabel(
                row,
                text=f"{entry.name}\n{count_observations(entry.log.observations).label()}",
                anchor="w",
                justify="left",
                wraplength=LEFT_WIDTH - 88,
            )
            label.pack(side="left", fill="x", expand=True)
            self._file_rows.append(row)

    def _refresh_counts(self, log: WigleLog | None) -> None:
        by_type = counts_by_type(log.observations) if log is not None else {}
        for name, label in self._legend_labels.items():
            summary = by_type.get(name)
            if summary is None:
                text = f"{name} · 0 unique · 0 samples"
            else:
                text = f"{name} · {summary.label()}"
            on = self._type_enabled.get(name, True)
            color = TYPE_COLORS[name] if on else LEGEND_OFF_COLOR
            label.configure(text=text, text_color=color)

    def _toggle_type(self, obs_type: str) -> None:
        if obs_type not in self._type_enabled:
            return
        self._type_enabled[obs_type] = not self._type_enabled[obs_type]
        state = "on" if self._type_enabled[obs_type] else "off"
        log_activity(f"Turned {state} {obs_type} on the plot.")
        self._selected = None
        self.position.configure(text="")
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self.redraw()

    def _toggle_entry(self, index: int) -> None:
        if index < 0 or index >= len(self.entries):
            return
        entry = self.entries[index]
        entry.enabled = not entry.enabled
        state = "on" if entry.enabled else "off"
        log_activity(f"Turned {state} {entry.name}.")
        self._selected = None
        self.position.configure(text="")
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self.fit()

    def _remove_entry(self, index: int) -> None:
        if index < 0 or index >= len(self.entries):
            return
        name = self.entries[index].name
        del self.entries[index]
        log_activity(f"Removed {name}.")
        self._rebuild_file_list()
        self._selected = None
        self.position.configure(text="")
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self.fit()

    def _enable_drop_zone(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            self.drop_label.configure(text="Install\ntkinterdnd2\nfor drop")
            return
        for widget in (self.drop_zone, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
            widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)

    def _on_drag_enter(self, _event: object) -> None:
        self.drop_zone.configure(border_color=("#4a8fd4", "#7eb6ff"))
        self.drop_label.configure(text="Release")

    def _on_drag_leave(self, _event: object) -> None:
        self.drop_zone.configure(border_color=("#9a9a9a", "#3a3a3a"))
        self.drop_label.configure(text="Drop\nCSV\nhere")

    def _on_drop(self, event: object) -> None:
        self._on_drag_leave(event)
        data = getattr(event, "data", "")
        paths = list(self.root.tk.splitlist(data))
        self.ingest_paths(paths)

    def clear_log(self) -> None:
        """Unload every file from the session."""
        if not self.entries:
            self.status.configure(text="Nothing loaded to clear.")
            return
        count = len(self.entries)
        self.entries.clear()
        self._rebuild_file_list()
        self._selected = None
        self.position.configure(text="")
        self._set_detail(
            "Click a point. Previous, Next, or the arrow keys move through the log."
        )
        self.fit()
        message = f"Cleared {count} loaded log(s)."
        self.status.configure(text=message)
        log_activity(message)

    def combine_logs(self) -> None:
        """Merge enabled logs as-is and save (no blacklist)."""
        log = self.combined()
        if log is None:
            self.status.configure(text="Turn on at least one log before Combine.")
            log_activity("Combine — nothing to save (no logs on).")
            return
        self._export_log(
            log,
            action="Combine",
            cleaned=False,
            excluded=0,
            initialfile=default_combined_csv_name(log),
        )

    def clean_logs(self) -> None:
        """Blacklist each enabled file; write only when rows were removed.

        One file with hits → Save As ``{basename} CLEAN.csv``.
        Multiple files with hits → ask for a folder; one cleaned CSV per hit.
        Files with zero blacklist hits are skipped (no rewrite, no CLEAN name).
        Does not merge (that is Clean and Combine).
        """
        enabled = [entry for entry in self.entries if entry.enabled]
        if not enabled:
            self.status.configure(text="Turn on at least one log before Clean.")
            log_activity("Clean — nothing to save (no logs on).")
            return

        if len(enabled) == 1:
            entry = enabled[0]
            cleaned, excluded = apply_blacklist(entry.log)
            if excluded == 0:
                message = (
                    f"Clean — nothing to remove in {entry.name}; skipped."
                )
                self.status.configure(text=message)
                log_activity(message)
                return
            log_activity(
                f"Clean — excluded {excluded} row(s) from {entry.name}."
            )
            if not cleaned.observations:
                self.status.configure(
                    text=f"Clean — nothing left in {entry.name} after blacklist."
                )
                log_activity(
                    f"Clean — nothing left in {entry.name} after blacklist."
                )
                return
            initial_dir = self.settings.combined_logs_folder.strip() or None
            path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Clean",
                defaultextension=".csv",
                filetypes=[("WiGLE CSV", "*.csv")],
                initialfile=cleaned_input_csv_name(entry.name),
                initialdir=initial_dir,
            )
            if not path:
                log_activity("Clean — cancelled.")
                return
            write_wigle_csv(path, cleaned)
            counts = count_observations(cleaned.observations)
            message = (
                f"Clean saved {counts.label()} to {Path(path).name}"
                f" (excluded {excluded})"
            )
            self.status.configure(text=message)
            log_activity(message)
            return

        to_write: list[tuple[LoadedLog, WigleLog, int]] = []
        skipped: list[str] = []
        empty_after: list[str] = []
        for entry in enabled:
            cleaned, excluded = apply_blacklist(entry.log)
            if excluded == 0:
                skipped.append(entry.name)
                continue
            log_activity(
                f"Clean — excluded {excluded} row(s) from {entry.name}."
            )
            if not cleaned.observations:
                empty_after.append(entry.name)
                continue
            to_write.append((entry, cleaned, excluded))

        for name in skipped:
            log_activity(f"Clean — nothing to remove in {name}; skipped.")
        for name in empty_after:
            log_activity(f"Clean — nothing left in {name} after blacklist.")

        if not to_write:
            if empty_after:
                message = (
                    f"Clean — nothing left after blacklist"
                    f" ({empty_after[0]})."
                )
            else:
                message = "Clean — nothing to remove; no files written."
            self.status.configure(text=message)
            log_activity(message)
            return

        initial_dir = self.settings.combined_logs_folder.strip() or None
        out_dir = filedialog.askdirectory(
            parent=self.root,
            title="Folder for cleaned files",
            mustexist=True,
            initialdir=initial_dir,
        )
        if not out_dir:
            log_activity("Clean — cancelled (no folder).")
            return
        out_path = Path(out_dir)
        written: list[str] = []
        total_excluded = 0
        errors: list[str] = []
        for entry, cleaned, excluded in to_write:
            total_excluded += excluded
            dest = out_path / cleaned_input_csv_name(entry.name)
            try:
                write_wigle_csv(dest, cleaned)
            except OSError as exc:
                errors.append(f"{entry.name}: {exc}")
                continue
            written.append(dest.name)
        for err in errors:
            log_activity(f"Clean — {err}")
        if not written:
            message = "Clean — no files written."
            if errors:
                message = f"Clean — no files written ({errors[0]})."
            self.status.configure(text=message)
            log_activity(message)
            return
        message = (
            f"Clean saved {len(written)} file(s) to {out_path.name}"
            f" (excluded {total_excluded} total)"
            f": {', '.join(written)}"
        )
        if skipped:
            message += f"; skipped {len(skipped)} with no matches"
        self.status.configure(text=message)
        log_activity(message)

    def clean_and_combine(self) -> None:
        """Merge enabled logs, then blacklist; CLEAN in name only if rows removed."""
        log = self.combined()
        if log is None:
            self.status.configure(
                text="Turn on at least one log before Clean and Combine."
            )
            log_activity("Clean and Combine — nothing to save (no logs on).")
            return
        log, excluded = apply_blacklist(log)
        did_clean = excluded > 0
        if did_clean:
            log_activity(
                f"Clean and Combine — excluded {excluded} row(s) by blacklist."
            )
        else:
            log_activity(
                "Clean and Combine — nothing to remove; saving without CLEAN."
            )
        if not log.observations:
            self.status.configure(
                text="Clean and Combine — nothing left after blacklist."
            )
            log_activity("Clean and Combine — nothing left after blacklist.")
            return
        self._export_log(
            log,
            action="Clean and Combine",
            cleaned=did_clean,
            excluded=excluded,
            initialfile=default_combined_csv_name(log, cleaned=did_clean),
        )

    def _export_log(
        self,
        log: WigleLog,
        *,
        action: str,
        cleaned: bool,
        excluded: int,
        initialfile: str,
    ) -> None:
        max_lines = self.settings.max_lines_per_part
        initial_dir = self.settings.combined_logs_folder.strip() or None
        if needs_row_cap_split(log, max_lines):
            out_dir = filedialog.askdirectory(
                parent=self.root,
                title=f"Folder for {action} split parts",
                mustexist=True,
                initialdir=initial_dir,
            )
            if not out_dir:
                log_activity(f"{action} — cancelled (no folder).")
                return
            try:
                paths = write_split_parts(
                    log, out_dir, max_lines, cleaned=cleaned
                )
            except (OSError, WigleCsvError) as exc:
                message = f"Could not save {action} split: {exc}"
                self.status.configure(text=message)
                log_activity(message)
                return
            counts = count_observations(log.observations)
            names = ", ".join(path.name for path in paths)
            message = (
                f"{action} saved {counts.label()} as {len(paths)} part(s)"
                + (f" (excluded {excluded})" if excluded else "")
                + f": {names}"
            )
            self.status.configure(text=message)
            log_activity(message)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=action,
            defaultextension=".csv",
            filetypes=[("WiGLE CSV", "*.csv")],
            initialfile=initialfile,
            initialdir=initial_dir,
        )
        if not path:
            log_activity(f"{action} — cancelled.")
            return
        write_wigle_csv(path, log)
        counts = count_observations(log.observations)
        message = (
            f"{action} saved {counts.label()} to {Path(path).name}"
            + (f" (excluded {excluded})" if excluded else "")
        )
        self.status.configure(text=message)
        log_activity(message)

    def fit(self) -> None:
        self._user_moved = False
        self.view = None
        self.redraw()

    def center_selection(self) -> None:
        """Pan so the selected / current point sits in the middle of the map."""
        if self._selected is None or not self._observations:
            self.status.configure(text="Select a point first, then View → Center.")
            return
        if self.view is None or self._space is None:
            return
        if self._selected < 0 or self._selected >= len(self._space.xs):
            return
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 2 or height < 2:
            return
        x = self.view.origin_x + self._space.xs[self._selected] * self.view.scale
        y = self.view.origin_y - self._space.ys[self._selected] * self.view.scale
        dx = (width / 2) - x
        dy = (height / 2) - y
        if dx or dy:
            self.view = pan_view(self.view, dx, dy)
            self._user_moved = True
            self.redraw()
        log_activity("Centered map on the selected point.")

    def active_logs(self) -> list[WigleLog]:
        return [entry.log for entry in self.entries if entry.enabled]

    def combined(self) -> WigleLog | None:
        logs = self.active_logs()
        if not logs:
            return None
        return merge_logs(logs)

    def visible_observations(
        self, log: WigleLog
    ) -> tuple[Observation, ...]:
        """Rows drawn and walked on the plot (legend type filters)."""
        return tuple(
            row
            for row in log.observations
            if self._type_enabled.get(row.obs_type, True)
        )

    def zoom_at_pixel(self, x: float, y: float, delta: int) -> None:
        if self.view is None or delta == 0 or not self._observations:
            return
        factor = 1.1 ** (delta / 120)
        self.view = zoom_view(self.view, x, y, factor, self.fit_scale)
        self._user_moved = True
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = int(self.canvas.winfo_width())
        height = int(self.canvas.winfo_height())
        log = self.combined()
        active = sum(1 for entry in self.entries if entry.enabled)
        if log is None:
            self._space = None
            self._observations = ()
            self._marks = []
            self._refresh_counts(None)
            self._empty_message(width, height)
            if self.entries and active == 0:
                self.status.configure(
                    text="All loaded logs are off. Toggle one on to show it."
                )
            else:
                self.status.configure(
                    text="Drop a log on the left square, or use Add logs."
                )
            return
        if width < 2 or height < 2:
            return

        self._refresh_counts(log)
        visible = self.visible_observations(log)
        if not visible:
            self._space = None
            self._observations = ()
            self._marks = []
            if width >= 2 and height >= 2:
                self.canvas.create_text(
                    width / 2,
                    height / 2,
                    text="All types are off. Click WIFI, BLE, LTE, or NR in the legend.",
                    fill="#8a8a8a",
                    font=("Segoe UI", 14),
                )
            self.status.configure(
                text="All types are off. Click WIFI, BLE, LTE, or NR to show them."
            )
            return

        space = MapSpace.from_observations(visible)
        fitted = fit_view(space, width, height)
        self.fit_scale = fitted.scale
        if self.view is None or not self._user_moved:
            self.view = fitted
        self._space = space
        self._observations = visible
        self._marks = screen_marks(space, self.view)
        for index, (x, y, obs_type) in enumerate(self._marks):
            color = TYPE_COLORS.get(obs_type, DEFAULT_COLOR)
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
            if index == self._selected:
                self.canvas.create_oval(
                    x - 6, y - 6, x + 6, y + 6, outline="#f2f2f2", width=1
                )
        counts = count_observations(visible)
        files_word = "file" if active == 1 else "files"
        self.status.configure(
            text=(
                f"{active} on · {len(self.entries)} loaded · {counts.label()}"
                f" · {files_word} · scroll to zoom · drag to move"
            )
        )

    def _empty_message(self, width: int, height: int) -> None:
        if width < 2 or height < 2:
            return
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Add a log. The map is built from the coordinates you have logged.",
            fill="#8a8a8a",
            font=("Segoe UI", 14),
        )

    def _on_resize(self, event: tk.Event) -> None:
        size = (event.width, event.height)
        if size == self._last_size:
            return
        self._last_size = size
        self.redraw()

    def _bind_wheel(self, _event: tk.Event) -> None:
        if not self._wheel_bound:
            self.canvas.bind_all("<MouseWheel>", self._on_wheel)
            self._wheel_bound = True

    def _unbind_wheel(self, _event: tk.Event) -> None:
        if self._wheel_bound:
            self.canvas.unbind_all("<MouseWheel>")
            self._wheel_bound = False

    def _on_wheel(self, event: tk.Event) -> None:
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        self.zoom_at_pixel(x, y, int(event.delta))

    def _on_press(self, event: tk.Event) -> None:
        self._press = (event.x, event.y)
        self._dragging = False

    def _on_drag(self, event: tk.Event) -> None:
        if self._press is None or self.view is None:
            return
        dx = event.x - self._press[0]
        dy = event.y - self._press[1]
        if not self._dragging and (dx * dx + dy * dy) < DRAG_THRESHOLD ** 2:
            return
        self._dragging = True
        self.canvas.configure(cursor="fleur")
        self.view = pan_view(self.view, dx, dy)
        self._user_moved = True
        self._press = (event.x, event.y)
        self.redraw()

    def _on_release(self, event: tk.Event) -> None:
        self.canvas.configure(cursor="")
        if self._dragging:
            self._press = None
            self._dragging = False
            return
        self._press = None
        self._select_at(event.x, event.y)

    def step_selection(self, delta: int) -> None:
        count = len(self._observations)
        if count == 0 or delta == 0:
            return
        if self._selected is None:
            self._selected = 0 if delta > 0 else count - 1
        else:
            self._selected = min(max(self._selected + delta, 0), count - 1)
        self._bring_into_view(self._selected)
        self._show_selected()
        self.redraw()

    def _select_at(self, x: float, y: float) -> None:
        hits = hits_near(self._marks, x, y, HIT_RADIUS)
        if not hits:
            self._selected = None
            self.position.configure(text="")
            self._set_detail(
                "Click a point. Previous, Next, or the arrow keys move through the log."
            )
            self.redraw()
            return
        self._selected = hits[0]
        self._show_selected()
        self.redraw()

    def _show_selected(self) -> None:
        if self._selected is None or not self._observations:
            return
        count = len(self._observations)
        self.position.configure(text=f"{self._selected + 1} of {count}")
        self._set_detail(_describe(self._observations[self._selected]))

    def _bring_into_view(self, index: int) -> None:
        if self.view is None or self._space is None:
            return
        if index < 0 or index >= len(self._space.xs):
            return
        x = self.view.origin_x + self._space.xs[index] * self.view.scale
        y = self.view.origin_y - self._space.ys[index] * self.view.scale
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        margin = 36
        dx = 0.0
        dy = 0.0
        if x < margin:
            dx = margin - x
        elif x > width - margin:
            dx = (width - margin) - x
        if y < margin:
            dy = margin - y
        elif y > height - margin:
            dy = (height - margin) - y
        if dx or dy:
            self.view = pan_view(self.view, dx, dy)
            self._user_moved = True

    def _bind_arrows(self) -> None:
        for key in ("<Left>", "<Right>", "<Up>", "<Down>"):
            self.root.bind_all(key, self._on_arrow)
        inner = getattr(self.detail, "_textbox", None)
        if inner is not None:
            for key in ("<Left>", "<Right>", "<Up>", "<Down>"):
                inner.bind(key, self._on_arrow)

    def _on_arrow(self, event: tk.Event) -> str:
        if event.keysym in ("Left", "Up"):
            self.step_selection(-1)
        elif event.keysym in ("Right", "Down"):
            self.step_selection(1)
        return "break"

    def _set_detail(self, text: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")


def _describe(obs: Observation) -> str:
    ssid = obs.ssid if obs.ssid != "" else "(no SSID)"
    auth = obs.auth_mode if obs.auth_mode != "" else "(none)"
    rcois = obs.rcois if obs.rcois != "" else "(none)"
    mfgr = obs.mfgr_id if obs.mfgr_id != "" else "(none)"
    return "\n".join(
        (
            f"Type: {obs.obs_type}",
            f"SSID: {ssid}",
            f"MAC: {obs.mac}",
            f"Auth: {auth}",
            f"First seen: {obs.first_seen}",
            f"Channel: {obs.channel}",
            f"Frequency: {obs.frequency}",
            f"RSSI: {obs.rssi}",
            f"Latitude: {obs.latitude}",
            f"Longitude: {obs.longitude}",
            f"Altitude m: {obs.altitude_meters}",
            f"Accuracy m: {obs.accuracy_meters}",
            f"RCOIs: {rcois}",
            f"MfgrId: {mfgr}",
        )
    )


def run() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    try:
        from tkinterdnd2 import TkinterDnD

        TkinterDnD.require(root)
    except ImportError:
        pass
    MapApp(root)
    root.mainloop()
