"""
Ad Hoc Report Page — Generate and save ad hoc update reports for managers.

Users can select a date range, generate a professional progress update (using
the LLM when available, or a formatted plain-text fallback), edit the result,
and either save it to a Markdown file or copy it to the clipboard.
"""
import os
import threading
import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog

import requests

from data_repository import DataRepository
from settings_manager import SettingsManager
import theme


class AdHocReportPage(tk.Frame):
    """Page for generating ad hoc update reports for managers."""

    def __init__(self, parent, data_repository: DataRepository,
                 settings_manager: SettingsManager):
        """
        Initialize the Ad Hoc Report page.

        Args:
            parent: Parent tkinter widget
            data_repository: Data repository instance
            settings_manager: Application settings manager
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.data_repository = data_repository
        self.settings_manager = settings_manager
        self._generating = False

        self._create_widgets()

    # ── Widget construction ────────────────────────────────────────────────

    def _create_widgets(self):
        """Build all UI widgets for the page."""
        # Header
        header_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        header_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(
            header_frame, text="Ad Hoc Manager Update",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')

        # Date range selector
        date_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        date_frame.pack(fill='x', padx=10, pady=5)

        today_str = datetime.date.today().strftime("%Y-%m-%d")

        tk.Label(
            date_frame, text="From:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 4))

        self.from_var = tk.StringVar(value=today_str)
        tk.Entry(
            date_frame, textvariable=self.from_var, width=12,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
        ).pack(side='left', padx=(0, 10))

        tk.Label(
            date_frame, text="To:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 4))

        self.to_var = tk.StringVar(value=today_str)
        tk.Entry(
            date_frame, textvariable=self.to_var, width=12,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
        ).pack(side='left', padx=(0, 10))

        tk.Button(
            date_frame, text="Today", command=self._set_today, width=8,
            bg=theme.SURFACE_BG, fg=theme.TEXT, relief='flat', cursor='hand2',
        ).pack(side='left', padx=2)

        self.generate_btn = tk.Button(
            date_frame, text="Generate Update", command=self._start_generate,
            width=16,
            bg=theme.PRIMARY, fg=theme.TEXT, relief='flat', cursor='hand2',
        )
        self.generate_btn.pack(side='left', padx=(10, 2))

        # Editable report text area
        text_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.report_text = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD,
            font=theme.FONT_MONO,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
        )
        self.report_text.pack(fill='both', expand=True)
        self.report_text.insert(
            '1.0',
            "Select a date range and click 'Generate Update' to create a report.",
        )
        self.report_text.config(state=tk.DISABLED)

        # Save / Copy buttons
        button_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        button_frame.pack(fill='x', padx=10, pady=5)

        self.save_btn = tk.Button(
            button_frame, text="Save to File", command=self._save_report,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=14, relief='flat', cursor='hand2',
            state=tk.DISABLED,
        )
        self.save_btn.pack(side='left', padx=5)

        self.copy_btn = tk.Button(
            button_frame, text="Copy to Clipboard", command=self._copy_to_clipboard,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=16, relief='flat', cursor='hand2',
            state=tk.DISABLED,
        )
        self.copy_btn.pack(side='left', padx=5)

        # Status label
        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=5)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _set_today(self):
        """Reset both date pickers to today."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self.from_var.set(today_str)
        self.to_var.set(today_str)

    def _parse_dates(self):
        """
        Parse and validate the from / to date entries.

        Returns:
            Tuple of (from_date, to_date) as datetime.date objects.

        Raises:
            ValueError: If a date is invalid or from_date > to_date.
        """
        try:
            from_date = datetime.datetime.strptime(
                self.from_var.get().strip(), "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError("'From' date must be in YYYY-MM-DD format.")

        try:
            to_date = datetime.datetime.strptime(
                self.to_var.get().strip(), "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError("'To' date must be in YYYY-MM-DD format.")

        if from_date > to_date:
            raise ValueError("'From' date must be on or before 'To' date.")

        return from_date, to_date

    def collect_tasks(self, from_date: datetime.date, to_date: datetime.date):
        """
        Collect all non-marker tasks between from_date and to_date (inclusive).

        Args:
            from_date: Start date (inclusive).
            to_date: End date (inclusive).

        Returns:
            List of task dictionaries.
        """
        _MARKERS = ('DAY STARTED', 'DAY ENDED', 'HOURLY SUMMARY', 'END OF DAY SUMMARY')
        tasks = []
        current = from_date
        while current <= to_date:
            day_tasks = self.data_repository.get_tasks_by_date(current)
            for task in day_tasks:
                title = task.get('Title', '')
                if not any(m in title for m in _MARKERS):
                    tasks.append(task)
            current += datetime.timedelta(days=1)
        return tasks

    def build_plain_report(self, tasks, from_date: datetime.date,
                           to_date: datetime.date) -> str:
        """
        Build a plain Markdown report without using the LLM.

        Args:
            tasks: List of task dictionaries.
            from_date: Start date of the report period.
            to_date: End date of the report period.

        Returns:
            Formatted Markdown string.
        """
        date_range = (
            from_date.strftime("%Y-%m-%d")
            if from_date == to_date
            else f"{from_date.strftime('%Y-%m-%d')} \u2013 {to_date.strftime('%Y-%m-%d')}"
        )
        lines = [f"# Work Update \u2014 {date_range}\n"]

        tickets = sorted({
            t.get('Ticket', '').strip()
            for t in tasks
            if t.get('Ticket', '').strip()
        })
        if tickets:
            lines.append(f"**Tickets:** {', '.join(tickets)}\n")

        lines.append("## Tasks Completed\n")
        for task in tasks:
            ticket = task.get('Ticket', '').strip()
            title = task.get('Title', '').strip()
            duration = task.get('Duration (Min)', '0')
            resolved = task.get('Resolved', 'No')
            ticket_str = f" [{ticket}]" if ticket else ""
            resolved_str = " \u2713" if resolved == "Yes" else ""
            lines.append(f"- {title}{ticket_str} \u2014 {duration} min{resolved_str}")

        return "\n".join(lines)

    def _call_llm(self, prompt: str):
        """
        Call the configured LLM to generate content.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            Response string, or None if the LLM is unreachable.
        """
        payload = {
            "model": self.settings_manager.get("ai_model"),
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = requests.post(
                self.settings_manager.get("ai_api_url"),
                json=payload,
                timeout=self.settings_manager.get("llm_request_timeout"),
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            return None
        except Exception:
            return None

    # ── Report generation ──────────────────────────────────────────────────

    def _start_generate(self):
        """Validate inputs then kick off report generation in a background thread."""
        if self._generating:
            return

        try:
            from_date, to_date = self._parse_dates()
        except ValueError as exc:
            messagebox.showerror("Invalid Date", str(exc))
            return

        self._generating = True
        self.generate_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete('1.0', tk.END)
        self.report_text.config(state=tk.DISABLED)
        self.status_label.config(text="Generating report\u2026")

        threading.Thread(
            target=self._generate_report,
            args=(from_date, to_date),
            daemon=True,
        ).start()

    def _generate_report(self, from_date: datetime.date, to_date: datetime.date):
        """
        Background thread: collect tasks and produce the report text.

        Posts results back to the main thread via :meth:`after`.
        """
        try:
            tasks = self.collect_tasks(from_date, to_date)

            if not tasks:
                report = "No tasks found for the selected date range."
            else:
                date_range = (
                    from_date.strftime("%Y-%m-%d")
                    if from_date == to_date
                    else f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
                )
                task_lines = "\n".join([
                    f"- {t.get('Title', '').strip()} "
                    f"(Ticket: {t.get('Ticket', 'N/A').strip() or 'N/A'}, "
                    f"{t.get('Duration (Min)', '0')} min, "
                    f"Resolved: {t.get('Resolved', 'No')})"
                    for t in tasks
                ])
                prompt = (
                    f"Create a professional manager update for the period {date_range}.\n\n"
                    f"Work completed:\n{task_lines}\n\n"
                    "Write a concise, professional update that:\n"
                    "1. Summarises the key work accomplished\n"
                    "2. Highlights any resolved issues\n"
                    "3. Mentions the tickets/references worked on\n"
                    "Format in Markdown. Keep it brief and suitable for sharing with a manager."
                )
                llm_result = self._call_llm(prompt)
                if llm_result:
                    report = f"# Work Update \u2014 {date_range}\n\n{llm_result}"
                else:
                    report = self.build_plain_report(tasks, from_date, to_date)

            self.after(0, lambda: self._show_report(report))
        except Exception as exc:  # pragma: no cover
            self.after(0, lambda: self._show_error(str(exc)))

    def _show_report(self, report: str):
        """Display the generated report and enable action buttons."""
        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete('1.0', tk.END)
        self.report_text.insert('1.0', report)
        self.save_btn.config(state=tk.NORMAL)
        self.copy_btn.config(state=tk.NORMAL)
        self.generate_btn.config(state=tk.NORMAL)
        self._generating = False
        self.status_label.config(
            text="Report generated. You can edit it before saving or copying."
        )

    def _show_error(self, msg: str):
        """Re-enable controls and show an error message."""
        self.generate_btn.config(state=tk.NORMAL)
        self._generating = False
        self.status_label.config(text=f"Error: {msg}")
        messagebox.showerror("Report Error", msg)

    # ── Save / Copy ────────────────────────────────────────────────────────

    def _get_report_text(self) -> str:
        """Return the current content of the report text area."""
        return self.report_text.get('1.0', 'end-1c')

    def _save_report(self):
        """Prompt the user for a save location and write the report to disk."""
        report = self._get_report_text()
        if not report:
            return

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        initial_file = f"manager_update_{today_str}.md"
        initial_dir = self.settings_manager.get("summary_file_directory", ".")

        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
            initialfile=initial_file,
            initialdir=initial_dir,
            title="Save Manager Update",
        )
        if not filepath:
            return  # User cancelled

        try:
            parent_dir = os.path.dirname(filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(report)
            self.status_label.config(text=f"Saved: {filepath}")
        except Exception as exc:
            messagebox.showerror("Save Error", f"Could not save file:\n{exc}")

    def _copy_to_clipboard(self):
        """Copy the current report text to the system clipboard."""
        report = self._get_report_text()
        if not report:
            return
        self.clipboard_clear()
        self.clipboard_append(report)
        self.status_label.config(text="Report copied to clipboard.")

    # ── Page lifecycle ─────────────────────────────────────────────────────

    def refresh(self):
        """Reset date pickers to today when the page is navigated to."""
        self._set_today()
