"""
Send Notes dialog for SheepCat Work Tracker.

Allows the user to generate a formatted Markdown note or summary from
today's work log and — with explicit consent — export it to a configured
note-taking application (Obsidian or Notable).

Privacy philosophy: **no data leaves the machine without the user clicking
"Export Note"**.  Every destructive (write) action is gated behind a
confirmation step.
"""
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests

import theme
from external_api_service import APIServiceFactory


class SendNotesDialog:
    """Modal dialog for exporting work summaries to note-taking apps.

    Args:
        parent:           The parent Tk widget (root window).
        settings_manager: Application :class:`~settings_manager.SettingsManager`.
        data_repository:  The active :class:`~data_repository.DataRepository`
                          used to retrieve today's tasks.
    """

    def __init__(self, parent, settings_manager, data_repository):
        self.parent = parent
        self.settings_manager = settings_manager
        self.data_repository = data_repository

        self._services = APIServiceFactory.get_configured_note_services(settings_manager)
        self._note_content = ""

        self._build_dialog()

    # ------------------------------------------------------------------
    # Dialog construction
    # ------------------------------------------------------------------

    def _build_dialog(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Export Note to Note-Taking App")
        dialog.geometry("720x680")
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)
        self._dialog = dialog

        # ── Consent banner ───────────────────────────────────────────────────
        banner = tk.Frame(dialog, bg=theme.SURFACE_BG, pady=8)
        banner.pack(fill='x', padx=0, pady=0)
        tk.Label(
            banner,
            text=(
                "🔒  Privacy notice: no data is exported to external apps "
                "without your explicit confirmation."
            ),
            font=theme.FONT_SMALL, bg=theme.SURFACE_BG, fg=theme.ACCENT,
            wraplength=680, justify='left',
        ).pack(padx=15)

        # ── Step 1 — Choose target app ────────────────────────────────────────
        tk.Label(
            dialog, text="Step 1 — Choose target app",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(12, 4))

        svc_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        svc_frame.pack(anchor='w', padx=15, pady=(0, 8))

        self._service_var = tk.StringVar()
        if self._services:
            service_names = [s.name for s in self._services]
            self._service_var.set(service_names[0])
            svc_combo = ttk.Combobox(
                svc_frame, textvariable=self._service_var,
                values=service_names, width=25, state='readonly',
            )
            svc_combo.pack(side='left')
        else:
            tk.Label(
                svc_frame,
                text=(
                    "⚠  No note-taking apps configured. "
                    "Go to Settings → Note-Taking App Settings."
                ),
                font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.ACCENT,
            ).pack()

        # ── Step 2 — Note title ───────────────────────────────────────────────
        tk.Label(
            dialog, text="Step 2 — Note title",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        title_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        title_frame.pack(fill='x', padx=15, pady=(0, 8))

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self._title_var = tk.StringVar(value=f"SheepCat Work Summary {today_str}")
        tk.Entry(
            title_frame, textvariable=self._title_var, width=60,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            font=theme.FONT_BODY,
        ).pack(side='left', fill='x', expand=True)

        # ── Step 3 — Note content ─────────────────────────────────────────────
        tk.Label(
            dialog, text="Step 3 — Review note content",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        gen_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        gen_frame.pack(anchor='w', padx=15, pady=(0, 6))

        self._btn_generate = theme.RoundedButton(
            gen_frame, text="✨ Generate Note",
            command=self._generate_note,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY, width=18,
            state=tk.NORMAL if self._services else tk.DISABLED,
            cursor='hand2',
        )
        self._btn_generate.pack(side='left')

        self._gen_status_var = tk.StringVar()
        tk.Label(
            gen_frame, textvariable=self._gen_status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(side='left', padx=10)

        note_outer = tk.Frame(dialog, bg=theme.WINDOW_BG)
        note_outer.pack(fill='both', expand=True, padx=15, pady=(0, 8))

        self._note_text_widget = tk.Text(
            note_outer, height=12, wrap=tk.WORD,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat', padx=6, pady=4,
        )
        vsb = ttk.Scrollbar(note_outer, orient='vertical',
                            command=self._note_text_widget.yview)
        self._note_text_widget.configure(yscrollcommand=vsb.set)
        self._note_text_widget.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # ── Step 4 — Export ────────────────────────────────────────────────────
        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_frame.pack(pady=10)

        self._btn_export = theme.RoundedButton(
            btn_frame, text="📤 Export Note",
            command=self._confirm_and_export,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=18,
            state=tk.DISABLED, cursor='hand2',
        )
        self._btn_export.pack(side='left', padx=5)

        theme.RoundedButton(
            btn_frame, text="Close",
            command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, cursor='hand2',
        ).pack(side='left', padx=5)

        self._status_var = tk.StringVar()
        tk.Label(
            dialog, textvariable=self._status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 8))

    # ------------------------------------------------------------------
    # Step 3 — Generate note content
    # ------------------------------------------------------------------

    def _generate_note(self):
        self._btn_generate.config(state=tk.DISABLED)
        self._btn_export.config(state=tk.DISABLED)
        self._gen_status_var.set("🔄 Generating…")
        self._note_text_widget.delete("1.0", tk.END)

        def _do_generate():
            content = self._build_note_content()
            self._dialog.after(0, self._apply_note_content, content)

        threading.Thread(target=_do_generate, daemon=True).start()

    def _build_note_content(self) -> str:
        """Fetch today's tasks and produce a Markdown-formatted note.

        Attempts to generate an AI-enhanced summary via the configured LLM;
        falls back to a plain-text listing if the LLM is unavailable.
        """
        try:
            today = datetime.date.today()
            tasks = self.data_repository.get_tasks_by_date(today)
        except Exception as exc:
            return f"*Error loading tasks: {exc}*"

        # Exclude day-marker rows
        work_tasks = [
            t for t in tasks
            if "DAY STARTED" not in t.get("Title", "")
            and "DAY ENDED" not in t.get("Title", "")
        ]

        if not work_tasks:
            return f"# {self._title_var.get()}\n\n*No tasks logged today.*\n"

        # Build a plain-text context for the LLM
        task_lines = []
        for t in work_tasks:
            ticket = t.get("Ticket", "").strip()
            title = t.get("Title", "").strip()
            duration = t.get("Duration (Min)", "")
            line = f"- {title}"
            if ticket:
                line += f" [{ticket}]"
            if duration:
                line += f" ({duration} min)"
            task_lines.append(line)

        tasks_text = "\n".join(task_lines)
        title = self._title_var.get()

        # Try LLM for a polished summary
        prompt = (
            f"I want to create a work summary note titled '{title}'.\n"
            f"Here is a list of tasks I worked on today:\n{tasks_text}\n\n"
            "Write a well-structured Markdown note with:\n"
            "1. A brief intro sentence summarising the day.\n"
            "2. A ## Tasks section listing each task concisely.\n"
            "3. A ## Summary section with 2-3 sentences describing overall progress.\n"
            "Use Markdown formatting."
        )
        llm_summary = self._call_llm(prompt)

        if llm_summary and not llm_summary.startswith("(LLM"):
            return llm_summary

        # Fallback: plain Markdown listing
        lines = [
            f"# {title}",
            "",
            f"*Generated by SheepCat on {datetime.date.today()}*",
            "",
            "## Tasks",
            "",
            tasks_text,
            "",
        ]
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        """Ask the configured LLM to produce a formatted note."""
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
            return f"(LLM error: HTTP {response.status_code})"
        except Exception as exc:
            return f"(LLM connection failed: {exc})"

    def _apply_note_content(self, content: str):
        self._note_content = content
        self._note_text_widget.delete("1.0", tk.END)
        self._note_text_widget.insert(tk.END, content)
        self._btn_generate.config(state=tk.NORMAL)
        self._btn_export.config(state=tk.NORMAL)
        self._gen_status_var.set("✅ Ready to export")

    # ------------------------------------------------------------------
    # Step 4 — Confirm and export
    # ------------------------------------------------------------------

    def _confirm_and_export(self):
        """Gate the actual export behind an explicit confirmation dialog."""
        content = self._note_text_widget.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning(
                "No Content",
                "The note is empty. Please generate note content first.",
                parent=self._dialog,
            )
            return

        title = self._title_var.get().strip() or "SheepCat Note"
        service = self._get_selected_service()
        if not service:
            return

        confirmed = messagebox.askyesno(
            "Confirm Export",
            f"Export this note to {service.name}?\n\n"
            f"Title: {title}\n\n"
            f"--- Preview ---\n{content[:300]}{'…' if len(content) > 300 else ''}",
            parent=self._dialog,
        )
        if not confirmed:
            return

        self._btn_export.config(state=tk.DISABLED)
        self._status_var.set(f"Exporting to {service.name}…")

        def _do_export():
            success = service.send_note(title, content)
            self._dialog.after(0, self._apply_export_result, success, title, service.name)

        threading.Thread(target=_do_export, daemon=True).start()

    def _apply_export_result(self, success: bool, title: str, service_name: str):
        if success:
            self._status_var.set(f"✅ Note exported to {service_name}.")
            messagebox.showinfo(
                "Note Exported",
                f"Your note '{title}' was successfully exported to {service_name}.",
                parent=self._dialog,
            )
        else:
            self._status_var.set(
                f"⚠  Failed to export note to {service_name}. "
                "Check credentials and settings."
            )
            messagebox.showerror(
                "Export Failed",
                f"Could not export the note to {service_name}.\n"
                "Please check your settings in Settings → Note-Taking App Settings.",
                parent=self._dialog,
            )
            self._btn_export.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_service(self):
        """Return the currently selected note service, or None."""
        name = self._service_var.get()
        for svc in self._services:
            if svc.name == name:
                return svc
        return None
