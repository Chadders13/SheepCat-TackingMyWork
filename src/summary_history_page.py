"""
Summary History Page — View all logged days and re-run end-of-day summaries.

Allows users to:
  - Browse every day that has work-log data (shown newest-first in a list)
  - See the task count and any existing end-of-day summary for a selected day
  - Re-run (regenerate) the full day summary for any past day using the LLM
"""
import datetime
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Callable, Dict, List, Optional

import theme
from data_repository import DataRepository

_MARKER_TITLES = ("DAY STARTED", "DAY ENDED", "HOURLY SUMMARY", "END OF DAY SUMMARY")


def _is_marker(title: str) -> bool:
    return any(m in title for m in _MARKER_TITLES)


class SummaryHistoryPage(tk.Frame):
    """Page for browsing all logged days and re-running end-of-day summaries."""

    def __init__(
        self,
        parent,
        data_repository: DataRepository,
        generate_summary_fn: Callable[[Dict], str],
    ):
        """
        Initialise the Summary History page.

        Args:
            parent: Parent tkinter widget.
            data_repository: Data repository instance.
            generate_summary_fn: Callable that accepts a day_data dict
                (keys: summaries, tickets, tasks) and returns a summary string.
                This is typically ``WorkLoggerApp.generate_day_summary``.
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.data_repository = data_repository
        self.generate_summary_fn = generate_summary_fn
        self._dates: List[datetime.date] = []
        self._selected_date: Optional[datetime.date] = None

        self._create_widgets()

    # ── Widget construction ───────────────────────────────────────────────────

    def _create_widgets(self):
        # ── Header ────────────────────────────────────────────────────────────
        header_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        header_frame.pack(fill='x', padx=10, pady=(10, 4))

        tk.Label(
            header_frame, text="Summary History",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')

        tk.Label(
            header_frame,
            text="Select a day then click the 'Re-run Day Summary' button to regenerate it",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(side='left', padx=20)

        # ── Main content: left list + right detail ────────────────────────────
        content_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        content_frame.pack(fill='both', expand=True, padx=10, pady=6)

        # ── Left panel: date list ─────────────────────────────────────────────
        left_frame = tk.Frame(content_frame, bg=theme.SURFACE_BG, width=220)
        left_frame.pack(side='left', fill='y', padx=(0, 8))
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame, text="Available Days",
            font=theme.FONT_BODY_BOLD, bg=theme.SURFACE_BG, fg=theme.TEXT,
        ).pack(pady=(8, 4), padx=8)

        theme.RoundedButton(
            left_frame, text="↻  Refresh List",
            command=self._load_dates,
            bg=theme.PRIMARY_D, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=18, cursor='hand2',
        ).pack(pady=(0, 6))

        list_scroll = tk.Scrollbar(left_frame, orient='vertical')
        self.date_listbox = tk.Listbox(
            left_frame,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            font=theme.FONT_BODY,
            selectbackground=theme.PRIMARY_D,
            selectforeground=theme.TEXT,
            activestyle='none',
            yscrollcommand=list_scroll.set,
            width=24,
            relief='flat',
            highlightthickness=0,
        )
        list_scroll.config(command=self.date_listbox.yview)
        self.date_listbox.pack(side='left', fill='both', expand=True)
        list_scroll.pack(side='right', fill='y')

        self.date_listbox.bind('<<ListboxSelect>>', self._on_date_selected)

        # ── Right panel: summary detail ───────────────────────────────────────
        right_frame = tk.Frame(content_frame, bg=theme.WINDOW_BG)
        right_frame.pack(side='left', fill='both', expand=True)

        # Action row: info label + Re-run button
        action_frame = tk.Frame(right_frame, bg=theme.WINDOW_BG)
        action_frame.pack(fill='x', pady=(0, 6))

        self.day_info_label = tk.Label(
            action_frame,
            text="← Select a day from the list",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.day_info_label.pack(side='left', padx=4)

        self.btn_generate = theme.RoundedButton(
            action_frame, text="Re-run Day Summary",
            command=self._generate_summary,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=20, cursor='hand2',
            state=tk.DISABLED,
        )
        self.btn_generate.pack(side='right', padx=4)

        # Summary text area
        tk.Label(
            right_frame, text="Day Summary:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(anchor='w', padx=4)

        self.summary_text = scrolledtext.ScrolledText(
            right_frame, wrap=tk.WORD,
            font=theme.FONT_MONO,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            state=tk.DISABLED,
            relief='flat',
            height=20,
        )
        self.summary_text.pack(fill='both', expand=True, padx=4, pady=(4, 0))

        # Status bar
        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=4)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_dates(self):
        """Scan all tasks and populate the date listbox with unique logged days."""
        self.date_listbox.delete(0, tk.END)
        self._dates = []
        self._selected_date = None
        self.btn_generate.config(state=tk.DISABLED)
        self.day_info_label.config(text="← Select a day from the list")
        self._set_summary_text("")

        all_tasks = self.data_repository.get_all_tasks()
        unique_dates: set = set()

        for task in all_tasks:
            start_str = task.get('Start Time', '')
            if not start_str:
                continue
            try:
                dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                unique_dates.add(dt.date())
            except ValueError:
                continue

        # Sort newest first
        self._dates = sorted(unique_dates, reverse=True)

        for d in self._dates:
            self.date_listbox.insert(tk.END, d.strftime("%Y-%m-%d"))

        count = len(self._dates)
        self.status_label.config(
            text=f"{count} day(s) found with log data"
        )

    def _on_date_selected(self, _event=None):
        """Called when a date is clicked in the listbox."""
        selection = self.date_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        date = self._dates[idx]
        self._show_date_info(date)

    def _show_date_info(self, date: datetime.date):
        """Load and display info for the selected date."""
        tasks = self.data_repository.get_tasks_by_date(date)

        # Count real work tasks (exclude marker rows)
        real_tasks = [t for t in tasks if not _is_marker(t.get('Title', ''))]
        task_count = len(real_tasks)

        # Look for an existing end-of-day summary
        existing_summary = ""
        for t in tasks:
            if 'END OF DAY SUMMARY' in t.get('Title', ''):
                existing_summary = t.get('AI Summary', '').strip()
                break

        self._selected_date = date
        day_label = date.strftime("%A, %d %B %Y")
        self.day_info_label.config(
            text=f"{day_label}  —  {task_count} task(s)"
        )
        self.btn_generate.config(state=tk.NORMAL)

        if existing_summary:
            self._set_summary_text(existing_summary)
            self.status_label.config(
                text=f"Showing existing summary for {date}.  "
                     "Click 'Re-run Day Summary' to regenerate."
            )
        else:
            self._set_summary_text(
                "No existing summary found for this day.\n\n"
                "Click 'Re-run Day Summary' to generate one now."
            )
            self.status_label.config(
                text=f"No existing summary for {date}."
            )

    # ── Summary generation ────────────────────────────────────────────────────

    def _generate_summary(self):
        """Start a background thread to generate the summary for the selected day."""
        if self._selected_date is None:
            return

        self.btn_generate.config(state=tk.DISABLED)
        self.status_label.config(text="Generating summary… please wait")
        self._set_summary_text("Generating summary, please wait…")

        threading.Thread(
            target=self._generate_summary_thread,
            args=(self._selected_date,),
            daemon=True,
        ).start()

    def _generate_summary_thread(self, date: datetime.date):
        """Background thread: read day data and call the LLM."""
        tasks = self.data_repository.get_tasks_by_date(date)

        summaries: List[str] = []
        tickets: set = set()
        task_list: List[Dict] = []

        for row in tasks:
            ai_summary = row.get('AI Summary', '').strip()
            title = row.get('Title', '').strip()
            ticket = row.get('Ticket', '').strip()

            if ai_summary and not _is_marker(title):
                summaries.append(ai_summary)

            if ticket:
                for t in ticket.split(','):
                    t = t.strip()
                    if t:
                        tickets.add(t)

            if title and not _is_marker(title):
                task_list.append({
                    'title': title,
                    'ticket': ticket,
                    'duration': row.get('Duration (Min)', '0'),
                })

        day_data = {
            'summaries': summaries,
            'tickets': sorted(tickets),
            'tasks': task_list,
        }

        result = self.generate_summary_fn(day_data)

        # Update the UI on the main thread
        self.after(0, lambda: self._on_summary_ready(result, date))

    def _on_summary_ready(self, summary: str, date: datetime.date):
        """Called on the main thread once summary generation is complete."""
        self._set_summary_text(summary)
        self.btn_generate.config(state=tk.NORMAL)
        self.status_label.config(
            text=f"Summary generated for {date}.  You can copy the text above."
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_summary_text(self, text: str):
        """Replace the content of the read-only summary text area."""
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete('1.0', tk.END)
        if text:
            self.summary_text.insert('1.0', text)
        self.summary_text.config(state=tk.DISABLED)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def refresh(self):
        """Called when the page becomes visible; reload the date list."""
        self._load_dates()
