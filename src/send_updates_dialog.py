"""
Send Updates dialog for SheepCat Work Tracker.

Allows the user to select a work-log entry from today, verify the linked
ticket exists in an external system (Jira or Azure DevOps), preview an
AI-generated comment, and — with explicit consent — post that comment to
the external system.

Privacy philosophy: **no data leaves the machine without the user clicking
"Send Update"**.  Every destructive (write) action is gated behind a
confirmation step.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import requests

import theme
from external_api_service import APIServiceFactory


class SendUpdatesDialog:
    """Modal dialog for sending work-log updates to external ticket systems.

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

        self._services = APIServiceFactory.get_configured_services(settings_manager)
        self._selected_task = None
        self._verified_ticket_info = None
        self._preview_text = ""

        self._build_dialog()

    # ------------------------------------------------------------------
    # Dialog construction
    # ------------------------------------------------------------------

    def _build_dialog(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title("Send Updates to External System")
        dialog.geometry("700x680")
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)
        self._dialog = dialog

        # ── Consent banner ───────────────────────────────────────────────────
        banner = tk.Frame(dialog, bg=theme.SURFACE_BG, pady=8)
        banner.pack(fill='x', padx=0, pady=0)
        tk.Label(
            banner,
            text="🔒  Privacy notice: no data is sent to external systems without your explicit confirmation.",
            font=theme.FONT_SMALL, bg=theme.SURFACE_BG, fg=theme.ACCENT,
            wraplength=660, justify='left',
        ).pack(padx=15)

        # ── Step 1 — Today's tickets ─────────────────────────────────────────
        tk.Label(
            dialog, text="Step 1 — Select a ticket from today",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(12, 4))

        ticket_outer = tk.Frame(dialog, bg=theme.WINDOW_BG)
        ticket_outer.pack(fill='x', padx=15, pady=(0, 8))

        cols = ("Time", "Ticket", "Title", "Resolved")
        self._ticket_tree = ttk.Treeview(
            ticket_outer, columns=cols, show='headings', height=6,
            selectmode='browse',
        )
        for col in cols:
            width = 80 if col in ("Time", "Resolved") else 200
            self._ticket_tree.heading(col, text=col)
            self._ticket_tree.column(col, width=width, anchor='w')

        vsb = ttk.Scrollbar(ticket_outer, orient='vertical',
                            command=self._ticket_tree.yview)
        self._ticket_tree.configure(yscrollcommand=vsb.set)
        self._ticket_tree.pack(side='left', fill='x', expand=True)
        vsb.pack(side='right', fill='y')

        self._ticket_tree.bind('<<TreeviewSelect>>', self._on_ticket_selected)

        self._status_var = tk.StringVar(value="Loading today's tasks…")
        self._status_label = tk.Label(
            dialog, textvariable=self._status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            anchor='w',
        )
        self._status_label.pack(fill='x', padx=15, pady=(0, 4))

        # ── Step 2 — Choose API service ──────────────────────────────────────
        tk.Label(
            dialog, text="Step 2 — Choose external system",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

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
            svc_combo.bind('<<ComboboxSelected>>', self._on_service_changed)
        else:
            tk.Label(
                svc_frame,
                text="⚠  No external APIs configured. Go to Settings → External API Settings.",
                font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.ACCENT,
            ).pack()

        # ── Step 3 — Verify ticket ───────────────────────────────────────────
        tk.Label(
            dialog, text="Step 3 — Verify ticket in external system",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        verify_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
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
            dialog, textvariable=self._ticket_detail_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
            wraplength=660, justify='left', anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 4))

        # ── Step 4 — AI preview ──────────────────────────────────────────────
        tk.Label(
            dialog, text="Step 4 — Review AI-generated update",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=15, pady=(8, 4))

        preview_outer = tk.Frame(dialog, bg=theme.WINDOW_BG)
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
            dialog, height=6, wrap=tk.WORD,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat', padx=6, pady=4,
        )
        self._preview_text_widget.pack(fill='x', padx=15, pady=(0, 8))

        # ── Step 5 — Send ────────────────────────────────────────────────────
        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
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
            command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, cursor='hand2',
        ).pack(side='left', padx=5)

        # Load tasks in background
        threading.Thread(target=self._load_tasks, daemon=True).start()

    # ------------------------------------------------------------------
    # Task loading
    # ------------------------------------------------------------------

    def _load_tasks(self):
        """Fetch today's tasks from the repository (background thread)."""
        import datetime
        try:
            today = datetime.date.today()
            tasks = self.data_repository.get_tasks_by_date(today)
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

        self._dialog.after(0, self._populate_ticket_tree, usable)

    def _populate_ticket_tree(self, tasks):
        """Populate the treeview with tasks (main thread)."""
        self._ticket_tree.delete(*self._ticket_tree.get_children())
        self._tasks_cache = tasks

        if not tasks:
            self._status_var.set("No tickets logged today yet.")
            return

        for task in tasks:
            start = task.get("Start Time", "")
            time_str = start[11:16] if len(start) >= 16 else start
            self._ticket_tree.insert(
                "", "end",
                values=(
                    time_str,
                    task.get("Ticket", ""),
                    task.get("Title", "")[:60],
                    task.get("Resolved", "No"),
                ),
                tags=(str(tasks.index(task)),),
            )

        self._status_var.set(
            f"{len(tasks)} ticket(s) logged today. Select one to continue."
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_ticket_selected(self, _event=None):
        """Handle ticket selection in the treeview."""
        sel = self._ticket_tree.selection()
        if not sel:
            return

        item = self._ticket_tree.item(sel[0])
        tag = item["tags"][0] if item["tags"] else None
        if tag is not None:
            self._selected_task = self._tasks_cache[int(tag)]

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
        if self._selected_task and self._services:
            self._btn_verify.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Step 3 — Verify ticket
    # ------------------------------------------------------------------

    def _verify_ticket(self):
        if not self._selected_task:
            return

        ticket_id = self._selected_task.get("Ticket", "").strip()
        # Use only the first ticket if comma-separated
        ticket_id = ticket_id.split(",")[0].strip()
        if not ticket_id:
            messagebox.showwarning(
                "No Ticket", "The selected task has no ticket ID.", parent=self._dialog
            )
            return

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
        if not self._selected_task or not self._verified_ticket_info:
            return

        self._btn_preview.config(state=tk.DISABLED)
        self._btn_send.config(state=tk.DISABLED)
        self._preview_text_widget.delete("1.0", tk.END)
        self._preview_text_widget.insert(
            tk.END, "✨ Generating AI preview… please wait."
        )

        task = self._selected_task
        ticket_info = self._verified_ticket_info

        def _do_generate():
            comment = self._call_llm_for_comment(task, ticket_info)
            self._dialog.after(0, self._apply_preview, comment)

        threading.Thread(target=_do_generate, daemon=True).start()

    def _call_llm_for_comment(self, task, ticket_info) -> str:
        """Ask the configured LLM to draft a comment for the external ticket."""
        title = task.get("Title", "")
        duration = task.get("Duration (Min)", "")
        ai_summary = task.get("AI Summary", "").strip()
        ticket_id = ticket_info.get("id", "")
        ticket_summary = ticket_info.get("summary", "")

        prompt = (
            f"I worked on ticket {ticket_id} titled '{ticket_summary}' for {duration} minutes.\n"
            f"My work notes: {title}\n"
        )
        if ai_summary:
            prompt += f"AI summary of the work: {ai_summary}\n"
        prompt += (
            "Write a concise, professional progress update comment (2-4 sentences) "
            "suitable for posting to a ticket tracking system. "
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
