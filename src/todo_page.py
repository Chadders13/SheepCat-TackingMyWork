"""
Todo List Page - Manage a personal list of tasks to focus on.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import theme
from todo_repository import TodoRepository


_PRIORITIES = ("High", "Medium", "Low")


class TodoPage(tk.Frame):
    """Page for managing a personal todo/focus list."""

    def __init__(self, parent, todo_repository: TodoRepository):
        """
        Initialize the Todo page.

        Args:
            parent: Parent tkinter widget
            todo_repository: TodoRepository instance
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.todo_repository = todo_repository
        self._create_widgets()
        self._load_todos()

    # ── Widget construction ────────────────────────────────────────────────────

    def _create_widgets(self):
        """Create all UI widgets for the todo page."""
        # Header
        tk.Label(
            self, text="Todo List",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(anchor='w', padx=10, pady=(10, 5))

        tk.Label(
            self, text="Keep track of the tasks you're concentrating on right now.",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(anchor='w', padx=10, pady=(0, 8))

        # Task list
        list_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('task', 'priority', 'status', 'created')
        self.todo_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        self.todo_tree.heading('task', text='Task')
        self.todo_tree.heading('priority', text='Priority')
        self.todo_tree.heading('status', text='Status')
        self.todo_tree.heading('created', text='Created')

        self.todo_tree.column('task', width=350)
        self.todo_tree.column('priority', width=80)
        self.todo_tree.column('status', width=80)
        self.todo_tree.column('created', width=130)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.todo_tree.yview)
        self.todo_tree.configure(yscrollcommand=scrollbar.set)

        self.todo_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind double-click to toggle status
        self.todo_tree.bind('<Double-1>', self._on_double_click)

        # Action buttons
        btn_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        btn_frame.pack(fill='x', padx=10, pady=8)

        tk.Button(
            btn_frame, text="Add Task", command=self._add_todo,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD, width=12, relief='flat', cursor='hand2',
            padx=8, pady=4,
        ).pack(side='left', padx=4)

        tk.Button(
            btn_frame, text="Mark Done", command=self._mark_done,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=12, relief='flat', cursor='hand2',
            padx=8, pady=4,
        ).pack(side='left', padx=4)

        tk.Button(
            btn_frame, text="Mark Pending", command=self._mark_pending,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=12, relief='flat', cursor='hand2',
            padx=8, pady=4,
        ).pack(side='left', padx=4)

        tk.Button(
            btn_frame, text="Delete", command=self._delete_todo,
            bg=theme.RED, fg=theme.TEXT,
            font=theme.FONT_BODY, width=12, relief='flat', cursor='hand2',
            padx=8, pady=4,
        ).pack(side='left', padx=4)

        # Status bar
        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=4)

    # ── Data loading ───────────────────────────────────────────────────────────

    def _load_todos(self):
        """Load all todos from the repository and populate the tree."""
        for item in self.todo_tree.get_children():
            self.todo_tree.delete(item)

        todos = self.todo_repository.get_all_todos()
        for todo in todos:
            self.todo_tree.insert(
                '', 'end',
                iid=todo.get('ID'),
                values=(
                    todo.get('Task', ''),
                    todo.get('Priority', ''),
                    todo.get('Status', ''),
                    todo.get('Created', ''),
                ),
            )

        pending = sum(1 for t in todos if t.get('Status') == 'Pending')
        self.status_label.config(
            text=f"{len(todos)} item(s) total — {pending} pending"
        )

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_double_click(self, _event):
        """Toggle status on double-click."""
        selection = self.todo_tree.selection()
        if not selection:
            return
        todo_id = selection[0]
        current_status = self.todo_tree.item(todo_id)['values'][2]
        new_status = "Pending" if current_status == "Done" else "Done"
        self._set_status(todo_id, new_status)

    def _add_todo(self):
        """Open a dialog to add a new todo item."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Todo Task")
        dialog.geometry("420x250")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)

        tk.Label(
            dialog, text="Task description:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT, anchor='w',
        ).pack(fill='x', padx=15, pady=(15, 2))

        task_var = tk.StringVar()
        task_entry = tk.Entry(
            dialog, textvariable=task_var,
            font=theme.FONT_BODY, bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
        )
        task_entry.pack(fill='x', padx=15, pady=(0, 10))

        tk.Label(
            dialog, text="Priority:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT, anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 2))

        priority_var = tk.StringVar(value="Medium")
        priority_combo = ttk.Combobox(
            dialog, textvariable=priority_var,
            values=list(_PRIORITIES), state='readonly', width=12,
        )
        priority_combo.pack(anchor='w', padx=15, pady=(0, 10))

        tk.Label(
            dialog, text="Notes (optional):",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT, anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 2))

        notes_var = tk.StringVar()
        tk.Entry(
            dialog, textvariable=notes_var,
            font=theme.FONT_BODY, bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief='flat',
        ).pack(fill='x', padx=15, pady=(0, 10))

        result = {"ok": False}

        def on_ok():
            task = task_var.get().strip()
            if not task:
                messagebox.showwarning("Input Required", "Please enter a task description.", parent=dialog)
                return
            result["task"] = task
            result["priority"] = priority_var.get()
            result["notes"] = notes_var.get().strip()
            result["ok"] = True
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_frame.pack(pady=6)
        tk.Button(
            btn_frame, text="Add", command=on_ok,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=10, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)
        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)

        task_entry.focus_set()
        self.wait_window(dialog)

        if result.get("ok"):
            if self.todo_repository.add_todo(result["task"], result["priority"], result["notes"]):
                self._load_todos()
                self.status_label.config(text="Task added.")
            else:
                messagebox.showerror("Error", "Failed to add task.")

    def _mark_done(self):
        """Mark selected item(s) as Done."""
        self._update_selected_status("Done")

    def _mark_pending(self):
        """Mark selected item(s) as Pending."""
        self._update_selected_status("Pending")

    def _update_selected_status(self, status: str):
        """Update the status of all selected items."""
        selection = self.todo_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select one or more tasks to update.")
            return
        for todo_id in selection:
            self._set_status(todo_id, status)

    def _set_status(self, todo_id: str, status: str):
        """Set the status of a single item and refresh the tree row."""
        if self.todo_repository.update_todo_status(todo_id, status):
            values = list(self.todo_tree.item(todo_id)['values'])
            values[2] = status
            self.todo_tree.item(todo_id, values=values)
            self.status_label.config(text=f"Task marked as {status}.")
        else:
            messagebox.showerror("Error", "Failed to update task status.")

    def _delete_todo(self):
        """Delete selected todo item(s) after confirmation."""
        selection = self.todo_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select one or more tasks to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete {len(selection)} task(s)?"):
            return
        for todo_id in selection:
            if self.todo_repository.delete_todo(todo_id):
                self.todo_tree.delete(todo_id)
        self._load_todos()

    # ── Public API ─────────────────────────────────────────────────────────────

    def refresh(self):
        """Refresh the page (called when navigating to this page)."""
        self._load_todos()
