"""Settings window — keys, batch folders, and activity log helpers."""

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
from src.core.settings import AppSettings, load_settings, save_settings, settings_path


class SettingsWindow(ctk.CTkToplevel):
    """Edit local settings.xml. Never writes secret values into the activity log."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("640x480")
        self.minsize(560, 420)
        self.transient(master)
        self.grab_set()

        self._settings = load_settings()

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        # Order: General first, About last.
        tab_general = tabs.add("General")
        tab_wigle = tabs.add("WiGLE")
        tab_wdg = tabs.add("WDGWars")
        tab_about = tabs.add("About")

        self._build_general_tab(tab_general)
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
        ctk.CTkLabel(tab, text="Raw logs folder", anchor="w").pack(
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

        ctk.CTkLabel(tab, text="Combined logs folder", anchor="w").pack(fill="x")
        out_row = ctk.CTkFrame(tab, fg_color="transparent")
        out_row.pack(fill="x", pady=(0, 12))
        self.combined_folder = ctk.CTkEntry(out_row)
        self.combined_folder.pack(side="left", fill="x", expand=True)
        self.combined_folder.insert(0, self._settings.combined_logs_folder)
        ctk.CTkButton(
            out_row, text="Browse", width=80, command=self._browse_combined
        ).pack(side="left", padx=(8, 0))

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

    def _browse_raw(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self, title="Raw logs folder", mustexist=True
        )
        if chosen:
            self.raw_folder.delete(0, "end")
            self.raw_folder.insert(0, chosen)

    def _browse_combined(self) -> None:
        chosen = filedialog.askdirectory(
            parent=self, title="Combined logs folder", mustexist=True
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
        settings = AppSettings(
            wigle_api_name=self.wigle_name.get().strip(),
            wigle_api_token=self.wigle_token.get().strip(),
            wdgwars_api_key=self.wdgwars_key.get().strip(),
            raw_logs_folder=self.raw_folder.get().strip(),
            combined_logs_folder=self.combined_folder.get().strip(),
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
        # Never put key/token values into the activity log.
        log_activity("Saved settings.xml.")
        self.destroy()
