"""
Settings Page for SheepCat Work Tracker.

Provides a UI for configuring application settings.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import os

import threading

from settings_manager import SettingsManager, DEFAULT_SETTINGS, DATE_FORMAT_MAP, PROVIDER_DEFAULT_URLS, DEFAULT_NOTES_FOLDER
import theme
from theme import THEME_NAMES
from ollama_client import check_connection, get_running_models, DEFAULT_OLLAMA_BASE_URL
from onboarding import _base_url_from_api_url


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
        model_row = tk.Frame(form, bg=theme.WINDOW_BG)
        model_row.grid(row=3, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.model_combo = ttk.Combobox(
            model_row, textvariable=self.model_var, width=27, state='normal')
        self.model_combo.pack(side='left')
        theme.RoundedButton(
            model_row, text="⟳ Refresh", command=self._refresh_models,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        ).pack(side='left', padx=5)

        self.models_status_var = tk.StringVar(value="")
        self.models_status_label = tk.Label(
            form, textvariable=self.models_status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED, anchor='w',
        )
        self.models_status_label.grid(row=4, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 2))

        tk.Label(
            form, text="Request Timeout (seconds):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=5, column=0, sticky='w', padx=15, pady=5)
        self.llm_timeout_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.llm_timeout_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=5, column=1, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Max Chunk Size (chars):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=6, column=0, sticky='w', padx=15, pady=5)
        self.max_chunk_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.max_chunk_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=6, column=1, sticky='w', padx=5, pady=5)

        # ---- Timer Settings ----
        tk.Label(
            form, text="Timer Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=7, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="Check-in Interval (minutes):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=8, column=0, sticky='w', padx=15, pady=5)
        self.interval_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.interval_var, width=10,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=8, column=1, sticky='w', padx=5, pady=5)

        # ---- Log File Settings ----
        tk.Label(
            form, text="Log File Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=9, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="Log File Directory:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=10, column=0, sticky='w', padx=15, pady=5)
        self.log_dir_var = tk.StringVar()
        dir_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        dir_frame.grid(row=10, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Entry(
            dir_frame, textvariable=self.log_dir_var, width=40,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        theme.RoundedButton(
            dir_frame, text="Browse...", command=self._browse_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        ).pack(side='left', padx=5)

        tk.Label(
            form, text="Log File Name (no extension):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=11, column=0, sticky='w', padx=15, pady=5)
        self.log_name_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.log_name_var, width=30,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=11, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Date Format in Filename:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=12, column=0, sticky='w', padx=15, pady=5)
        self.date_format_var = tk.StringVar()
        self.date_format_combo = ttk.Combobox(
            form, textvariable=self.date_format_var, width=38, state='readonly')
        self.date_format_combo['values'] = [opt[0] for opt in DATE_FORMAT_OPTIONS]
        self.date_format_combo.grid(row=12, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Filename Preview:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=13, column=0, sticky='w', padx=15, pady=5)
        self.preview_var = tk.StringVar()
        tk.Label(
            form, textvariable=self.preview_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=13, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        # Bind changes to update preview
        self.log_dir_var.trace_add('write', self._update_preview)
        self.log_name_var.trace_add('write', self._update_preview)
        self.date_format_combo.bind('<<ComboboxSelected>>', lambda e: self._update_preview())

        # ---- Daily Summary Settings ----
        tk.Label(
            form, text="Daily Summary Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=14, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        self.summary_save_var = tk.BooleanVar()
        tk.Checkbutton(
            form, text="Save daily summary as standalone file",
            variable=self.summary_save_var,
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
            selectcolor=theme.INPUT_BG, activebackground=theme.WINDOW_BG,
            command=self._on_summary_save_toggled,
        ).grid(row=15, column=0, columnspan=3, sticky='w', padx=15, pady=5)

        tk.Label(
            form, text="Summary File Directory:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=16, column=0, sticky='w', padx=15, pady=5)
        self.summary_dir_var = tk.StringVar()
        summary_dir_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        summary_dir_frame.grid(row=16, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.summary_dir_entry = tk.Entry(
            summary_dir_frame, textvariable=self.summary_dir_var, width=40,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        )
        self.summary_dir_entry.pack(side='left')
        self.summary_dir_browse_btn = theme.RoundedButton(
            summary_dir_frame, text="Browse...", command=self._browse_summary_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        )
        self.summary_dir_browse_btn.pack(side='left', padx=5)

        tk.Label(
            form, text="Date Format in Filename:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=17, column=0, sticky='w', padx=15, pady=5)
        self.summary_date_format_var = tk.StringVar()
        self.summary_date_format_combo = ttk.Combobox(
            form, textvariable=self.summary_date_format_var, width=38, state='readonly')
        self.summary_date_format_combo['values'] = [opt[0] for opt in DATE_FORMAT_OPTIONS]
        self.summary_date_format_combo.grid(row=17, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Summary Filename Preview:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=18, column=0, sticky='w', padx=15, pady=5)
        self.summary_preview_var = tk.StringVar()
        tk.Label(
            form, textvariable=self.summary_preview_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=18, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        # Bind changes to update summary preview
        self.summary_dir_var.trace_add('write', self._update_summary_preview)
        self.summary_date_format_combo.bind('<<ComboboxSelected>>', lambda e: self._update_summary_preview())

        # ---- Todo Archiving Settings ----
        tk.Label(
            form, text="Todo Archiving Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=19, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        self.archive_done_var = tk.BooleanVar()
        tk.Checkbutton(
            form, text="Archive done todos automatically",
            variable=self.archive_done_var,
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
            selectcolor=theme.INPUT_BG, activebackground=theme.WINDOW_BG,
            command=self._on_archive_toggled,
        ).grid(row=20, column=0, columnspan=3, sticky='w', padx=15, pady=5)

        tk.Label(
            form, text="Archive trigger:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=21, column=0, sticky='w', padx=15, pady=5)
        self.archive_trigger_var = tk.StringVar()
        self.archive_trigger_combo = ttk.Combobox(
            form, textvariable=self.archive_trigger_var,
            values=["Daily (on day start/end)", "After end-of-day summary"],
            width=30, state='readonly',
        )
        self.archive_trigger_combo.grid(row=21, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Archive File Directory:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=22, column=0, sticky='w', padx=15, pady=5)
        self.archive_dir_var = tk.StringVar()
        archive_dir_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        archive_dir_frame.grid(row=22, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.archive_dir_entry = tk.Entry(
            archive_dir_frame, textvariable=self.archive_dir_var, width=40,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        )
        self.archive_dir_entry.pack(side='left')
        self.archive_dir_browse_btn = theme.RoundedButton(
            archive_dir_frame, text="Browse...", command=self._browse_archive_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        )
        self.archive_dir_browse_btn.pack(side='left', padx=5)

        # ---- Appearance Settings ----
        tk.Label(
            form, text="Appearance",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=23, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form, text="UI Theme:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=24, column=0, sticky='w', padx=15, pady=5)
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(
            form, textvariable=self.theme_var, values=THEME_NAMES, width=20, state='readonly')
        self.theme_combo.grid(row=24, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Classic – original dark slate/indigo\nGlass Purple – soft modern purple palette",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED, justify='left',
        ).grid(row=25, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 5))

        self.theme_note_label = tk.Label(
            form, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.ACCENT, justify='left',
        )
        self.theme_note_label.grid(row=26, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 5))
        self.theme_combo.bind('<<ComboboxSelected>>', self._on_theme_changed)

        # ---- AI Summary Prompt Context ----
        tk.Label(
            form, text="AI Summary Prompt Context",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=27, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 5))

        tk.Label(
            form,
            text="Extra instructions added to the interval (hourly) summary prompt:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=28, column=0, columnspan=3, sticky='w', padx=15, pady=(5, 0))
        self.hourly_context_text = tk.Text(
            form, height=4, width=60, wrap='word',
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            font=theme.FONT_BODY,
        )
        self.hourly_context_text.grid(row=29, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 5))

        tk.Label(
            form,
            text="Extra instructions added to the end-of-day summary prompt:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=30, column=0, columnspan=3, sticky='w', padx=15, pady=(5, 0))
        self.daily_context_text = tk.Text(
            form, height=4, width=60, wrap='word',
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            font=theme.FONT_BODY,
        )
        self.daily_context_text.grid(row=31, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 10))

        # ---- External API Settings ----
        tk.Label(
            form, text="External API Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=32, column=0, columnspan=3, sticky='w', padx=15, pady=(15, 2))

        tk.Label(
            form,
            text=(
                "🔒  API tokens are stored securely in your OS keychain (Windows Credential\n"
                "Manager / macOS Keychain / Linux Secret Service). Non-sensitive settings\n"
                "are saved to the local settings file. No data is sent to external systems\n"
                "without your explicit confirmation."
            ),
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.ACCENT,
            justify='left',
        ).grid(row=33, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 8))

        # -- Jira --
        self.jira_enabled_var = tk.BooleanVar()
        jira_header = tk.Frame(form, bg=theme.WINDOW_BG)
        jira_header.grid(row=34, column=0, columnspan=3, sticky='w', padx=15, pady=(5, 2))
        tk.Label(
            jira_header, text="Jira (API v3)",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        tk.Checkbutton(
            jira_header, text="Enable", variable=self.jira_enabled_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            activebackground=theme.WINDOW_BG, selectcolor=theme.INPUT_BG,
        ).pack(side='left', padx=(12, 0))

        tk.Label(
            form, text="Jira Host URL:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=35, column=0, sticky='w', padx=15, pady=5)
        self.jira_host_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.jira_host_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=35, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Jira Account Email:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=36, column=0, sticky='w', padx=15, pady=5)
        self.jira_email_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.jira_email_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=36, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Jira API Token:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=37, column=0, sticky='w', padx=15, pady=5)
        self.jira_token_var = tk.StringVar()
        jira_token_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        jira_token_frame.grid(row=37, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Entry(
            jira_token_frame, textvariable=self.jira_token_var, width=42, show="*",
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        self._jira_token_status = tk.Label(
            jira_token_frame, text="", font=theme.FONT_SMALL,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self._jira_token_status.pack(side='left', padx=(6, 0))

        # -- Azure DevOps --
        self.ado_enabled_var = tk.BooleanVar()
        ado_header = tk.Frame(form, bg=theme.WINDOW_BG)
        ado_header.grid(row=38, column=0, columnspan=3, sticky='w', padx=15, pady=(10, 2))
        tk.Label(
            ado_header, text="Azure DevOps",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        tk.Checkbutton(
            ado_header, text="Enable", variable=self.ado_enabled_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            activebackground=theme.WINDOW_BG, selectcolor=theme.INPUT_BG,
        ).pack(side='left', padx=(12, 0))

        tk.Label(
            form, text="Organization / Project URL:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=39, column=0, sticky='w', padx=15, pady=5)
        self.ado_org_url_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.ado_org_url_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=39, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Personal Access Token (PAT):",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=40, column=0, sticky='w', padx=15, pady=5)
        self.ado_pat_var = tk.StringVar()
        ado_pat_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        ado_pat_frame.grid(row=40, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Entry(
            ado_pat_frame, textvariable=self.ado_pat_var, width=42, show="*",
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        self._ado_pat_status = tk.Label(
            ado_pat_frame, text="", font=theme.FONT_SMALL,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self._ado_pat_status.pack(side='left', padx=(6, 0))

        # ---- Note-Taking App Settings ----
        tk.Label(
            form, text="Note-Taking App Settings",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).grid(row=41, column=0, columnspan=3, sticky='w', padx=15, pady=(20, 2))

        tk.Label(
            form,
            text=(
                "Export formatted work summaries to Obsidian or Notable.\n"
                "Enable each integration and provide credentials below."
            ),
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.ACCENT,
            justify='left',
        ).grid(row=42, column=0, columnspan=3, sticky='w', padx=15, pady=(0, 8))

        # -- Obsidian --
        self.obsidian_enabled_var = tk.BooleanVar()
        obsidian_header = tk.Frame(form, bg=theme.WINDOW_BG)
        obsidian_header.grid(row=43, column=0, columnspan=3, sticky='w', padx=15, pady=(5, 2))
        tk.Label(
            obsidian_header, text="Obsidian (Local REST API plugin)",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        tk.Checkbutton(
            obsidian_header, text="Enable", variable=self.obsidian_enabled_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            activebackground=theme.WINDOW_BG, selectcolor=theme.INPUT_BG,
        ).pack(side='left', padx=(12, 0))

        tk.Label(
            form,
            text=(
                "Requires the 'Local REST API' community plugin installed and running in Obsidian.\n"
                "Default host: http://localhost:27123"
            ),
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify='left',
        ).grid(row=44, column=0, columnspan=3, sticky='w', padx=30, pady=(0, 4))

        tk.Label(
            form, text="Host URL:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=45, column=0, sticky='w', padx=15, pady=5)
        self.obsidian_host_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.obsidian_host_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=45, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="Notes Folder:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=46, column=0, sticky='w', padx=15, pady=5)
        self.obsidian_folder_var = tk.StringVar()
        tk.Entry(
            form, textvariable=self.obsidian_folder_var, width=50,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).grid(row=46, column=1, columnspan=2, sticky='w', padx=5, pady=5)

        tk.Label(
            form, text="API Key:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=47, column=0, sticky='w', padx=15, pady=5)
        self.obsidian_key_var = tk.StringVar()
        obsidian_key_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        obsidian_key_frame.grid(row=47, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        tk.Entry(
            obsidian_key_frame, textvariable=self.obsidian_key_var, width=42, show="*",
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        self._obsidian_key_status = tk.Label(
            obsidian_key_frame, text="", font=theme.FONT_SMALL,
            bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self._obsidian_key_status.pack(side='left', padx=(6, 0))

        # -- Notable --
        self.notable_enabled_var = tk.BooleanVar()
        notable_header = tk.Frame(form, bg=theme.WINDOW_BG)
        notable_header.grid(row=48, column=0, columnspan=3, sticky='w', padx=15, pady=(10, 2))
        tk.Label(
            notable_header, text="Notable",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        tk.Checkbutton(
            notable_header, text="Enable", variable=self.notable_enabled_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            activebackground=theme.WINDOW_BG, selectcolor=theme.INPUT_BG,
        ).pack(side='left', padx=(12, 0))

        tk.Label(
            form,
            text="Point to the directory where Notable stores its Markdown notes.",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify='left',
        ).grid(row=49, column=0, columnspan=3, sticky='w', padx=30, pady=(0, 4))

        tk.Label(
            form, text="Notes Directory:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).grid(row=50, column=0, sticky='w', padx=15, pady=5)
        self.notable_dir_var = tk.StringVar()
        notable_dir_frame = tk.Frame(form, bg=theme.WINDOW_BG)
        notable_dir_frame.grid(row=50, column=1, columnspan=2, sticky='w', padx=5, pady=(5, 15))
        tk.Entry(
            notable_dir_frame, textvariable=self.notable_dir_var, width=42,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left')
        theme.RoundedButton(
            notable_dir_frame, text="Browse…",
            command=self._browse_notable_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=8, cursor='hand2',
        ).pack(side='left', padx=(6, 0))

        # ---- Buttons ----
        button_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        button_frame.pack(pady=15)

        theme.RoundedButton(
            button_frame, text="Save Settings", command=self._save_settings,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=15, cursor='hand2',
        ).pack(side='left', padx=5)
        theme.RoundedButton(
            button_frame, text="Reset to Defaults", command=self._reset_defaults,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=15, cursor='hand2',
        ).pack(side='left', padx=5)

        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=5)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_base_url(self) -> str:
        """Derive the Ollama base URL from the current API URL field."""
        api_url = self.api_url_var.get().strip()
        if api_url:
            try:
                return _base_url_from_api_url(api_url)
            except Exception:
                pass
        return DEFAULT_OLLAMA_BASE_URL

    def _refresh_models(self):
        """Fetch available and running models from Ollama in a background thread."""
        self.models_status_var.set("🔄 Fetching models…")
        self.model_combo['values'] = []

        def _fetch():
            base_url = self._get_base_url()
            result = check_connection(base_url)
            running = get_running_models(base_url) if result.success else []
            self.after(0, self._apply_models, result.success, result.models, running)

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_models(self, success: bool, models: list, running: list):
        """Update model combobox and status label with fetched data (called on main thread)."""
        if not success:
            self.models_status_var.set("⚠ Could not reach Ollama – check API URL")
            self.models_status_label.config(fg=theme.RED)
            return

        self.model_combo['values'] = models

        # Keep the currently configured model selected (or the first available)
        current = self.model_var.get().strip()
        if current not in models and models:
            self.model_var.set(models[0])

        if running:
            running_str = ", ".join(running)
            self.models_status_var.set(f"✅ {len(models)} model(s) available  |  🟢 Running: {running_str}")
        else:
            self.models_status_var.set(f"✅ {len(models)} model(s) available  |  ⚪ No model currently running")
        self.models_status_label.config(fg=theme.MUTED)

    def refresh(self):
        """Reload settings and refresh the model list from Ollama."""
        self._load_settings()
        self._refresh_models()

    def _on_theme_changed(self, _event=None):
        """Show a note when the user picks a different theme."""
        self.theme_note_label.config(
            text="⚠ Restart the application to apply the new theme."
        )

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

    def _browse_summary_directory(self):
        """Open a directory chooser and populate the summary directory field."""
        directory = filedialog.askdirectory(title="Select Summary File Directory")
        if directory:
            self.summary_dir_var.set(directory)

    def _browse_archive_directory(self):
        """Open a directory chooser and populate the archive directory field."""
        directory = filedialog.askdirectory(title="Select Archive File Directory")
        if directory:
            self.archive_dir_var.set(directory)

    def _browse_notable_directory(self):
        """Open a directory chooser and populate the Notable notes directory field."""
        directory = filedialog.askdirectory(title="Select Notable Notes Directory")
        if directory:
            self.notable_dir_var.set(directory)

    def _on_archive_toggled(self):
        """Enable or disable the archive trigger and directory widgets."""
        enabled = self.archive_done_var.get()
        state_entry = tk.NORMAL if enabled else tk.DISABLED
        state_combo = 'readonly' if enabled else tk.DISABLED
        self.archive_dir_entry.config(state=state_entry)
        self.archive_dir_browse_btn.config(state=state_entry)
        self.archive_trigger_combo.config(state=state_combo)

    def _on_summary_save_toggled(self):
        """Enable or disable the summary directory widgets based on the checkbox."""
        enabled = self.summary_save_var.get()
        state = 'normal' if enabled else 'disabled'
        self.summary_dir_entry.config(state=state)
        self.summary_dir_browse_btn.config(state=state)
        self.summary_date_format_combo.config(state='readonly' if enabled else 'disabled')

    def _get_date_format_value(self):
        """Return the format token corresponding to the currently selected display label."""
        display = self.date_format_var.get()
        for label, value in DATE_FORMAT_OPTIONS:
            if label == display:
                return value
        return ""

    def _get_summary_date_format_value(self):
        """Return the format token for the currently selected summary date format label."""
        display = self.summary_date_format_var.get()
        for label, value in DATE_FORMAT_OPTIONS:
            if label == display:
                return value
        return "{yyyy-MM-dd}"

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

    def _update_summary_preview(self, *_args):
        """Rebuild the summary filename preview whenever relevant fields change."""
        directory = self.summary_dir_var.get() or "."
        date_format_value = self._get_summary_date_format_value()

        if date_format_value and date_format_value in DATE_FORMAT_MAP:
            py_fmt = DATE_FORMAT_MAP[date_format_value]
            date_str = datetime.datetime.now().strftime(py_fmt)
        else:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        filename = f"daily_summary_{date_str}.md"
        self.summary_preview_var.set(os.path.join(directory, filename))

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

        # Daily summary settings
        self.summary_save_var.set(bool(sm.get("summary_save_to_file")))
        self.summary_dir_var.set(sm.get("summary_file_directory"))

        summary_date_fmt_value = sm.get("summary_file_date_format")
        summary_display_label = DATE_FORMAT_OPTIONS[0][0]
        for label, value in DATE_FORMAT_OPTIONS:
            if value == summary_date_fmt_value:
                summary_display_label = label
                break
        self.summary_date_format_var.set(summary_display_label)

        # Apply enabled/disabled state based on checkbox
        self._on_summary_save_toggled()

        # Archive settings
        self.archive_done_var.set(bool(sm.get("archive_done_todos")))
        trigger_value = sm.get("archive_trigger", "daily")
        trigger_label = "Daily (on day start/end)" if trigger_value == "daily" else "After end-of-day summary"
        self.archive_trigger_var.set(trigger_label)
        self.archive_dir_var.set(sm.get("archive_file_directory", "."))
        self._on_archive_toggled()

        # Appearance
        self.theme_var.set(sm.get("ui_theme", "Classic"))
        self.theme_note_label.config(text="")

        # AI Summary Prompt Context
        self.hourly_context_text.delete("1.0", tk.END)
        self.hourly_context_text.insert("1.0", sm.get("hourly_summary_extra_context", ""))
        self.daily_context_text.delete("1.0", tk.END)
        self.daily_context_text.insert("1.0", sm.get("daily_summary_extra_context", ""))

        # External API settings
        self.jira_enabled_var.set(bool(sm.get("jira_enabled", True)))
        self.jira_host_var.set(sm.get("jira_host", ""))
        self.jira_email_var.set(sm.get("jira_email", ""))
        # Token fields: show placeholder when a token is already stored in keychain
        jira_token = sm.get_credential("jira_api_token")
        self.jira_token_var.set("")
        self._jira_token_status.config(
            text="🔑 Token stored" if jira_token else "",
            fg=theme.GREEN if jira_token else theme.MUTED,
        )
        self.ado_enabled_var.set(bool(sm.get("azure_devops_enabled", True)))
        self.ado_org_url_var.set(sm.get("azure_devops_org_url", ""))
        ado_pat = sm.get_credential("azure_devops_pat")
        self.ado_pat_var.set("")
        self._ado_pat_status.config(
            text="🔑 Token stored" if ado_pat else "",
            fg=theme.GREEN if ado_pat else theme.MUTED,
        )
        # Note-taking app settings
        self.obsidian_enabled_var.set(bool(sm.get("obsidian_enabled", False)))
        self.obsidian_host_var.set(sm.get("obsidian_host", "http://localhost:27123"))
        self.obsidian_folder_var.set(sm.get("obsidian_notes_folder", DEFAULT_NOTES_FOLDER))
        obsidian_key = sm.get_credential("obsidian_api_key")
        self.obsidian_key_var.set("")
        self._obsidian_key_status.config(
            text="🔑 Key stored" if obsidian_key else "",
            fg=theme.GREEN if obsidian_key else theme.MUTED,
        )
        self.notable_enabled_var.set(bool(sm.get("notable_enabled", False)))
        self.notable_dir_var.set(sm.get("notable_notes_directory", ""))

        self._update_preview()
        self._update_summary_preview()

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

        if self.summary_save_var.get() and not self.summary_dir_var.get().strip():
            messagebox.showerror("Invalid Settings",
                                 "Please specify a directory for the standalone summary file.")
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
        sm.set("summary_save_to_file", self.summary_save_var.get())
        sm.set("summary_file_directory", self.summary_dir_var.get().strip())
        sm.set("summary_file_date_format", self._get_summary_date_format_value())

        sm.set("archive_done_todos", self.archive_done_var.get())
        trigger_label = self.archive_trigger_var.get()
        sm.set("archive_trigger", "on_summary" if "summary" in trigger_label.lower() else "daily")
        sm.set("archive_file_directory", self.archive_dir_var.get().strip() or ".")
        sm.set("ui_theme", self.theme_var.get())
        sm.set("hourly_summary_extra_context",
               self.hourly_context_text.get("1.0", tk.END).strip())
        sm.set("daily_summary_extra_context",
               self.daily_context_text.get("1.0", tk.END).strip())

        # External API settings
        sm.set("jira_enabled", self.jira_enabled_var.get())
        sm.set("jira_host", self.jira_host_var.get().strip())
        sm.set("jira_email", self.jira_email_var.get().strip())
        # Only update the token when the field is non-empty (user typed a new value).
        jira_token = self.jira_token_var.get().strip()
        if jira_token:
            sm.set_credential("jira_api_token", jira_token)
            self.jira_token_var.set("")
            self._jira_token_status.config(text="🔑 Token stored", fg=theme.GREEN)
        sm.set("azure_devops_enabled", self.ado_enabled_var.get())
        sm.set("azure_devops_org_url", self.ado_org_url_var.get().strip())
        ado_pat = self.ado_pat_var.get().strip()
        if ado_pat:
            sm.set_credential("azure_devops_pat", ado_pat)
            self.ado_pat_var.set("")
            self._ado_pat_status.config(text="🔑 Token stored", fg=theme.GREEN)
        # Note-taking app settings
        sm.set("obsidian_enabled", self.obsidian_enabled_var.get())
        sm.set("obsidian_host", self.obsidian_host_var.get().strip())
        sm.set("obsidian_notes_folder", self.obsidian_folder_var.get().strip() or DEFAULT_NOTES_FOLDER)
        obsidian_key = self.obsidian_key_var.get().strip()
        if obsidian_key:
            sm.set_credential("obsidian_api_key", obsidian_key)
            self.obsidian_key_var.set("")
            self._obsidian_key_status.config(text="🔑 Key stored", fg=theme.GREEN)
        sm.set("notable_enabled", self.notable_enabled_var.get())
        sm.set("notable_notes_directory", self.notable_dir_var.get().strip())

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
