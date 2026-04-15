"""
Knowledge Graph Page for SheepCat Work Tracker.

Provides a UI for categorising tasks with tags, adding timing notes,
importing documents, and linking documents to tasks.
"""
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

import requests

import theme
from graph_repository import GraphRepository, GRAPH_DB_FILENAME
from ollama_client import strip_thinking_tokens


class KnowledgeGraphPage(tk.Frame):
    """Page for managing task tags, timing notes, documents, and their relationships."""

    def __init__(self, parent, graph_repository: GraphRepository, data_repository,
                 settings_manager=None, on_settings_saved=None):
        """
        Initialise the Knowledge Graph page.

        Args:
            parent:            Parent tkinter widget.
            graph_repository:  :class:`GraphRepository` instance.
            data_repository:   Data repository (CSVDataRepository) for reading tasks.
            settings_manager:  :class:`SettingsManager` instance used by the
                               auto-tag feature and the DB-path bar.
            on_settings_saved: Optional callback invoked after the DB directory
                               is changed from within this page, so the parent
                               application can resync its own references.
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.graph_repo = graph_repository
        self.data_repo = data_repository
        self.settings_manager = settings_manager
        self._on_settings_saved = on_settings_saved
        self._all_tasks_data: list = []
        # Maps unique Treeview iid -> graph task_id (Start Time string).
        # Required because Start Time strings contain spaces that are
        # special characters in Tcl/Tk and cannot be used directly as iids.
        self._iid_to_task_id: dict = {}
        self._create_widgets()
        self._load_data()

    # ── Widget construction ────────────────────────────────────────────────────

    def _create_widgets(self):
        """Build all UI widgets."""
        tk.Label(
            self, text="Knowledge Graph",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(anchor='w', padx=10, pady=(10, 2))

        tk.Label(
            self,
            text=(
                "Categorise tasks with tags, add timing notes, "
                "import documents and link them to tasks."
            ),
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(anchor='w', padx=10, pady=(0, 4))

        # ── Graph DB path bar ─────────────────────────────────────────────────
        db_bar = tk.Frame(self, bg=theme.SURFACE_BG, bd=0)
        db_bar.pack(fill='x', padx=10, pady=(0, 6))

        tk.Label(
            db_bar, text="Graph DB:",
            font=theme.FONT_SMALL, bg=theme.SURFACE_BG, fg=theme.MUTED,
        ).pack(side='left', padx=(8, 4), pady=4)

        self._db_path_var = tk.StringVar()
        db_path_entry = tk.Entry(
            db_bar, textvariable=self._db_path_var,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            relief='flat', font=theme.FONT_SMALL, width=48,
            state='readonly',
        )
        db_path_entry.pack(side='left', padx=(0, 6), pady=4)

        theme.RoundedButton(
            db_bar, text="Browse…",
            command=self._browse_db_directory,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left', padx=(0, 4), pady=4)

        theme.RoundedButton(
            db_bar, text="Apply",
            command=self._apply_db_path,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=8, cursor='hand2',
        ).pack(side='left', pady=4)

        self._db_path_var.set(self._current_db_path())

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=4)

        self._create_tags_tab()
        self._create_documents_tab()

    # ── Tags tab ──────────────────────────────────────────────────────────────

    # ── Graph DB path helpers ──────────────────────────────────────────────────

    def _current_db_path(self) -> str:
        """Return the effective graph DB file path from settings."""
        if self.settings_manager is not None:
            return self.settings_manager.get_graph_db_path()
        return self.graph_repo.db_path if self.graph_repo else ""

    def _browse_db_directory(self):
        """Open a folder-chooser so the user can pick a new graph DB directory."""
        initial = os.path.dirname(self._db_path_var.get()) or "."
        directory = filedialog.askdirectory(
            title="Select Graph DB Directory",
            initialdir=initial,
            parent=self,
        )
        if directory:
            preview = os.path.join(directory, GRAPH_DB_FILENAME)
            self._db_path_var.set(preview)
            # Store the chosen directory for Apply
            self._pending_db_directory = directory

    def _apply_db_path(self):
        """Apply the selected graph DB directory and reinitialise the repository.

        Settings are saved first, then:
        * When a parent callback is available (``_on_settings_saved``), it is
          invoked to handle the actual ``GraphRepository`` reinitialisation —
          this avoids creating two repository instances.
        * Without a callback the page reinitialises the repository itself.
        """
        pending = getattr(self, '_pending_db_directory', None)
        if not pending:
            # Nothing was browsed — no change
            messagebox.showinfo(
                "No Change",
                "Use Browse… to choose a directory first.",
                parent=self,
            )
            return

        if self.settings_manager is None:
            messagebox.showerror(
                "Not Available",
                "Settings manager is not connected. Please restart the app.",
                parent=self,
            )
            return

        new_path = os.path.join(pending, GRAPH_DB_FILENAME)
        old_path = self.graph_repo.db_path if self.graph_repo else ""

        if new_path == old_path:
            self._pending_db_directory = None
            messagebox.showinfo(
                "No Change",
                "The selected directory is the same as the current one.",
                parent=self,
            )
            return

        # Persist the new directory
        self.settings_manager.set("graph_db_directory", pending)
        self.settings_manager.save()
        self._pending_db_directory = None

        if self._on_settings_saved:
            # Parent handles close/create/reassign of graph_repository and
            # updates self.graph_repo via _on_settings_changed.
            self._on_settings_saved()
        else:
            # Standalone mode — handle reinit locally
            if self.graph_repo:
                self.graph_repo.close()
            self.graph_repo = GraphRepository(new_path)
            self.graph_repo.initialize()

        # Refresh the DB path bar and reload data unconditionally
        self._db_path_var.set(self._current_db_path())
        self._load_data()

        messagebox.showinfo(
            "Graph DB Updated",
            f"Graph database location updated to:\n{new_path}",
            parent=self,
        )

    def _create_tags_tab(self):
        """Create the Task Tags tab."""
        tab = tk.Frame(self.notebook, bg=theme.WINDOW_BG)
        self.notebook.add(tab, text="Task Tags")

        paned = tk.PanedWindow(tab, orient='horizontal', bg=theme.WINDOW_BG, sashwidth=4)
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # ── Left panel: tag list ──────────────────────────────────────────────
        left = tk.Frame(paned, bg=theme.WINDOW_BG)
        paned.add(left, minsize=180)

        tk.Label(
            left, text="Tags",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(5, 2))

        self.tags_listbox = tk.Listbox(
            left, bg=theme.INPUT_BG, fg=theme.TEXT, selectmode='single',
            font=theme.FONT_BODY, relief='flat', height=18,
        )
        self.tags_listbox.pack(fill='both', expand=True, padx=5, pady=3)
        self.tags_listbox.bind('<<ListboxSelect>>', self._on_tag_selected)

        # New-tag input row
        new_tag_frame = tk.Frame(left, bg=theme.WINDOW_BG)
        new_tag_frame.pack(fill='x', padx=5, pady=(2, 2))
        self.new_tag_var = tk.StringVar()
        tk.Entry(
            new_tag_frame, textvariable=self.new_tag_var, width=16,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left', padx=(0, 4))
        theme.RoundedButton(
            new_tag_frame, text="Add", command=self._add_tag,
            bg=theme.PRIMARY, fg=theme.TEXT, font=theme.FONT_SMALL, width=6, cursor='hand2',
        ).pack(side='left')

        tag_btn_frame = tk.Frame(left, bg=theme.WINDOW_BG)
        tag_btn_frame.pack(fill='x', padx=5, pady=(0, 5))
        theme.RoundedButton(
            tag_btn_frame, text="Delete Tag", command=self._delete_tag,
            bg=theme.RED, fg=theme.TEXT, font=theme.FONT_SMALL, width=12, cursor='hand2',
        ).pack(side='left')

        # Auto-tag turbo button
        auto_tag_frame = tk.Frame(left, bg=theme.WINDOW_BG)
        auto_tag_frame.pack(fill='x', padx=5, pady=(4, 8))
        theme.RoundedButton(
            auto_tag_frame, text="⚡ Auto-Tag All",
            command=self._auto_tag_all,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_SMALL, width=16, cursor='hand2',
        ).pack(side='left')

        # ── Right panel: tasks for tag + all tasks ────────────────────────────
        right = tk.Frame(paned, bg=theme.WINDOW_BG)
        paned.add(right, minsize=300)

        tk.Label(
            right, text="Tasks with selected tag",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(5, 2))

        tagged_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        tagged_frame.pack(fill='x', padx=5, pady=3)

        self.tagged_tasks_tree = ttk.Treeview(
            tagged_frame,
            columns=('start_time', 'title', 'tags', 'notes'),
            show='headings', height=8,
        )
        self.tagged_tasks_tree.heading('start_time', text='Start Time')
        self.tagged_tasks_tree.heading('title', text='Title')
        self.tagged_tasks_tree.heading('tags', text='Tags')
        self.tagged_tasks_tree.heading('notes', text='Notes')
        self.tagged_tasks_tree.column('start_time', width=140)
        self.tagged_tasks_tree.column('title', width=230)
        self.tagged_tasks_tree.column('tags', width=140)
        self.tagged_tasks_tree.column('notes', width=80)

        tagged_scroll = ttk.Scrollbar(tagged_frame, orient='vertical', command=self.tagged_tasks_tree.yview)
        self.tagged_tasks_tree.configure(yscrollcommand=tagged_scroll.set)
        self.tagged_tasks_tree.pack(side='left', fill='both', expand=True)
        tagged_scroll.pack(side='right', fill='y')

        # All tasks section
        tk.Label(
            right, text="All Tasks  (select to tag / add note)",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(8, 2))

        all_tasks_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        all_tasks_frame.pack(fill='both', expand=True, padx=5, pady=3)

        self.all_tasks_tree = ttk.Treeview(
            all_tasks_frame,
            columns=('start_time', 'title', 'tags'),
            show='headings', height=10,
        )
        self.all_tasks_tree.heading('start_time', text='Start Time')
        self.all_tasks_tree.heading('title', text='Title')
        self.all_tasks_tree.heading('tags', text='Current Tags')
        self.all_tasks_tree.column('start_time', width=140)
        self.all_tasks_tree.column('title', width=280)
        self.all_tasks_tree.column('tags', width=180)

        all_scroll = ttk.Scrollbar(all_tasks_frame, orient='vertical', command=self.all_tasks_tree.yview)
        self.all_tasks_tree.configure(yscrollcommand=all_scroll.set)
        self.all_tasks_tree.pack(side='left', fill='both', expand=True)
        all_scroll.pack(side='right', fill='y')

        # Action buttons
        action_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        action_frame.pack(fill='x', padx=5, pady=4)
        theme.RoundedButton(
            action_frame, text="Apply Tag to Task",
            command=self._tag_selected_task,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_SMALL, width=18, cursor='hand2',
        ).pack(side='left', padx=(0, 4))
        theme.RoundedButton(
            action_frame, text="Remove Tag",
            command=self._untag_selected_task,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=12, cursor='hand2',
        ).pack(side='left', padx=(0, 4))
        theme.RoundedButton(
            action_frame, text="Add Note",
            command=self._add_timing_note,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left')

    # ── Documents tab ─────────────────────────────────────────────────────────

    def _create_documents_tab(self):
        """Create the Documents tab."""
        tab = tk.Frame(self.notebook, bg=theme.WINDOW_BG)
        self.notebook.add(tab, text="Documents")

        paned = tk.PanedWindow(tab, orient='horizontal', bg=theme.WINDOW_BG, sashwidth=4)
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # ── Left: document list ───────────────────────────────────────────────
        left = tk.Frame(paned, bg=theme.WINDOW_BG)
        paned.add(left, minsize=220)

        tk.Label(
            left, text="Documents",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(5, 2))

        docs_frame = tk.Frame(left, bg=theme.WINDOW_BG)
        docs_frame.pack(fill='both', expand=True, padx=5, pady=3)

        self.docs_tree = ttk.Treeview(
            docs_frame, columns=('name', 'added'), show='headings', height=20,
        )
        self.docs_tree.heading('name', text='Document')
        self.docs_tree.heading('added', text='Added')
        self.docs_tree.column('name', width=150)
        self.docs_tree.column('added', width=90)

        docs_scroll = ttk.Scrollbar(docs_frame, orient='vertical', command=self.docs_tree.yview)
        self.docs_tree.configure(yscrollcommand=docs_scroll.set)
        self.docs_tree.pack(side='left', fill='both', expand=True)
        docs_scroll.pack(side='right', fill='y')

        self.docs_tree.bind('<<TreeviewSelect>>', self._on_doc_selected)

        doc_btn_frame = tk.Frame(left, bg=theme.WINDOW_BG)
        doc_btn_frame.pack(fill='x', padx=5, pady=3)
        theme.RoundedButton(
            doc_btn_frame, text="Import Document",
            command=self._import_document,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=16, cursor='hand2',
        ).pack(side='left', padx=(0, 4))
        theme.RoundedButton(
            doc_btn_frame, text="Delete",
            command=self._delete_document,
            bg=theme.RED, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=8, cursor='hand2',
        ).pack(side='left')

        # ── Right: linked tasks + all tasks ───────────────────────────────────
        right = tk.Frame(paned, bg=theme.WINDOW_BG)
        paned.add(right, minsize=280)

        tk.Label(
            right, text="Tasks linked to this document",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(5, 2))

        linked_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        linked_frame.pack(fill='x', padx=5, pady=3)

        self.doc_tasks_tree = ttk.Treeview(
            linked_frame, columns=('task_id', 'note'), show='headings', height=8,
        )
        self.doc_tasks_tree.heading('task_id', text='Task Start Time')
        self.doc_tasks_tree.heading('note', text='Relationship Note')
        self.doc_tasks_tree.column('task_id', width=160)
        self.doc_tasks_tree.column('note', width=260)

        linked_scroll = ttk.Scrollbar(linked_frame, orient='vertical', command=self.doc_tasks_tree.yview)
        self.doc_tasks_tree.configure(yscrollcommand=linked_scroll.set)
        self.doc_tasks_tree.pack(side='left', fill='both', expand=True)
        linked_scroll.pack(side='right', fill='y')

        # All tasks for linking
        tk.Label(
            right, text="All Tasks  (select to link / unlink)",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        ).pack(anchor='w', padx=5, pady=(8, 2))

        doc_all_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        doc_all_frame.pack(fill='both', expand=True, padx=5, pady=3)

        self.doc_all_tasks_tree = ttk.Treeview(
            doc_all_frame,
            columns=('start_time', 'title'),
            show='headings', height=10,
        )
        self.doc_all_tasks_tree.heading('start_time', text='Start Time')
        self.doc_all_tasks_tree.heading('title', text='Title')
        self.doc_all_tasks_tree.column('start_time', width=140)
        self.doc_all_tasks_tree.column('title', width=300)

        doc_all_scroll = ttk.Scrollbar(doc_all_frame, orient='vertical', command=self.doc_all_tasks_tree.yview)
        self.doc_all_tasks_tree.configure(yscrollcommand=doc_all_scroll.set)
        self.doc_all_tasks_tree.pack(side='left', fill='both', expand=True)
        doc_all_scroll.pack(side='right', fill='y')

        link_frame = tk.Frame(right, bg=theme.WINDOW_BG)
        link_frame.pack(fill='x', padx=5, pady=4)
        theme.RoundedButton(
            link_frame, text="Link to Task",
            command=self._link_doc_to_task,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_SMALL, width=14, cursor='hand2',
        ).pack(side='left', padx=(0, 4))
        theme.RoundedButton(
            link_frame, text="Unlink",
            command=self._unlink_doc_from_task,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left')

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data(self):
        """Reload all data from both repositories."""
        self._load_tags()
        self._load_all_tasks()
        self._load_documents()

    def _load_tags(self):
        """Reload the tags listbox."""
        self.tags_listbox.delete(0, tk.END)
        for tag in self.graph_repo.get_all_tags():
            self.tags_listbox.insert(tk.END, tag['name'])

    def _load_all_tasks(self):
        """Load all work-log tasks into both task trees.

        A unique, Tcl-safe iid is built for each row from the task date,
        sanitised title, and row index so that:
        * iids never contain spaces (Tcl argument separator),
        * every CSV row gets its own entry even when two tasks share the
          same Start Time (e.g. multi-ticket entries).

        The mapping from iid → graph task_id (Start Time) is stored in
        ``self._iid_to_task_id`` for use by the selection handlers.
        """
        for tree in (self.all_tasks_tree, self.doc_all_tasks_tree):
            for item in tree.get_children():
                tree.delete(item)

        self._iid_to_task_id = {}
        self._all_tasks_data = self.data_repo.get_all_tasks()

        for idx, task in enumerate(self._all_tasks_data):
            task_id = task.get('Start Time', '')   # graph repo key
            title = task.get('Title', '')

            # Build a unique Tcl-safe iid: date part + sanitised title + index
            # e.g.  "2024-01-15T100000_Fixed_login_bug_42"
            date_part = task_id.replace(' ', 'T').replace(':', '')
            title_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:30])
            unique_iid = f"{date_part}_{title_safe}_{idx}"

            self._iid_to_task_id[unique_iid] = task_id

            tags = ', '.join(self.graph_repo.get_task_tags(task_id))
            self.all_tasks_tree.insert(
                '', 'end', iid=unique_iid,
                values=(task_id, title, tags),
            )
            self.doc_all_tasks_tree.insert(
                '', 'end', iid=unique_iid,
                values=(task_id, title),
            )

    def _load_documents(self):
        """Reload the documents tree."""
        for item in self.docs_tree.get_children():
            self.docs_tree.delete(item)
        for doc in self.graph_repo.get_all_documents():
            self.docs_tree.insert(
                '', 'end', iid=str(doc['id']),
                values=(doc['name'], doc['added_at'][:10]),
            )

    # ── Auto-tag ──────────────────────────────────────────────────────────────

    def _auto_tag_all(self):
        """Auto-tag every task using the configured AI model.

        Opens a confirmation dialog letting the user choose whether to skip
        already-tagged tasks or re-tag everything.  The AI call runs in a
        background thread so the UI stays responsive; progress is streamed into
        a scrollable log window.
        """
        if not self._all_tasks_data:
            messagebox.showinfo(
                "No Tasks", "There are no tasks to tag yet.", parent=self
            )
            return

        if self.settings_manager is None:
            messagebox.showerror(
                "Not Available",
                "Settings manager is not connected. Please restart the app.",
                parent=self,
            )
            return

        ai_url = self.settings_manager.get("ai_api_url", "")
        ai_model = (
            self.settings_manager.get("doc_eval_model", "").strip()
            or self.settings_manager.get("ai_model", "")
        )
        # Use the same configurable timeout as all other LLM calls.
        # Thinking models (Qwen3, DeepSeek-R1, etc.) can take several minutes
        # before they finish their reasoning chain — the default of 1000 s
        # gives them plenty of room.
        ai_timeout = int(self.settings_manager.get("llm_request_timeout", 1000))
        if not ai_url or not ai_model:
            messagebox.showerror(
                "AI Not Configured",
                "Please configure an AI model in Settings before using Auto-Tag.",
                parent=self,
            )
            return

        # Confirmation dialog — choose scope
        dialog = tk.Toplevel(self)
        dialog.title("Auto-Tag All Tasks")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)

        tk.Label(
            dialog,
            text="Auto-Tag All Tasks",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=(16, 4))

        tk.Label(
            dialog,
            text=(
                "The AI will suggest categories for each task\n"
                "and apply them automatically."
            ),
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
            justify='center',
        ).pack(pady=(0, 10))

        skip_tagged_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            dialog,
            text="Skip tasks that already have tags",
            variable=skip_tagged_var,
            bg=theme.WINDOW_BG, fg=theme.TEXT,
            activebackground=theme.WINDOW_BG, activeforeground=theme.TEXT,
            selectcolor=theme.INPUT_BG, font=theme.FONT_SMALL,
        ).pack(pady=(0, 12))

        confirmed = [False]

        def _confirm():
            confirmed[0] = True
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_row.pack()
        theme.RoundedButton(
            btn_row, text="Start", command=_confirm,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left', padx=6)
        theme.RoundedButton(
            btn_row, text="Cancel", command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
        ).pack(side='left', padx=6)

        self.wait_window(dialog)

        if not confirmed[0]:
            return

        skip_tagged = skip_tagged_var.get()
        self._run_auto_tag_with_progress(ai_url, ai_model, ai_timeout, skip_tagged)

    def _run_auto_tag_with_progress(self, ai_url: str, ai_model: str, ai_timeout: int, skip_tagged: bool):
        """Open a live progress window and start the background tagging thread."""
        progress_win = tk.Toplevel(self)
        progress_win.title("Auto-Tagging...")
        progress_win.geometry("520x400")
        progress_win.transient(self)
        progress_win.configure(bg=theme.WINDOW_BG)
        # Not grab_set so user can still navigate the app

        tk.Label(
            progress_win, text="Auto-Tagging Tasks",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(anchor='w', padx=14, pady=(12, 4))

        status_var = tk.StringVar(value="Starting...")
        tk.Label(
            progress_win, textvariable=status_var,
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
            anchor='w',
        ).pack(fill='x', padx=14, pady=(0, 4))

        log_frame = tk.Frame(progress_win, bg=theme.WINDOW_BG)
        log_frame.pack(fill='both', expand=True, padx=10, pady=4)

        log_text = tk.Text(
            log_frame, height=16, wrap='word', state='disabled',
            bg=theme.INPUT_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, relief='flat',
            insertbackground=theme.TEXT,
        )
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=log_text.yview)
        log_text.configure(yscrollcommand=log_scroll.set)
        log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')

        close_btn = theme.RoundedButton(
            progress_win, text="Close",
            command=progress_win.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_SMALL, width=10, cursor='hand2',
            state=tk.DISABLED,
        )
        close_btn.pack(pady=(4, 10))

        def _log(msg: str):
            """Append a line to the progress log (must be called from UI thread)."""
            log_text.configure(state='normal')
            log_text.insert(tk.END, msg + "\n")
            log_text.see(tk.END)
            log_text.configure(state='disabled')

        def _worker():
            tasks = list(self._all_tasks_data)
            total = len(tasks)
            tagged_count = 0
            skipped_count = 0
            error_count = 0

            for idx, task in enumerate(tasks, start=1):
                task_id = task.get('Start Time', '')
                title = task.get('Title', '').strip()

                self.after(0, status_var.set, f"Processing {idx}/{total}: {title[:40]}")

                if not title:
                    self.after(0, _log, f"  [{idx}/{total}] Skipped (no title)")
                    skipped_count += 1
                    continue

                if skip_tagged and self.graph_repo.get_task_tags(task_id):
                    self.after(0, _log, f"  [{idx}/{total}] Already tagged — skipped: {title[:50]}")
                    skipped_count += 1
                    continue

                suggested = self._suggest_tags_via_ai(ai_url, ai_model, title, ai_timeout)

                if suggested is None:
                    self.after(0, _log, f"  [{idx}/{total}] ✗ AI error for: {title[:50]}")
                    error_count += 1
                    continue

                if not suggested:
                    self.after(0, _log, f"  [{idx}/{total}] ~ No tags suggested for: {title[:50]}")
                    skipped_count += 1
                    continue

                for tag in suggested:
                    self.graph_repo.tag_task(task_id, tag)

                self.after(
                    0, _log,
                    f"  [{idx}/{total}] ✓ {title[:40]} → {', '.join(suggested)}",
                )
                tagged_count += 1

            # Done — update UI from main thread
            summary = (
                f"\nDone. Tagged: {tagged_count}  |  "
                f"Skipped: {skipped_count}  |  Errors: {error_count}"
            )
            self.after(0, _log, summary)
            self.after(0, status_var.set, "Complete ✓")
            self.after(0, lambda: close_btn.configure(state=tk.NORMAL))
            # Refresh the page data so new tags are visible
            self.after(0, self._load_data)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    @staticmethod
    def _suggest_tags_via_ai(ai_url: str, ai_model: str, title: str, request_timeout: int = 1000):
        """Ask the AI to suggest category tags for a task title.

        Supports thinking/reasoning models (Qwen3, DeepSeek-R1, etc.) that
        emit ``<think>…</think>`` blocks before their actual answer — those
        blocks are stripped automatically before the tag list is parsed.

        Args:
            ai_url:          Full Ollama API generate URL.
            ai_model:        Model name to use.
            title:           Task title string.
            request_timeout: HTTP request timeout in seconds (default 1000 to
                             give thinking models enough time to finish their
                             reasoning chain before returning a response).

        Returns:
            A list of lowercase tag strings, an empty list when no tags are
            suggested, or ``None`` on connection/parse failure.
        """
        prompt = (
            "You are a work-task categorisation assistant.\n"
            "Given the task title below, suggest 1 to 3 concise category tags.\n\n"
            "Rules:\n"
            "- Each tag must be a single word or short hyphenated phrase "
            "(e.g. bug-fix, meeting, deployment, review, admin, testing)\n"
            "- Return ONLY a comma-separated list of tag names — no explanation, "
            "no bullet points, nothing else\n"
            "- Use lowercase\n\n"
            f"Task title: {title}\n"
            "Tags:"
        )
        payload = {"model": ai_model, "prompt": prompt, "stream": False}
        try:
            response = requests.post(ai_url, json=payload, timeout=request_timeout)
            if response.status_code != 200:
                return None
            raw = strip_thinking_tokens(response.json().get("response", ""))
            # Parse comma-separated tags; sanitise to word-chars + hyphen,
            # replace runs of whitespace with hyphens, drop empties / overly long.
            tags = []
            for part in raw.split(","):
                tag = re.sub(r'\s+', '-', re.sub(r'[^a-zA-Z0-9 _-]', '', part).strip()).lower()
                if tag and len(tag) <= 40:
                    tags.append(tag)
            return tags[:3]  # cap at 3
        except Exception as exc:
            print(f"Auto-tag AI request failed: {exc}")
            return None

    # ── Tag events ────────────────────────────────────────────────────────────

    def _on_tag_selected(self, _event=None):
        """Populate the tagged-tasks tree when a tag is selected."""
        selection = self.tags_listbox.curselection()
        if not selection:
            return
        tag_name = self.tags_listbox.get(selection[0])
        task_ids = self.graph_repo.get_tasks_by_tag(tag_name)

        for item in self.tagged_tasks_tree.get_children():
            self.tagged_tasks_tree.delete(item)

        task_map = {t.get('Start Time', ''): t for t in self._all_tasks_data}
        for task_id in task_ids:
            task = task_map.get(task_id, {})
            title = task.get('Title', task_id)
            tags = ', '.join(self.graph_repo.get_task_tags(task_id))
            notes = self.graph_repo.get_timing_notes(task_id)
            note_str = f"{len(notes)} note(s)" if notes else ""
            self.tagged_tasks_tree.insert(
                '', 'end',
                values=(task_id, title, tags, note_str),
            )

    def _add_tag(self):
        """Add a new tag from the inline entry field."""
        name = self.new_tag_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a tag name.", parent=self)
            return
        self.graph_repo.add_tag(name)
        self.new_tag_var.set("")
        self._load_tags()

    def _delete_tag(self):
        """Delete the currently selected tag after confirmation."""
        selection = self.tags_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a tag to delete.", parent=self)
            return
        tag_name = self.tags_listbox.get(selection[0])
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete tag '{tag_name}' and remove it from all tasks?",
            parent=self,
        ):
            self.graph_repo.delete_tag(tag_name)
            self._load_tags()
            for item in self.tagged_tasks_tree.get_children():
                self.tagged_tasks_tree.delete(item)

    def _tag_selected_task(self):
        """Apply the selected tag to the selected task."""
        tag_sel = self.tags_listbox.curselection()
        task_sel = self.all_tasks_tree.selection()
        if not tag_sel or not task_sel:
            messagebox.showinfo(
                "Selection Required",
                "Please select a tag on the left and a task in the lower list.",
                parent=self,
            )
            return
        tag_name = self.tags_listbox.get(tag_sel[0])
        task_id = self._iid_to_task_id.get(task_sel[0], task_sel[0])
        if self.graph_repo.tag_task(task_id, tag_name):
            self._refresh_task_tags_column()
            self._on_tag_selected()

    def _untag_selected_task(self):
        """Remove the selected tag from the task highlighted in the tagged-tasks tree."""
        tag_sel = self.tags_listbox.curselection()
        task_sel = self.tagged_tasks_tree.selection()
        if not tag_sel or not task_sel:
            messagebox.showinfo(
                "Selection Required",
                "Please select a tag and a task in the 'Tasks with selected tag' list.",
                parent=self,
            )
            return
        tag_name = self.tags_listbox.get(tag_sel[0])
        task_id = str(self.tagged_tasks_tree.item(task_sel[0])['values'][0])
        self.graph_repo.untag_task(task_id, tag_name)
        self._refresh_task_tags_column()
        self._on_tag_selected()

    def _refresh_task_tags_column(self):
        """Refresh the tags column in the all-tasks tree."""
        for item in self.all_tasks_tree.get_children():
            task_id = self._iid_to_task_id.get(item, item)
            tags = ', '.join(self.graph_repo.get_task_tags(task_id))
            vals = list(self.all_tasks_tree.item(item)['values'])
            if len(vals) >= 3:
                vals[2] = tags
                self.all_tasks_tree.item(item, values=vals)

    def _add_timing_note(self):
        """Open a dialog to add a timing/context note to the selected task."""
        task_sel = self.all_tasks_tree.selection()
        if not task_sel:
            messagebox.showinfo(
                "No Selection", "Please select a task to add a note to.", parent=self
            )
            return
        task_id = self._iid_to_task_id.get(task_sel[0], task_sel[0])
        self._show_add_note_dialog(task_id)

    def _show_add_note_dialog(self, task_id: str):
        """Display a modal dialog for entering a timing note."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Timing Note")
        dialog.geometry("420x220")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)

        tk.Label(
            dialog,
            text=f"Note for: {task_id[:50]}",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT, anchor='w',
        ).pack(fill='x', padx=15, pady=(15, 5))

        note_text = tk.Text(
            dialog, height=5, wrap='word',
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
            font=theme.FONT_BODY,
        )
        note_text.pack(fill='x', padx=15, pady=5)

        def _on_save():
            note = note_text.get("1.0", tk.END).strip()
            if not note:
                messagebox.showwarning("Empty Note", "Please enter a note.", parent=dialog)
                return
            self.graph_repo.add_timing_note(task_id, note)
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_frame.pack(pady=8)
        theme.RoundedButton(
            btn_frame, text="Save", command=_on_save,
            bg=theme.GREEN, fg=theme.WINDOW_BG, font=theme.FONT_BODY, width=8, cursor='hand2',
        ).pack(side='left', padx=5)
        theme.RoundedButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT, font=theme.FONT_BODY, width=8, cursor='hand2',
        ).pack(side='left', padx=5)

        note_text.focus_set()
        self.wait_window(dialog)

    # ── Document events ────────────────────────────────────────────────────────

    def _on_doc_selected(self, _event=None):
        """Populate the linked-tasks tree when a document is selected."""
        selection = self.docs_tree.selection()
        if not selection:
            return
        doc_id = int(selection[0])
        linked = self.graph_repo.get_document_tasks(doc_id)
        for item in self.doc_tasks_tree.get_children():
            self.doc_tasks_tree.delete(item)
        for rel in linked:
            self.doc_tasks_tree.insert(
                '', 'end',
                values=(rel['task_id'], rel.get('note', '')),
            )

    def _import_document(self):
        """Open a file picker and import a document into the graph store."""
        file_path = filedialog.askopenfilename(
            title="Select Document to Import",
            filetypes=[
                ("Text files",     "*.txt"),
                ("Markdown files", "*.md"),
                ("CSV files",      "*.csv"),
                ("Log files",      "*.log"),
                ("All files",      "*.*"),
            ],
            parent=self,
        )
        if not file_path:
            return

        name = os.path.basename(file_path)
        content = None

        # Extract text content for plain-text formats (cap at 100 KB)
        if file_path.lower().endswith(('.txt', '.md', '.csv', '.log')):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read(102400)
            except Exception:
                pass

        doc_id = self.graph_repo.add_document(name, file_path, content)
        if doc_id is None:
            messagebox.showerror("Error", "Failed to import document.", parent=self)
            return
        self._load_documents()

    def _delete_document(self):
        """Delete the selected document and all its task links after confirmation."""
        selection = self.docs_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a document to delete.", parent=self)
            return
        doc_id = int(selection[0])
        if messagebox.askyesno(
            "Confirm Delete",
            "Delete this document and remove all its task links?",
            parent=self,
        ):
            self.graph_repo.delete_document(doc_id)
            self._load_documents()
            for item in self.doc_tasks_tree.get_children():
                self.doc_tasks_tree.delete(item)

    def _link_doc_to_task(self):
        """Link the selected document to the selected task."""
        doc_sel = self.docs_tree.selection()
        task_sel = self.doc_all_tasks_tree.selection()
        if not doc_sel or not task_sel:
            messagebox.showinfo(
                "Selection Required",
                "Please select a document on the left and a task in the lower list.",
                parent=self,
            )
            return
        doc_id = int(doc_sel[0])
        task_id = self._iid_to_task_id.get(task_sel[0], task_sel[0])
        self.graph_repo.link_document_to_task(task_id, doc_id)
        self._on_doc_selected()

    def _unlink_doc_from_task(self):
        """Remove the link between the selected document and the highlighted linked task."""
        doc_sel = self.docs_tree.selection()
        task_sel = self.doc_tasks_tree.selection()
        if not doc_sel or not task_sel:
            messagebox.showinfo(
                "Selection Required",
                "Please select a document and a linked task to unlink.",
                parent=self,
            )
            return
        doc_id = int(doc_sel[0])
        task_id = str(self.doc_tasks_tree.item(task_sel[0])['values'][0])
        self.graph_repo.unlink_document_from_task(task_id, doc_id)
        self._on_doc_selected()

    # ── Public API ─────────────────────────────────────────────────────────────

    def refresh(self):
        """Refresh all data from both repositories (called on page navigation)."""
        self._load_data()
