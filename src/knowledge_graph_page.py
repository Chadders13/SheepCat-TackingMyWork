"""
Knowledge Graph Page for SheepCat Work Tracker.

Provides a UI for categorising tasks with tags, adding timing notes,
importing documents, and linking documents to tasks.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

import theme
from graph_repository import GraphRepository


class KnowledgeGraphPage(tk.Frame):
    """Page for managing task tags, timing notes, documents, and their relationships."""

    def __init__(self, parent, graph_repository: GraphRepository, data_repository):
        """
        Initialise the Knowledge Graph page.

        Args:
            parent:           Parent tkinter widget.
            graph_repository: :class:`GraphRepository` instance.
            data_repository:  Data repository (CSVDataRepository) for reading tasks.
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.graph_repo = graph_repository
        self.data_repo = data_repository
        self._all_tasks_data: list = []
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
        ).pack(anchor='w', padx=10, pady=(0, 8))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=4)

        self._create_tags_tab()
        self._create_documents_tab()

    # ── Tags tab ──────────────────────────────────────────────────────────────

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
        """Load all work-log tasks into both task trees."""
        for tree in (self.all_tasks_tree, self.doc_all_tasks_tree):
            for item in tree.get_children():
                tree.delete(item)

        self._all_tasks_data = self.data_repo.get_all_tasks()

        seen_in_all: set = set()
        seen_in_doc: set = set()
        for task in self._all_tasks_data:
            task_id = task.get('Start Time', '')
            title = task.get('Title', '')
            tags = ', '.join(self.graph_repo.get_task_tags(task_id))

            if task_id not in seen_in_all:
                self.all_tasks_tree.insert(
                    '', 'end', iid=task_id,
                    values=(task_id, title, tags),
                )
                seen_in_all.add(task_id)

            if task_id not in seen_in_doc:
                self.doc_all_tasks_tree.insert(
                    '', 'end', iid=task_id,
                    values=(task_id, title),
                )
                seen_in_doc.add(task_id)

    def _load_documents(self):
        """Reload the documents tree."""
        for item in self.docs_tree.get_children():
            self.docs_tree.delete(item)
        for doc in self.graph_repo.get_all_documents():
            self.docs_tree.insert(
                '', 'end', iid=str(doc['id']),
                values=(doc['name'], doc['added_at'][:10]),
            )

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
        task_id = task_sel[0]
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
            task_id = item
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
        task_id = task_sel[0]
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
        task_id = task_sel[0]
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
