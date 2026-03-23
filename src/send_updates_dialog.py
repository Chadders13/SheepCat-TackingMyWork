"""
Send Updates dialog for SheepCat Work Tracker.

Allows the user to select one or more work-log entries (optionally across
multiple days), verify the linked ticket exists in an external system
(Jira or Azure DevOps), preview an AI-generated comment that combines all
selected entries, and — with explicit consent — post that comment to the
external system.

Privacy philosophy: **no data leaves the machine without the user clicking
"Send Update"**.  Every destructive (write) action is gated behind a
confirmation step.
"""
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests

import theme
from external_api_service import APIServiceFactory


_TICKET_COL_WIDTHS = {"Date": 85, "Time": 55, "Resolved": 70, "Ticket": 90, "Title": 220}


class SendUpdatesDialog:
    """Modal dialog for sending work-log updates to external ticket systems.

    Args:
        parent:           The parent Tk widget (root window).
        settings_manager: Application :class:`~settings_manager.SettingsManager`.
        data_repository:  The active :class:`~data_repository.DataRepository`
                          used to retrieve tasks.
    """

    def __init__(self, parent, settings_manager, data_repository):
        self.parent = parent
        self.settings_manager = settings_manager
        self.data_repository = data_repository

        self._services = APIServiceFactory.get_configured_services(settings_manager)
        self._selected_tasks = []
        self._verified_ticket_info = None
        self._preview_text = ""

        self._build_dialog()

    # ------------------------------------------------------------------
    # Dialog construction
    # ------------------------------------------------------------------

    def _build_dialog(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Send Updates to External System")
        dialog.geometry("700x700")
        dialog.minsize(600, 500)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)
        self._dialog = dialog

        # ── Outer scrollable area ────────────────────────────────────────────
        outer = tk.Frame(dialog, bg=theme.WINDOW_BG)
        outer.pack(fill='both', expand=True)

        canvas = tk.Canvas(outer, bg=theme.WINDOW_BG, highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        # Inner frame that holds all dialog content
        inner = tk.Frame(canvas, bg=theme.WINDOW_BG)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        inner.bind('<Configure>', _on_inner_configure)
        canvas.bind('<Configure>', _on_canvas_configure)

        # Mouse-wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, 'units')
            elif event.num == 5:
                canvas.yview_scroll(1, 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        canvas.bind_all('<Button-4>', _on_mousewheel_linux)
        canvas.bind_all('<Button-5>', _on_mousewheel_linux)

        # Clean up mousewheel bindings when dialog is closed
        def _on_dialog_destroy():
            try:
                canvas.unbind_all('<MouseWheel>')
                canvas.unbind_all('<Button-4>')
                canvas.unbind_all('<Button-5>')
            except tk.TclError:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", _on_dialog_destroy)

        self._canvas = canvas

        # ── Consent banner ───────────────────────────────────────────────────
        banner = tk.Frame(inner, bg=theme.SURFACE_BG, pady=8)
        banner.pack(fill='x', padx=0, pady=0)
        tk.Label(
            banner,
            text="🔒  Privacy notice: no data is sent to external systems without your explicit confirmation.",
            font=theme.FONT_SMALL, bg=theme.SURFACE_BG, fg=theme.ACCENT,
            wraplength=660, justify='left',
        ).pack(padx=15)

        # ── Step 1 — Select tickets ──────────────────────────────────────────
        tk.Label(
            inner, text="Step 1 — Select ticket entries (hold Ctrl/Shift for multiple)",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(12, 2))

        # Date range controls
        date_ctrl_frame = tk.Frame(inner, bg=theme.WINDOW_BG)
        date_ctrl_frame.pack(fill='x', padx=15, pady=(0, 4))

        tk.Label(
            date_ctrl_frame, text="Load tasks from:",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(side='left', padx=(0, 6))

        theme.RoundedButton(
            date_ctrl_frame, text="Today",
            command=lambda: self._reload_tasks(0),
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=8, cursor='hand2',
        ).pack(side='left', padx=2)

        theme.RoundedButton(
            date_ctrl_frame, text="Yesterday",
            command=lambda: self._reload_tasks(1),
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left', padx=2)

        theme.RoundedButton(
            date_ctrl_frame, text="Last 7 Days",
            command=lambda: self._reload_tasks(7),
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=11, cursor='hand2',
        ).pack(side='left', padx=2)

        theme.RoundedButton(
            date_ctrl_frame, text="Last 30 Days",
            command=lambda: self._reload_tasks(30),
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=12, cursor='hand2',
        ).pack(side='left', padx=2)

        ticket_outer = tk.Frame(inner, bg=theme.WINDOW_BG)
        ticket_outer.pack(fill='x', padx=15, pady=(0, 8))

        cols = ("Date", "Time", "Ticket", "Title", "Resolved")
        self._ticket_tree = ttk.Treeview(
            ticket_outer, columns=cols, show='headings', height=7,
            selectmode='extended',
        )
        col_widths = _TICKET_COL_WIDTHS
        for col in cols:
            self._ticket_tree.heading(col, text=col)
            self._ticket_tree.column(col, width=col_widths.get(col, 120), anchor='w')

        vsb = ttk.Scrollbar(ticket_outer, orient='vertical',
                            command=self._ticket_tree.yview)
        self._ticket_tree.configure(yscrollcommand=vsb.set)
        self._ticket_tree.pack(side='left', fill='x', expand=True)
        vsb.pack(side='right', fill='y')

        self._ticket_tree.bind('<<TreeviewSelect>>', self._on_ticket_selected)

        self._status_var = tk.StringVar(value="Loading today's tasks…")
        self._status_label = tk.Label(
            inner, textvariable=self._status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            anchor='w',
        )
        self._status_label.pack(fill='x', padx=15, pady=(0, 4))

        # ── Step 2 — Choose API service ──────────────────────────────────────
        tk.Label(
            inner, text="Step 2 — Choose external system",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        svc_frame = tk.Frame(inner, bg=theme.WINDOW_BG)
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
            svc_combo.bind('<<ComboboxSelected>>', self._on_service_changed)
        else:
            tk.Label(
                svc_frame,
                text="⚠  No external APIs configured. Go to Settings → External API Settings.",
                font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.ACCENT,
            ).pack()

        # ── Step 3 — Verify ticket ───────────────────────────────────────────
        tk.Label(
            inner, text="Step 3 — Verify ticket in external system",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        verify_frame = tk.Frame(inner, bg=theme.WINDOW_BG)
        verify_frame.pack(anchor='w', padx=15, pady=(0, 8))

        self._btn_verify = theme.RoundedButton(
            verify_frame, text="🔍 Verify Ticket",
            command=self._verify_ticket,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY, width=18,
            state=tk.DISABLED, cursor='hand2',
        )
        self._btn_verify.pack(side='left')

        self._verify_status_var = tk.StringVar()
        tk.Label(
            verify_frame, textvariable=self._verify_status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(side='left', padx=10)

        self._ticket_detail_var = tk.StringVar()
        tk.Label(
            inner, textvariable=self._ticket_detail_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
            wraplength=660, justify='left', anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 4))

        # ── Step 4 — AI preview ──────────────────────────────────────────────
        tk.Label(
            inner, text="Step 4 — Review AI-generated update",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        preview_outer = tk.Frame(inner, bg=theme.WINDOW_BG)
        preview_outer.pack(fill='x', padx=15, pady=(0, 4))

        self._btn_preview = theme.RoundedButton(
            preview_outer, text="✨ Generate Preview",
            command=self._generate_preview,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY, width=18,
            state=tk.DISABLED, cursor='hand2',
        )
        self._btn_preview.pack(anchor='w', pady=(0, 6))

        self._preview_text_widget = tk.Text(
            inner, height=6, wrap=tk.WORD,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat', padx=6, pady=4,
        )
        self._preview_text_widget.pack(fill='x', padx=15, pady=(0, 8))

        # ── Step 5 — Send ────────────────────────────────────────────────────
        btn_frame = tk.Frame(inner, bg=theme.WINDOW_BG)
        btn_frame.pack(pady=10)

        self._btn_send = theme.RoundedButton(
            btn_frame, text="✅ Send Update",
            command=self._confirm_and_send,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=18,
            state=tk.DISABLED, cursor='hand2',
        )
        self._btn_send.pack(side='left', padx=5)

        theme.RoundedButton(
            btn_frame, text="Close",
            command=_on_dialog_destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, cursor='hand2',
        ).pack(side='left', padx=5)

        # Load today's tasks in background
        self._days_back = 0
        threading.Thread(target=self._load_tasks, daemon=True).start()

    # ------------------------------------------------------------------
    # Task loading
    # ------------------------------------------------------------------

    @staticmethod
    def _days_label(days_back: int) -> str:
        """Return a human-readable label for the given days-back value."""
        if days_back == 0:
            return "today"
        if days_back == 1:
            return "yesterday"
        return f"the last {days_back} days"

    def _reload_tasks(self, days_back: int):
        """Reload tasks using a new date range and reset downstream state."""
        self._days_back = days_back
        self._selected_tasks = []
        self._verified_ticket_info = None
        self._ticket_detail_var.set("")
        self._verify_status_var.set("")
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text = ""
        self._btn_verify.config(state=tk.DISABLED)
        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)

        self._status_var.set(f"Loading tasks from {self._days_label(days_back)}…")
        threading.Thread(target=self._load_tasks, daemon=True).start()

    def _load_tasks(self):
        """Fetch tasks from the repository for the configured date range (background thread)."""
        days_back = self._days_back
        try:
            today = datetime.date.today()
            if days_back == 0:
                tasks = self.data_repository.get_tasks_by_date(today)
            elif days_back == 1:
                yesterday = today - datetime.timedelta(days=1)
                tasks = self.data_repository.get_tasks_by_date(yesterday)
            else:
                start_dt = datetime.datetime.combine(
                    today - datetime.timedelta(days=days_back - 1),
                    datetime.time.min,
                )
                tasks = self.data_repository.get_tasks_since(start_dt)
        except Exception as exc:
            self._dialog.after(0, self._status_var.set,
                               f"Error loading tasks: {exc}")
            return

        # Filter out day-marker rows and tasks without tickets
        usable = [
            t for t in tasks
            if t.get("Ticket", "").strip()
            and "DAY STARTED" not in t.get("Title", "")
            and "DAY ENDED" not in t.get("Title", "")
        ]

        self._dialog.after(0, self._populate_ticket_tree, usable, days_back)

    def _populate_ticket_tree(self, tasks, days_back: int = 0):
        """Populate the treeview with tasks (main thread)."""
        self._ticket_tree.delete(*self._ticket_tree.get_children())
        self._tasks_cache = tasks

        label = self._days_label(days_back)

        if not tasks:
            self._status_var.set(f"No tickets logged for {label}.")
            return

        for idx, task in enumerate(tasks):
            start = task.get("Start Time", "")
            date_str = start[:10] if len(start) >= 10 else ""
            time_str = start[11:16] if len(start) >= 16 else start
            # The tag stores the index into _tasks_cache so _on_ticket_selected
            # can retrieve the original task dict efficiently.
            self._ticket_tree.insert(
                "", "end",
                values=(
                    date_str,
                    time_str,
                    task.get("Ticket", ""),
                    task.get("Title", "")[:60],
                    task.get("Resolved", "No"),
                ),
                tags=(str(idx),),
            )

        self._status_var.set(
            f"{len(tasks)} ticket(s) for {label}. "
            "Select one or more (same ticket number) to continue."
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_ticket_selected(self, _event=None):
        """Handle ticket selection in the treeview (supports multiple rows)."""
        sel = self._ticket_tree.selection()
        if not sel:
            self._selected_tasks = []
            return

        self._selected_tasks = []
        for item_id in sel:
            item = self._ticket_tree.item(item_id)
            tag = item["tags"][0] if item["tags"] else None
            if tag is not None:
                self._selected_tasks.append(self._tasks_cache[int(tag)])

        self._verified_ticket_info = None
        self._ticket_detail_var.set("")
        self._verify_status_var.set("")
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text = ""

        # Enable verify if a service is configured
        if self._services:
            self._btn_verify.config(state=tk.NORMAL)

        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)

    def _on_service_changed(self, _event=None):
        """Reset downstream state when the user picks a different service."""
        self._verified_ticket_info = None
        self._ticket_detail_var.set("")
        self._verify_status_var.set("")
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text = ""
        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)
        if self._selected_tasks and self._services:
            self._btn_verify.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Step 3 — Verify ticket
    # ------------------------------------------------------------------

    def _verify_ticket(self):
        if not self._selected_tasks:
            return

        # Extract and validate ticket IDs from all selected tasks
        ticket_ids = []
        for task in self._selected_tasks:
            raw = task.get("Ticket", "").strip()
            tid = raw.split(",")[0].strip()
            if tid and tid not in ticket_ids:
                ticket_ids.append(tid)

        if not ticket_ids:
            messagebox.showwarning(
                "No Ticket", "The selected task(s) have no ticket ID.", parent=self._dialog
            )
            return

        if len(ticket_ids) > 1:
            messagebox.showwarning(
                "Mixed Tickets",
                "The selected entries belong to different tickets:\n"
                + ", ".join(ticket_ids)
                + "\n\nPlease select entries that all share the same ticket number.",
                parent=self._dialog,
            )
            return

        ticket_id = ticket_ids[0]

        service = self._get_selected_service()
        if not service:
            return

        self._verify_status_var.set("🔄 Verifying…")
        self._btn_verify.config(state=tk.DISABLED)
        self._ticket_detail_var.set("")
        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)

        def _do_verify():
            info = service.verify_ticket(ticket_id)
            self._dialog.after(0, self._apply_verify_result, info, ticket_id)

        threading.Thread(target=_do_verify, daemon=True).start()

    def _apply_verify_result(self, info, ticket_id):
        self._btn_verify.config(state=tk.NORMAL)
        if info:
            self._verified_ticket_info = info
            self._verify_status_var.set("✅ Ticket found")
            detail = (
                f"  {info['id']}: {info['summary']}  |  "
                f"Status: {info['status']}  |  {info['url']}"
            )
            self._ticket_detail_var.set(detail)
            self._btn_preview.config(state=tk.NORMAL)
        else:
            self._verified_ticket_info = None
            self._verify_status_var.set(
                f"⚠  Ticket '{ticket_id}' not found in {self._get_selected_service_name()}."
            )
            self._ticket_detail_var.set("")
            self._btn_preview.config(state=tk.DISABLED)
            self._btn_send.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Step 4 — AI preview
    # ------------------------------------------------------------------

    def _generate_preview(self):
        if not self._selected_tasks or not self._verified_ticket_info:
            return

        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text_widget.insert(
            tk.END, "✨ Generating AI preview… please wait."
        )

        tasks = list(self._selected_tasks)
        ticket_info = self._verified_ticket_info

        def _do_generate():
            comment = self._call_llm_for_comment(tasks, ticket_info)
            self._dialog.after(0, self._apply_preview, comment)

        threading.Thread(target=_do_generate, daemon=True).start()

    def _call_llm_for_comment(self, tasks: list, ticket_info) -> str:
        """Ask the configured LLM to draft a comment for the external ticket.

        When multiple work-log entries are provided they are all included in
        the prompt so the AI can produce a combined summary.
        """
        ticket_summary = ticket_info.get("summary", "")

        # Build a compact log of all selected entries — omit timestamps and
        # dates because the ticketing system already records when the comment
        # was posted.
        entry_lines = []
        for task in tasks:
            title = task.get("Title", "").replace("\n", " ")
            duration = task.get("Duration (Min)", "")
            ai_sum = task.get("AI Summary", "").strip()
            line = f"- {title} ({duration} min)"
            if ai_sum:
                line += f"\n  Summary: {ai_sum}"
            entry_lines.append(line)

        entries_block = "\n".join(entry_lines)

        prompt = (
            f"The following work was done on a ticket titled '{ticket_summary}'.\n"
            f"Work log entries:\n{entries_block}\n\n"
            "Write a concise, professional progress update comment (2-4 sentences) "
            "that combines all the above entries and is suitable for posting directly "
            "to the ticket as a comment. "
            "Do NOT include the ticket number or any dates — the ticketing system "
            "already records those. "
            "Only mention another ticket number if the work directly references or "
            "depends on a different ticket. "
            "Use plain text, no markdown formatting."
        )

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

    def _apply_preview(self, comment: str):
        self._preview_text = comment
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text_widget.insert(tk.END, comment)
        self._btn_preview.config(state=tk.NORMAL)
        self._btn_send.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Step 5 — Confirm and send
    # ------------------------------------------------------------------

    def _confirm_and_send(self):
        """Gate the actual send behind an explicit confirmation dialog."""
        if not self._verified_ticket_info:
            messagebox.showwarning(
                "Verify First",
                "Please verify the ticket before sending.",
                parent=self._dialog,
            )
            return

        comment = self._preview_text_widget.get("1.0", tk.END).strip()
        if not comment:
            messagebox.showwarning(
                "No Content",
                "The update comment is empty. Please generate a preview first.",
                parent=self._dialog,
            )
            return

        ticket_id = self._verified_ticket_info.get("id", "")
        service_name = self._get_selected_service_name()

        confirmed = messagebox.askyesno(
            "Confirm Send",
            f"Send this update to {service_name} ticket {ticket_id}?\n\n"
            f"--- Preview ---\n{comment[:400]}{'…' if len(comment) > 400 else ''}",
            parent=self._dialog,
        )
        if not confirmed:
            return

        self._btn_send.config(state=tk.DISABLED)
        self._status_var.set("Sending update…")

        service = self._get_selected_service()

        def _do_send():
            success = service.send_comment(ticket_id, comment)
            self._dialog.after(0, self._apply_send_result, success, ticket_id, service_name)

        threading.Thread(target=_do_send, daemon=True).start()

    def _apply_send_result(self, success: bool, ticket_id: str, service_name: str):
        if success:
            self._status_var.set(
                f"✅ Update sent to {service_name} ticket {ticket_id}."
            )
            messagebox.showinfo(
                "Update Sent",
                f"Your update was successfully posted to {service_name} ticket {ticket_id}.",
                parent=self._dialog,
            )
        else:
            self._status_var.set("⚠  Failed to send update. Check credentials and connectivity.")
            messagebox.showerror(
                "Send Failed",
                f"Could not post the update to {service_name}.\n"
                "Please check your API credentials in Settings → External API Settings.",
                parent=self._dialog,
            )
            self._btn_send.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_service(self):
        """Return the currently selected service instance, or None."""
        name = self._service_var.get()
        for svc in self._services:
            if svc.name == name:
                return svc
        return None

    def _get_selected_service_name(self) -> str:
        svc = self._get_selected_service()
        return svc.name if svc else "unknown"
