"""Settings window — keys, batch folders, split cap, and activity log helpers."""

from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import APP_NAME, __version__
from src.core.activity_log import (
    activity_log_path,
    clear_activity_log,
    log_activity,
    open_activity_log,
)
from src.core.blacklist import (
    Blacklist,
    blacklist_path,
    load_blacklist,
    save_blacklist,
)
from src.core.settings import (
    AppSettings,
    DEFAULT_INBOX_PULSE_SECONDS,
    MAX_INBOX_PULSE_SECONDS,
    MIN_INBOX_PULSE_SECONDS,
    clamp_max_lines_per_part,
    format_hhmmss,
    load_settings,
    parse_hhmmss,
    save_settings,
    settings_path,
)
from src.core.wigle_csv import (
    DEFAULT_MAX_LINES_PER_PART,
    MIN_MAX_LINES_PER_PART,
    PREAMBLE_LINES,
)

# Practical slider range; typed field can go outside (clamped on save to >= 3).
_SLIDER_MIN = 1_000
_SLIDER_MAX = 500_000


class SettingsWindow(ctk.CTkToplevel):
    """Edit local settings.xml. Never writes secret values into the activity log."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("640x640")
        self.minsize(560, 560)
        self.transient(master)
        self.grab_set()

        self._settings = load_settings()
        self._blacklist = load_blacklist()
        self._syncing_lines = False

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        # Order: General · Blacklist · WiGLE · WDGWars · About.
        tab_general = tabs.add("General")
        tab_blacklist = tabs.add("Blacklist")
        tab_wigle = tabs.add("WiGLE")
        tab_wdg = tabs.add("WDGWars")
        tab_about = tabs.add("About")

        self._build_general_tab(tab_general)
        self._build_blacklist_tab(tab_blacklist)
        self._build_wigle_tab(tab_wigle)
        self._build_wdgwars_tab(tab_wdg)
        self._build_about_tab(tab_about)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(buttons, text="Cancel", width=100, command=self.destroy).pack(
            side="right"
        )
        ctk.CTkButton(buttons, text="Save", width=100, command=self._save).pack(
            side="right", padx=(0, 8)
        )

        self.after(50, self._focus)

    def _build_wigle_tab(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="API name", anchor="w").pack(fill="x", pady=(8, 0))
        self.wigle_name = ctk.CTkEntry(tab)
        self.wigle_name.pack(fill="x", pady=(0, 8))
        self.wigle_name.insert(0, self._settings.wigle_api_name)

        ctk.CTkLabel(tab, text="API token", anchor="w").pack(fill="x")
        self.wigle_token = ctk.CTkEntry(tab, show="*")
        self.wigle_token.pack(fill="x", pady=(0, 8))
        self.wigle_token.insert(0, self._settings.wigle_api_token)

        ctk.CTkLabel(
            tab,
            text="Used later for uploading combined CSVs to WiGLE.",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(8, 0))

    def _build_wdgwars_tab(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="API key", anchor="w").pack(fill="x", pady=(8, 0))
        self.wdgwars_key = ctk.CTkEntry(tab, show="*")
        self.wdgwars_key.pack(fill="x", pady=(0, 8))
        self.wdgwars_key.insert(0, self._settings.wdgwars_api_key)

        ctk.CTkLabel(
            tab,
            text="Used later for uploading combined CSVs to WDGWars.",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(8, 0))

    def _build_general_tab(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(tab, text="Dropzone folder", anchor="w").pack(
            fill="x", pady=(8, 0)
        )
        raw_row = ctk.CTkFrame(tab, fg_color="transparent")
        raw_row.pack(fill="x", pady=(0, 8))
        self.raw_folder = ctk.CTkEntry(raw_row)
        self.raw_folder.pack(side="left", fill="x", expand=True)
        self.raw_folder.insert(0, self._settings.raw_logs_folder)
        ctk.CTkButton(
            raw_row, text="Browse", width=80, command=self._browse_raw
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(tab, text="Cleared folder", anchor="w").pack(fill="x")
        out_row = ctk.CTkFrame(tab, fg_color="transparent")
        out_row.pack(fill="x", pady=(0, 8))
        self.combined_folder = ctk.CTkEntry(out_row)
        self.combined_folder.pack(side="left", fill="x", expand=True)
        self.combined_folder.insert(0, self._settings.combined_logs_folder)
        ctk.CTkButton(
            out_row, text="Browse", width=80, command=self._browse_combined
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            tab,
            text=(
                "Automation reads pending .csv from Dropzone and writes day files "
                "to Cleared."
            ),
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tab, text="Inbox pulse interval", anchor="w").pack(fill="x")
        ctk.CTkLabel(
            tab,
            text=(
                "How often the app checks Dropzone for new .csv files "
                f"(format HH:MM:SS). Default {format_hhmmss(DEFAULT_INBOX_PULSE_SECONDS)}; "
                f"min {format_hhmmss(MIN_INBOX_PULSE_SECONDS)}; "
                f"max {format_hhmmss(MAX_INBOX_PULSE_SECONDS)}. "
                "Processed sources are renamed to .csv.done."
            ),
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(0, 4))
        pulse_row = ctk.CTkFrame(tab, fg_color="transparent")
        pulse_row.pack(fill="x", pady=(0, 12))
        self.pulse_entry = ctk.CTkEntry(pulse_row, width=100)
        self.pulse_entry.pack(side="left")
        self.pulse_entry.insert(
            0, format_hhmmss(self._settings.inbox_pulse_seconds)
        )
        ctk.CTkLabel(
            pulse_row,
            text="HH:MM:SS",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(tab, text="Max lines per split part", anchor="w").pack(
            fill="x"
        )
        ctk.CTkLabel(
            tab,
            text=(
                f"Hard cap for each part file (meta + column header + data). "
                f"Default {DEFAULT_MAX_LINES_PER_PART:,} → "
                f"{DEFAULT_MAX_LINES_PER_PART - PREAMBLE_LINES:,} data rows. "
                f"Minimum {MIN_MAX_LINES_PER_PART}."
            ),
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(0, 4))
        lines_row = ctk.CTkFrame(tab, fg_color="transparent")
        lines_row.pack(fill="x", pady=(0, 4))
        self.lines_entry = ctk.CTkEntry(lines_row, width=120)
        self.lines_entry.pack(side="left")
        self.lines_entry.insert(0, str(self._settings.max_lines_per_part))
        self.lines_entry.bind("<KeyRelease>", self._on_lines_typed)
        self.lines_entry.bind("<FocusOut>", self._on_lines_typed)
        ctk.CTkLabel(
            lines_row,
            text="lines",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
        ).pack(side="left", padx=(8, 0))
        self.lines_slider = ctk.CTkSlider(
            tab,
            from_=_SLIDER_MIN,
            to=_SLIDER_MAX,
            number_of_steps=(_SLIDER_MAX - _SLIDER_MIN) // 1_000,
            command=self._on_lines_slider,
        )
        self.lines_slider.pack(fill="x", pady=(0, 12))
        self._set_lines_widgets(self._settings.max_lines_per_part)

        ctk.CTkLabel(tab, text="Activity log", anchor="w").pack(fill="x")
        ctk.CTkLabel(
            tab,
            text=str(activity_log_path()),
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(0, 8))
        log_row = ctk.CTkFrame(tab, fg_color="transparent")
        log_row.pack(fill="x")
        ctk.CTkButton(
            log_row, text="Open log file", command=self._open_log
        ).pack(side="left")
        ctk.CTkButton(
            log_row, text="Clear log file", command=self._clear_log
        ).pack(side="left", padx=(8, 0))

    def _build_blacklist_tab(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            tab,
            text=(
                "Rows matching these SSIDs or MACs are removed on Clean, "
                "Clean and Combine, and Dropzone → Cleared writes. Matching is "
                "case-sensitive and exact. Add / drop onto the map is not filtered."
            ),
            anchor="w",
            justify="left",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(8, 8))
        ctk.CTkLabel(
            tab,
            text=f"Saved to:\n{blacklist_path()}",
            anchor="w",
            justify="left",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tab, text="SSIDs (one per line)", anchor="w").pack(fill="x")
        self.ssid_box = ctk.CTkTextbox(tab, height=120)
        self.ssid_box.pack(fill="both", expand=True, pady=(0, 8))
        if self._blacklist.ssids:
            self.ssid_box.insert("1.0", "\n".join(self._blacklist.ssids) + "\n")

        ctk.CTkLabel(tab, text="MACs / BSSIDs (one per line)", anchor="w").pack(
            fill="x"
        )
        self.mac_box = ctk.CTkTextbox(tab, height=120)
        self.mac_box.pack(fill="both", expand=True, pady=(0, 4))
        if self._blacklist.macs:
            self.mac_box.insert("1.0", "\n".join(self._blacklist.macs) + "\n")
        ctk.CTkLabel(
            tab,
            text="Separators (: - .) are ignored when matching MACs; letter case is kept.",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x")

    def _build_about_tab(self, tab: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            tab,
            text=APP_NAME,
            anchor="w",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(fill="x", pady=(12, 4))
        ctk.CTkLabel(tab, text=f"Version {__version__}", anchor="w").pack(fill="x")
        ctk.CTkLabel(
            tab,
            text=(
                "Ingest wardrive logs (WiGLE CSV 1.6 / Biscuit), merge them, "
                "and plot the sightings as points. This is a coordinate plot — "
                "not a Google Maps–style street or satellite map."
            ),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(12, 8))
        ctk.CTkLabel(
            tab,
            text="License: MIT",
            anchor="w",
            text_color=("#6a6a6a", "#8a8a8a"),
        ).pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            tab,
            text=f"Local settings file:\n{settings_path()}",
            anchor="w",
            justify="left",
            text_color=("#6a6a6a", "#8a8a8a"),
            wraplength=560,
        ).pack(fill="x", pady=(12, 0))

    def _focus(self) -> None:
        self.lift()
        self.focus_force()

    def _set_lines_widgets(self, value: int) -> None:
        self._syncing_lines = True
        try:
            clamped = clamp_max_lines_per_part(value)
            self.lines_entry.delete(0, "end")
            self.lines_entry.insert(0, str(clamped))
            slider_value = min(max(clamped, _SLIDER_MIN), _SLIDER_MAX)
            self.lines_slider.set(slider_value)
        finally:
            self._syncing_lines = False

    def _on_lines_slider(self, value: float) -> None:
        if self._syncing_lines:
            return
        self._syncing_lines = True
        try:
            lines = int(round(float(value) / 1_000.0) * 1_000)
            lines = clamp_max_lines_per_part(lines)
            self.lines_entry.delete(0, "end")
            self.lines_entry.insert(0, str(lines))
        finally:
            self._syncing_lines = False

    def _on_lines_typed(self, _event: object = None) -> None:
        if self._syncing_lines:
            return
        text = self.lines_entry.get().strip().replace(",", "")
        if not text:
            return
        try:
            value = int(text, 10)
        except ValueError:
            return
        self._syncing_lines = True
        try:
            slider_value = min(max(value, _SLIDER_MIN), _SLIDER_MAX)
            self.lines_slider.set(slider_value)
        finally:
            self._syncing_lines = False

    def _parsed_max_lines(self) -> int | None:
        text = self.lines_entry.get().strip().replace(",", "")
        try:
            return clamp_max_lines_per_part(int(text, 10))
        except ValueError:
            return None

    def _browse_raw(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self, title="Dropzone folder", mustexist=True
        )
        if chosen:
            self.raw_folder.delete(0, "end")
            self.raw_folder.insert(0, chosen)

    def _browse_combined(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self, title="Cleared folder", mustexist=True
        )
        if chosen:
            self.combined_folder.delete(0, "end")
            self.combined_folder.insert(0, chosen)

    def _open_log(self) -> None:
        if open_activity_log():
            log_activity("Opened the activity log.")
        else:
            messagebox.showerror(
                "Activity log",
                "Could not open the activity log file.",
                parent=self,
            )

    def _clear_log(self) -> None:
        if not messagebox.askyesno(
            "Clear activity log",
            "Erase everything in the activity log?",
            parent=self,
        ):
            return
        if clear_activity_log():
            log_activity("Cleared the activity log.")
            messagebox.showinfo(
                "Activity log",
                "The activity log was cleared.",
                parent=self,
            )
        else:
            messagebox.showerror(
                "Activity log",
                "Could not clear the activity log file.",
                parent=self,
            )

    def _save(self) -> None:
        max_lines = self._parsed_max_lines()
        if max_lines is None:
            messagebox.showerror(
                "Settings",
                "Max lines per split part must be a whole number.",
                parent=self,
            )
            return
        try:
            pulse_seconds = parse_hhmmss(self.pulse_entry.get())
        except ValueError as exc:
            messagebox.showerror("Settings", str(exc), parent=self)
            return
        settings = AppSettings(
            wigle_api_name=self.wigle_name.get().strip(),
            wigle_api_token=self.wigle_token.get().strip(),
            wdgwars_api_key=self.wdgwars_key.get().strip(),
            raw_logs_folder=self.raw_folder.get().strip(),
            combined_logs_folder=self.combined_folder.get().strip(),
            max_lines_per_part=max_lines,
            inbox_pulse_seconds=pulse_seconds,
        )
        try:
            save_settings(settings)
        except OSError as exc:
            messagebox.showerror(
                "Settings",
                f"Could not save settings.xml:\n{exc}",
                parent=self,
            )
            return
        ssids = [
            line
            for line in self.ssid_box.get("1.0", "end").splitlines()
            if line != ""
        ]
        macs = [
            line.strip()
            for line in self.mac_box.get("1.0", "end").splitlines()
            if line.strip() != ""
        ]
        try:
            save_blacklist(Blacklist(ssids=ssids, macs=macs))
        except OSError as exc:
            messagebox.showerror(
                "Settings",
                f"Could not save blacklist.xml:\n{exc}",
                parent=self,
            )
            return
        # Never put key/token or blacklist values into the activity log.
        log_activity(
            f"Saved settings.xml (max lines per part: {max_lines:,}; "
            f"inbox pulse: {format_hhmmss(pulse_seconds)}) and blacklist.xml "
            f"({len(ssids)} SSID(s), {len(macs)} MAC(s))."
        )
        self.destroy()
