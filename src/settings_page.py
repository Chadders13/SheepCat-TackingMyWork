"""
Settings Page for SheepCat Work Tracker.

Provides a UI for configuring application settings.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import os

from settings_manager import SettingsManager, DEFAULT_SETTINGS, DATE_FORMAT_MAP, PROVIDER_DEFAULT_URLS
import theme


# AI providers available in the dropdown
AI_PROVIDERS = list(PROVIDER_DEFAULT_URLS.keys())


# Display labels and their corresponding format tokens
DATE_FORMAT_OPTIONS = [
    ("No date in filename", ""),
    ("{yyyyMMdd}  e.g. 20240219", "{yyyyMMdd}"),
    ("{ddmmyyyy}  e.g. 19022024", "{ddmmyyyy}"),
    ("{ddmmyy}    e.g. 190224", "{ddmmyy}"),
    ("{MMddyyyy}  e.g. 02192024", "{MMddyyyy}"),
    ("{yyyyddMM}  e.g. 20241902", "{yyyyddMM}"),
    ("{yyyy-MM-dd} e.g. 2024-02-19", "{yyyy-MM-dd}"),
    ("{dd-MM-yyyy} e.g. 19-02-2024", "{dd-MM-yyyy}"),
]


class SettingsPage(tk.Frame):
    """Settings configuration page."""

    def __init__(self, parent, settings_manager: SettingsManager, on_settings_changed=None):
        """
        Initialize the Settings page.

        Args:
            parent: Parent tkinter widget
            settings_manager: SettingsManager instance
            on_settings_changed: Optional callback invoked after settings are saved
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.settings_manager = settings_manager
        self.on_settings_changed = on_settings_changed
        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        """Build all UI widgets."""
        tk.Label(
            self, text="Settings",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=15)

        # Scrollable content area
        outer = tk.Frame(self, bg=theme.WINDOW_BG)
        outer.pack(fill='both', expand=True)

        canvas = tk.Canvas(outer, bg=theme.WINDOW_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        form = tk.Frame(canvas, bg=theme.WINDOW_BG)

        form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ---- AI Provider Settings ----
        tk.Label(
            form, text="AI Provider Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=0, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="AI Provider:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(
            form, textvariable=self.provider_var, values=AI_PROVIDERS, width=27, state='readonly')
        self.provider_combo.grid(row=1, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.provider_combo.bind('<<ComboboxSelected>>', self._on_provider_changed)

        tk.Label(
            form, text="API URL:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=2, column=0, sticky='w', padx=15, pady=5)
        self.api_url_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.api_url_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=2, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Model:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=3, column=0, sticky='w', padx=15, pady=5)
        self.model_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.model_var, width=30,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=3, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Request Timeout (seconds):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=4, column=0, sticky='w', padx=15, pady=5)
        self.llm_timeout_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.llm_timeout_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=4, column=1, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Max Chunk Size (chars):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=5, column=0, sticky='w', padx=15, pady=5)
        self.max_chunk_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.max_chunk_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=5, column=1, sticky='w', padx=5, pady=5)

        # ---- Timer Settings ----
        tk.Label(
            form, text="Timer Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=6, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="Check-in Interval (minutes):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=7, column=0, sticky='w', padx=15, pady=5)
        self.interval_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.interval_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=7, column=1, sticky='w', padx=5, pady=5)

        # ---- Log File Settings ----
        tk.Label(
            form, text="Log File Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=8, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="Log File Directory:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=9, column=0, sticky='w', padx=15, pady=5)
        self.log_dir_var = tk.StringVar()
        dir_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        dir_frame.grid(row=9, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Entry(
            dir_frame, textvariable=self.log_dir_var, width=40,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        tk.Button(
            dir_frame, text="Browse...", command=self._browse_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)

        tk.Label(
            form, text="Log File Name (no extension):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=10, column=0, sticky='w', padx=15, pady=5)
        self.log_name_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.log_name_var, width=30,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=10, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Date Format in Filename:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=11, column=0, sticky='w', padx=15, pady=5)
        self.date_format_var = tk.StringVar()
        self.date_format_combo = ttk.Combobox(
            form, textvariable=self.date_format_var, width=38, state='readonly')
        self.date_format_combo['values'] = [opt[0] for opt in DATE_FORMAT_OPTIONS]
        self.date_format_combo.grid(row=11, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Filename Preview:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=12, column=0, sticky='w', padx=15, pady=5)
        self.preview_var = tk.StringVar()
        tk.Label(
            form, textvariable=self.preview_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=12, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        # Bind changes to update preview
        self.log_dir_var.trace_add('write', self._update_preview)
        self.log_name_var.trace_add('write', self._update_preview)
        self.date_format_combo.bind('<<ComboboxSelected>>', lambda e: self._update_preview())

        # ---- Buttons ----
        button_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        button_frame.pack(pady=15)

        tk.Button(
            button_frame, text="Save Settings", command=self._save_settings,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=15, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)
        tk.Button(
            button_frame, text="Reset to Defaults", command=self._reset_defaults,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=15, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)

        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=5)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_provider_changed(self, _event=None):
        """Auto-fill the default API URL when the provider selection changes."""
        provider = self.provider_var.get()
        if provider in PROVIDER_DEFAULT_URLS:
            self.api_url_var.set(PROVIDER_DEFAULT_URLS[provider])

    def _browse_directory(self):
        """Open a directory chooser and populate the directory field."""
        directory = filedialog.askdirectory(title="Select Log File Directory")
        if directory:
            self.log_dir_var.set(directory)

    def _get_date_format_value(self):
        """Return the format token corresponding to the currently selected display label."""
        display = self.date_format_var.get()
        for label, value in DATE_FORMAT_OPTIONS:
            if label == display:
                return value
        return ""

    def _update_preview(self, *_args):
        """Rebuild the filename preview whenever relevant fields change."""
        directory = self.log_dir_var.get() or "."
        name = self.log_name_var.get() or "work_log"
        date_format_value = self._get_date_format_value()

        if date_format_value and date_format_value in DATE_FORMAT_MAP:
            py_fmt = DATE_FORMAT_MAP[date_format_value]
            date_str = datetime.datetime.now().strftime(py_fmt)
            filename = f"{name}_{date_str}.csv"
        else:
            filename = f"{name}.csv"

        self.preview_var.set(os.path.join(directory, filename))

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load_settings(self):
        """Populate UI fields from the settings manager."""
        sm = self.settings_manager
        self.provider_var.set(sm.get("ai_provider"))
        self.api_url_var.set(sm.get("ai_api_url"))
        self.model_var.set(sm.get("ai_model"))
        self.llm_timeout_var.set(str(sm.get("llm_request_timeout")))
        self.max_chunk_var.set(str(sm.get("max_chunk_size")))
        self.interval_var.set(str(sm.get("checkin_interval_minutes")))
        self.log_dir_var.set(sm.get("log_file_directory"))
        self.log_name_var.set(sm.get("log_file_name"))

        # Select the matching date format label in the combobox
        date_fmt_value = sm.get("log_file_date_format")
        display_label = DATE_FORMAT_OPTIONS[0][0]  # default: "No date in filename"
        for label, value in DATE_FORMAT_OPTIONS:
            if value == date_fmt_value:
                display_label = label
                break
        self.date_format_var.set(display_label)

        self._update_preview()

    def _save_settings(self):
        """Validate UI input and persist settings."""
        try:
            timeout = int(self.llm_timeout_var.get())
            chunk_size = int(self.max_chunk_var.get())
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("Invalid Settings",
                                 "Timeout, chunk size and interval must be valid whole numbers.")
            return

        if timeout <= 0 or chunk_size <= 0 or interval <= 0:
            messagebox.showerror("Invalid Settings",
                                 "Timeout, chunk size and interval must be positive numbers.")
            return

        sm = self.settings_manager
        sm.set("ai_provider", self.provider_var.get())
        sm.set("ai_api_url", self.api_url_var.get().strip())
        sm.set("ai_model", self.model_var.get().strip())
        sm.set("llm_request_timeout", timeout)
        sm.set("max_chunk_size", chunk_size)
        sm.set("checkin_interval_minutes", interval)
        sm.set("log_file_directory", self.log_dir_var.get().strip())
        sm.set("log_file_name", self.log_name_var.get().strip())
        sm.set("log_file_date_format", self._get_date_format_value())

        if sm.save():
            self.status_label.config(text="Settings saved successfully!", fg=theme.GREEN)
            if self.on_settings_changed:
                self.on_settings_changed()
        else:
            self.status_label.config(text="Error saving settings.", fg=theme.RED)

    def _reset_defaults(self):
        """Reset all settings to their default values after confirmation."""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            for key, value in DEFAULT_SETTINGS.items():
                self.settings_manager.set(key, value)
            self._load_settings()
            self.status_label.config(text="Settings reset to defaults.", fg=theme.PRIMARY)

    def refresh(self):
        """Reload settings from the manager (called when navigating to this page)."""
        self._load_settings()
