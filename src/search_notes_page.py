"""
Search Notes Page - Search past work log entries and export results.

Allows users to:
  - Search notes by keyword across a date range (yesterday, last 7 days, custom)
  - View every matching entry with its timestamp, title, and AI summary
  - Ask the LLM to analyse the matched entries (themes, patterns, progress summary)
  - Export results (with optional AI analysis) as:
      • Markdown  — formal headed report suitable for a manager/boss review
      • CSV       — spreadsheet-friendly data for checks and analysis
      • Highlights — a plain-text digest of the most interesting / AI-summarised entries
"""
import csv
import datetime
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import requests
import theme
from data_repository import DataRepository

_MARKER_TITLES = ("DAY STARTED", "DAY ENDED", "HOURLY SUMMARY", "END OF DAY SUMMARY")

_DEFAULT_AI_PROMPT = (
    "Please analyse these work log entries. "
    "Identify any recurring themes or patterns, highlight what progress was made, "
    "and give a concise summary of what this work meant overall."
)


def _is_marker(title: str) -> bool:
    return any(m in title for m in _MARKER_TITLES)


class SearchNotesPage(tk.Frame):
    """Page for searching past work log notes and exporting results."""

    def __init__(self, parent, data_repository: DataRepository, settings_manager=None):
        """
        Initialise the Search Notes page.

        Args:
            parent: Parent tkinter widget.
            data_repository: Data repository instance.
            settings_manager: SettingsManager instance for LLM configuration.
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.data_repository = data_repository
        self.settings_manager = settings_manager
        self._results: list = []
        self._ai_analysis: str = ""
        self._create_widgets()

    # ── Widget construction ───────────────────────────────────────────────────

    def _create_widgets(self):
        # ── Header ────────────────────────────────────────────────────────────
        header_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        header_frame.pack(fill='x', padx=10, pady=(10, 4))

        tk.Label(
            header_frame, text="Search Notes",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')

        # ── Keyword row ───────────────────────────────────────────────────────
        kw_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        kw_frame.pack(fill='x', padx=10, pady=2)

        tk.Label(
            kw_frame, text="Keyword:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 5))

        self.keyword_var = tk.StringVar()
        keyword_entry = tk.Entry(
            kw_frame, textvariable=self.keyword_var, width=30,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
        )
        keyword_entry.pack(side='left', padx=(0, 8))
        keyword_entry.bind('<Return>', lambda _e: self._run_search())

        # ── Date range row ────────────────────────────────────────────────────
        date_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        date_frame.pack(fill='x', padx=10, pady=2)

        tk.Label(
            date_frame, text="From:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 4))

        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        self.from_var = tk.StringVar(value=yesterday)
        tk.Entry(
            date_frame, textvariable=self.from_var, width=12,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
        ).pack(side='left', padx=(0, 8))

        tk.Label(
            date_frame, text="To:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 4))

        self.to_var = tk.StringVar(value=today_str)
        tk.Entry(
            date_frame, textvariable=self.to_var, width=12,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
        ).pack(side='left', padx=(0, 8))

        # Quick date range shortcuts
        theme.RoundedButton(
            date_frame, text="Yesterday", command=self._set_yesterday,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=10, cursor='hand2',
        ).pack(side='left', padx=2)
        theme.RoundedButton(
            date_frame, text="Last 7 Days", command=self._set_last_7,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=11, cursor='hand2',
        ).pack(side='left', padx=2)
        theme.RoundedButton(
            date_frame, text="Last 30 Days", command=self._set_last_30,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=12, cursor='hand2',
        ).pack(side='left', padx=2)
        theme.RoundedButton(
            date_frame, text="All Time", command=self._set_all_time,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=9, cursor='hand2',
        ).pack(side='left', padx=2)

        # ── Search button row ─────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        search_frame.pack(fill='x', padx=10, pady=6)

        theme.RoundedButton(
            search_frame, text="Search", command=self._run_search,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD, width=10, cursor='hand2',
        ).pack(side='left', padx=(0, 6))

        self.status_label = tk.Label(
            search_frame, text="Enter a keyword and press Search",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(side='left')

        # ── Results treeview ──────────────────────────────────────────────────
        list_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        columns = ('date', 'time', 'ticket', 'title', 'summary')
        self.result_tree = ttk.Treeview(
            list_frame, columns=columns, show='headings', height=8,
        )
        self.result_tree.heading('date', text='Date')
        self.result_tree.heading('time', text='Time')
        self.result_tree.heading('ticket', text='Ticket')
        self.result_tree.heading('title', text='Title / Notes')
        self.result_tree.heading('summary', text='AI Summary')

        self.result_tree.column('date', width=90, stretch=False)
        self.result_tree.column('time', width=60, stretch=False)
        self.result_tree.column('ticket', width=90, stretch=False)
        self.result_tree.column('title', width=250)
        self.result_tree.column('summary', width=350)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical',
                                  command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        self.result_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Double-click shows full detail popup
        self.result_tree.bind('<Double-1>', self._show_detail)

        # ── AI Analysis section ───────────────────────────────────────────────
        ai_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        ai_frame.pack(fill='x', padx=10, pady=(4, 2))

        ai_top = tk.Frame(ai_frame, bg=theme.WINDOW_BG)
        ai_top.pack(fill='x')

        tk.Label(
            ai_top, text="Ask AI about these results:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 8))

        self._analyse_btn = theme.RoundedButton(
            ai_top, text="🤖 Analyse with AI",
            command=self._run_ai_analysis,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=18, cursor='hand2',
        )
        self._analyse_btn.pack(side='left', padx=(0, 6))

        self._ai_status_label = tk.Label(
            ai_top, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self._ai_status_label.pack(side='left')

        self.ai_prompt_var = tk.StringVar(value=_DEFAULT_AI_PROMPT)
        self.ai_prompt_entry = tk.Entry(
            ai_frame, textvariable=self.ai_prompt_var,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
            font=theme.FONT_BODY,
        )
        self.ai_prompt_entry.pack(fill='x', pady=(4, 2))

        self.ai_response_box = tk.Text(
            ai_frame, height=5, wrap=tk.WORD,
            font=theme.FONT_BODY, bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
            padx=6, pady=4, state='disabled',
        )
        self.ai_response_box.pack(fill='x', pady=(2, 4))

        # ── Export buttons ────────────────────────────────────────────────────
        export_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        export_frame.pack(fill='x', padx=10, pady=(4, 10))

        tk.Label(
            export_frame, text="Export results as:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(side='left', padx=(0, 8))

        theme.RoundedButton(
            export_frame, text="📄 Markdown (Boss Review)",
            command=self._export_markdown,
            bg=theme.PRIMARY_D, fg=theme.TEXT,
            font=theme.FONT_BODY, width=22, cursor='hand2',
        ).pack(side='left', padx=3)

        theme.RoundedButton(
            export_frame, text="📊 CSV (Data Check)",
            command=self._export_csv,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=18, cursor='hand2',
        ).pack(side='left', padx=3)

        theme.RoundedButton(
            export_frame, text="✨ Highlights",
            command=self._export_highlights,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=12, cursor='hand2',
        ).pack(side='left', padx=3)

    # ── Date shortcut helpers ─────────────────────────────────────────────────

    def _set_yesterday(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.from_var.set(yesterday.strftime("%Y-%m-%d"))
        self.to_var.set(yesterday.strftime("%Y-%m-%d"))

    def _set_last_7(self):
        end = datetime.date.today()
        start = end - datetime.timedelta(days=6)
        self.from_var.set(start.strftime("%Y-%m-%d"))
        self.to_var.set(end.strftime("%Y-%m-%d"))

    def _set_last_30(self):
        end = datetime.date.today()
        start = end - datetime.timedelta(days=29)
        self.from_var.set(start.strftime("%Y-%m-%d"))
        self.to_var.set(end.strftime("%Y-%m-%d"))

    def _set_all_time(self):
        self.from_var.set("")
        self.to_var.set("")

    # ── Date parsing helper ───────────────────────────────────────────────────

    def _parse_date_range(self) -> tuple:
        """Return (start_date, end_date) or raise ValueError."""
        from_str = self.from_var.get().strip()
        to_str = self.to_var.get().strip()
        start_date: Optional[datetime.date] = None
        end_date: Optional[datetime.date] = None
        if from_str:
            start_date = datetime.datetime.strptime(from_str, "%Y-%m-%d").date()
        if to_str:
            end_date = datetime.datetime.strptime(to_str, "%Y-%m-%d").date()
        return start_date, end_date

    # ── Search ────────────────────────────────────────────────────────────────

    def _run_search(self):
        """Execute the keyword search and populate the results treeview."""
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showinfo(
                "Keyword Required",
                "Please enter a keyword to search for.\n\n"
                "For example: 'standup', 'bug fix', or a ticket number.",
            )
            return

        try:
            start_date, end_date = self._parse_date_range()
        except ValueError:
            messagebox.showerror(
                "Invalid Date",
                "Please enter dates in YYYY-MM-DD format, or leave them blank for no limit.",
            )
            return

        # Clear old results
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self._results = []
        self._ai_analysis = ""
        self._set_ai_response("")
        self._ai_status_label.config(text="")

        raw = self.data_repository.search_tasks(keyword, start_date, end_date)
        self._results = [r for r in raw if not _is_marker(r.get('Title', ''))]

        for task in self._results:
            start_str = task.get('Start Time', '')
            date_disp, time_disp = '', ''
            if start_str:
                try:
                    dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    date_disp = dt.strftime("%Y-%m-%d")
                    time_disp = dt.strftime("%H:%M")
                except ValueError:
                    date_disp = start_str

            summary_short = task.get('AI Summary', '').replace('\n', ' ')[:120]
            if len(task.get('AI Summary', '')) > 120:
                summary_short += '…'

            self.result_tree.insert('', 'end', values=(
                date_disp,
                time_disp,
                task.get('Ticket', ''),
                task.get('Title', ''),
                summary_short,
            ))

        count = len(self._results)
        date_range_label = self._date_range_label(start_date, end_date)
        self.status_label.config(
            text=f"Found {count} result(s) for '{keyword}'{date_range_label}",
        )

    def _date_range_label(self, start_date, end_date) -> str:
        if start_date and end_date:
            if start_date == end_date:
                return f" on {start_date}"
            return f" between {start_date} and {end_date}"
        if start_date:
            return f" from {start_date}"
        if end_date:
            return f" up to {end_date}"
        return " (all time)"

    # ── AI Analysis ───────────────────────────────────────────────────────────

    def _run_ai_analysis(self):
        """Send the search results to the LLM and display the analysis."""
        if not self._results:
            messagebox.showinfo(
                "No Results",
                "Please run a search first so there are entries for the AI to analyse.",
            )
            return

        if not self.settings_manager:
            messagebox.showwarning(
                "AI Not Available",
                "Settings are not connected — cannot reach the AI model.",
            )
            return

        user_prompt = self.ai_prompt_var.get().strip()
        if not user_prompt:
            user_prompt = _DEFAULT_AI_PROMPT

        # Build context from search results
        keyword = self.keyword_var.get().strip()
        from_str = self.from_var.get().strip() or "all time"
        to_str = self.to_var.get().strip() or "all time"

        entries_text_parts = []
        for task in self._results:
            start_str = task.get('Start Time', '')
            try:
                dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                stamp = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                stamp = start_str

            ticket = task.get('Ticket', '') or '(no ticket)'
            title = task.get('Title', '').replace('\n', ' ')
            summary = task.get('AI Summary', '').strip()

            entry_lines = [f"[{stamp}] {ticket} — {title}"]
            if summary:
                entry_lines.append(f"  Summary: {summary}")
            entries_text_parts.append('\n'.join(entry_lines))

        entries_text = '\n\n'.join(entries_text_parts)

        full_prompt = (
            f"The following are work log entries matching the keyword \"{keyword}\" "
            f"between {from_str} and {to_str}.\n\n"
            f"{entries_text}\n\n"
            f"{user_prompt}"
        )

        # Disable button and show spinner text while waiting
        self._analyse_btn.config(state=tk.DISABLED)
        self._ai_status_label.config(text="Analysing…")
        self._set_ai_response("")

        def _call_llm():
            payload = {
                "model": self.settings_manager.get("ai_model"),
                "prompt": full_prompt,
                "stream": False,
            }
            try:
                response = requests.post(
                    self.settings_manager.get("ai_api_url"),
                    json=payload,
                    timeout=self.settings_manager.get("llm_request_timeout"),
                )
                if response.status_code == 200:
                    analysis = response.json().get("response", "").strip()
                else:
                    analysis = f"Error from AI: HTTP {response.status_code}"
            except requests.exceptions.Timeout:
                analysis = (
                    "AI request timed out. "
                    "Try increasing the LLM timeout in Settings, or use a smaller date range."
                )
            except requests.exceptions.ConnectionError:
                analysis = (
                    "Could not connect to the AI service. "
                    "Check that Ollama is running and the API URL in Settings is correct."
                )
            except Exception as exc:
                analysis = f"AI connection failed: {exc}"

            # Update UI on the main thread
            self.after(0, lambda: self._on_analysis_done(analysis))

        threading.Thread(target=_call_llm, daemon=True).start()

    def _on_analysis_done(self, analysis: str):
        """Called on the main thread once the LLM response is ready."""
        self._ai_analysis = analysis
        self._set_ai_response(analysis)
        self._analyse_btn.config(state=tk.NORMAL)
        self._ai_status_label.config(text="Analysis complete.")

    def _set_ai_response(self, text: str):
        """Replace the content of the AI response text box."""
        self.ai_response_box.config(state='normal')
        self.ai_response_box.delete('1.0', tk.END)
        self.ai_response_box.insert('1.0', text)
        self.ai_response_box.config(state='disabled')

    # ── Detail popup ──────────────────────────────────────────────────────────

    def _show_detail(self, _event):
        """Show full details for the double-clicked result."""
        selection = self.result_tree.selection()
        if not selection:
            return
        idx = self.result_tree.index(selection[0])
        if idx >= len(self._results):
            return
        task = self._results[idx]

        win = tk.Toplevel(self)
        win.title("Entry Detail")
        win.geometry("600x400")
        win.configure(bg=theme.WINDOW_BG)
        win.transient(self)

        tk.Label(
            win, text=f"{task.get('Start Time', '')}  —  {task.get('Ticket', '(no ticket)')}",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(12, 2))

        tk.Label(
            win, text=task.get('Title', ''),
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
            wraplength=560, justify='left',
        ).pack(anchor='w', padx=15, pady=(0, 8))

        tk.Label(
            win, text="AI Summary:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(anchor='w', padx=15)

        summary_box = tk.Text(
            win, height=10, wrap=tk.WORD,
            font=theme.FONT_BODY, bg=theme.INPUT_BG, fg=theme.TEXT,
            relief='flat', padx=6, pady=4, state='disabled',
        )
        summary_box.pack(fill='both', expand=True, padx=15, pady=(4, 12))
        summary_box.config(state='normal')
        summary_box.insert('1.0', task.get('AI Summary', '(no summary)'))
        summary_box.config(state='disabled')

        theme.RoundedButton(
            win, text="Close", command=win.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=8, cursor='hand2',
        ).pack(pady=(0, 10))

    # ── Export helpers ────────────────────────────────────────────────────────

    def _require_results(self) -> bool:
        if not self._results:
            messagebox.showinfo(
                "No Results",
                "Please run a search first to produce results to export.",
            )
            return False
        return True

    def _ask_save_path(self, title: str, default_ext: str, filetypes: list) -> Optional[str]:
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=default_ext,
            filetypes=filetypes,
        )
        return path or None

    # ── Export: Markdown ──────────────────────────────────────────────────────

    def _export_markdown(self):
        """Export results as a formal Markdown report for boss/manager review."""
        if not self._require_results():
            return

        path = self._ask_save_path(
            "Save Markdown Report",
            ".md",
            [("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return

        keyword = self.keyword_var.get().strip()
        from_str = self.from_var.get().strip() or "—"
        to_str = self.to_var.get().strip() or "—"
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"# Work Log Review — {keyword}",
            "",
            f"**Generated:** {generated_at}  ",
            f"**Search keyword:** `{keyword}`  ",
            f"**Date range:** {from_str} → {to_str}  ",
            f"**Total entries:** {len(self._results)}",
            "",
            "---",
            "",
        ]

        # AI Analysis section (if available)
        if self._ai_analysis:
            lines += [
                "## AI Analysis",
                "",
            ]
            for para in self._ai_analysis.splitlines():
                lines.append(para)
            lines += ["", "---", ""]

        # Group entries by date
        by_date: dict = {}
        for task in self._results:
            start_str = task.get('Start Time', '')
            try:
                dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                day_key = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                day_key = "Unknown Date"
                time_str = ""
            by_date.setdefault(day_key, []).append((time_str, task))

        for day in sorted(by_date.keys()):
            lines.append(f"## {day}")
            lines.append("")
            for time_str, task in sorted(by_date[day], key=lambda x: x[0]):
                ticket = task.get('Ticket', '') or '—'
                title = task.get('Title', '').replace('\n', ' ')
                summary = task.get('AI Summary', '').strip() or '*(no AI summary)*'
                lines.append(f"### {time_str} — {ticket}")
                lines.append("")
                lines.append(f"**Notes:** {title}")
                lines.append("")
                lines.append("**Summary of Thoughts:**")
                lines.append("")
                # Indent summary lines
                for para in summary.splitlines():
                    lines.append(f"> {para}" if para.strip() else ">")
                lines.append("")
                lines.append("---")
                lines.append("")

        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines))
            messagebox.showinfo("Exported", f"Markdown report saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ── Export: CSV ───────────────────────────────────────────────────────────

    def _export_csv(self):
        """Export results as a CSV file for data checking."""
        if not self._require_results():
            return

        path = self._ask_save_path(
            "Save CSV Export",
            ".csv",
            [("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        fieldnames = ["Date", "Time", "Ticket", "Title", "Duration (Min)",
                      "AI Summary", "Resolved"]

        try:
            with open(path, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for task in self._results:
                    start_str = task.get('Start Time', '')
                    date_val, time_val = '', ''
                    try:
                        dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                        date_val = dt.strftime("%Y-%m-%d")
                        time_val = dt.strftime("%H:%M")
                    except ValueError:
                        date_val = start_str
                    writer.writerow({
                        "Date": date_val,
                        "Time": time_val,
                        "Ticket": task.get('Ticket', ''),
                        "Title": task.get('Title', ''),
                        "Duration (Min)": task.get('Duration (Min)', ''),
                        "AI Summary": task.get('AI Summary', ''),
                        "Resolved": task.get('Resolved', ''),
                    })
                # Append AI analysis as a clearly labelled trailing row if present
                if self._ai_analysis:
                    writer.writerow({})
                    for i, line in enumerate(self._ai_analysis.splitlines()):
                        if not line.strip():
                            continue
                        writer.writerow({
                            "Date": "AI Analysis" if i == 0 else "",
                            "Time": "",
                            "Ticket": "",
                            "Title": line,
                            "Duration (Min)": "",
                            "AI Summary": "",
                            "Resolved": "",
                        })
            messagebox.showinfo("Exported", f"CSV file saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ── Export: Highlights ────────────────────────────────────────────────────

    def _export_highlights(self):
        """
        Export a plain-text highlights digest — entries that have a non-empty
        AI summary, presented in a scannable format ideal for quick review.
        """
        if not self._require_results():
            return

        path = self._ask_save_path(
            "Save Highlights",
            ".txt",
            [("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        keyword = self.keyword_var.get().strip()
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        highlighted = [t for t in self._results if t.get('AI Summary', '').strip()]

        lines = [
            f"HIGHLIGHTS — {keyword}",
            f"Generated: {generated_at}",
            f"Entries with AI summaries: {len(highlighted)} / {len(self._results)} total",
            "=" * 60,
            "",
        ]

        # AI analysis (if available)
        if self._ai_analysis:
            lines += [
                "AI ANALYSIS",
                "-" * 40,
                self._ai_analysis,
                "",
                "=" * 60,
                "",
            ]

        if not highlighted:
            lines.append("No entries with AI summaries were found for this search.")
        else:
            for task in highlighted:
                start_str = task.get('Start Time', '')
                try:
                    dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    stamp = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    stamp = start_str

                ticket = task.get('Ticket', '') or '(no ticket)'
                title = task.get('Title', '').replace('\n', ' ')
                summary = task.get('AI Summary', '').strip()

                lines.append(f"[{stamp}]  {ticket}")
                lines.append(f"Task: {title}")
                lines.append(f"Summary: {summary}")
                lines.append("-" * 40)
                lines.append("")

        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(lines))
            messagebox.showinfo("Exported", f"Highlights file saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def refresh(self):
        """Called when navigating to this page — reset to yesterday's date range."""
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self.from_var.set(yesterday)
        self.to_var.set(today_str)
        self.status_label.config(text="Enter a keyword and press Search")
        self._ai_status_label.config(text="")
