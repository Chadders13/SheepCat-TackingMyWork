"""
Work Log Review Page - Review and update today's work log entries.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from typing import Optional
from data_repository import DataRepository
import theme


class ReviewLogPage(tk.Frame):
    """Page for reviewing and editing work log entries"""
    
    def __init__(self, parent, data_repository: DataRepository):
        """
        Initialize the Review Log page.
        
        Args:
            parent: Parent tkinter widget
            data_repository: Data repository instance
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.data_repository = data_repository
        self.current_date = datetime.date.today()
        self.tasks = []
        
        self._create_widgets()
        self._load_tasks()
    
    def _create_widgets(self):
        """Create the UI widgets for the review page"""
        # Header
        header_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(
            header_frame, text="Work Log Review",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        
        # Date selector
        date_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        date_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            date_frame, text="Date:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=5)
        
        self.date_var = tk.StringVar(value=self.current_date.strftime("%Y-%m-%d"))
        self.date_entry = tk.Entry(
            date_frame, textvariable=self.date_var, width=12,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
        )
        self.date_entry.pack(side='left', padx=5)
        
        theme.RoundedButton(
            date_frame, text="Today", command=self._set_today, width=8,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        ).pack(side='left', padx=2)
        theme.RoundedButton(
            date_frame, text="Load", command=self._load_tasks, width=8,
            bg=theme.PRIMARY, fg=theme.TEXT, cursor='hand2',
        ).pack(side='left', padx=2)
        theme.RoundedButton(
            date_frame, text="Refresh", command=self._load_tasks, width=8,
            bg=theme.SURFACE_BG, fg=theme.TEXT, cursor='hand2',
        ).pack(side='left', padx=2)
        
        # Task list with scrollbar
        list_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create Treeview for task list
        columns = ('time', 'title', 'ticket', 'duration', 'resolved')
        self.task_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.task_tree.heading('time', text='Time')
        self.task_tree.heading('title', text='Title')
        self.task_tree.heading('ticket', text='Ticket')
        self.task_tree.heading('duration', text='Duration (min)')
        self.task_tree.heading('resolved', text='Resolved')
        
        # Define column widths
        self.task_tree.column('time', width=80)
        self.task_tree.column('title', width=300)
        self.task_tree.column('ticket', width=100)
        self.task_tree.column('duration', width=80)
        self.task_tree.column('resolved', width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        self.task_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind double-click to edit ticket/title
        self.task_tree.bind('<Double-1>', self._on_task_double_click)
        
        # Action buttons
        button_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        theme.RoundedButton(
            button_frame, text="Mark as Resolved", command=self._mark_resolved,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=15, cursor='hand2',
        ).pack(side='left', padx=5)
        theme.RoundedButton(
            button_frame, text="Mark as Unresolved", command=self._mark_unresolved,
            bg=theme.ACCENT, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=15, cursor='hand2',
        ).pack(side='left', padx=5)
        theme.RoundedButton(
            button_frame, text="Edit Task", command=self._edit_selected_task,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=12, cursor='hand2',
        ).pack(side='left', padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=5)
    
    def _set_today(self):
        """Set the date to today"""
        self.current_date = datetime.date.today()
        self.date_var.set(self.current_date.strftime("%Y-%m-%d"))
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks for the selected date"""
        try:
            # Parse the date from entry
            date_str = self.date_var.get()
            self.current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format")
            return
        
        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # Load tasks from repository
        self.tasks = self.data_repository.get_tasks_by_date(self.current_date)
        
        # Filter out marker rows (DAY STARTED, DAY ENDED, HOURLY SUMMARY)
        display_tasks = [
            task for task in self.tasks
            if 'DAY STARTED' not in task.get('Title', '') 
            and 'DAY ENDED' not in task.get('Title', '')
            and 'HOURLY SUMMARY' not in task.get('Title', '')
            and 'END OF DAY SUMMARY' not in task.get('Title', '')
        ]
        
        # Populate tree
        for task in display_tasks:
            start_time = task.get('Start Time', '')
            # Extract just the time portion
            if start_time:
                try:
                    time_obj = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                    time_str = time_obj.strftime("%H:%M")
                except:
                    time_str = start_time
            else:
                time_str = ""
            
            self.task_tree.insert('', 'end', iid=task.get('task_id'), values=(
                time_str,
                task.get('Title', ''),
                task.get('Ticket', ''),
                task.get('Duration (Min)', ''),
                task.get('Resolved', 'No')
            ))
        
        self.status_label.config(text=f"Loaded {len(display_tasks)} tasks for {date_str}")
    
    def _on_task_double_click(self, event):
        """Handle double-click on a task to open the inline edit dialog"""
        selection = self.task_tree.selection()
        if not selection:
            return
        self._open_edit_dialog(selection[0])
    
    def _edit_selected_task(self):
        """Open the edit dialog for the currently selected task"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a task to edit")
            return
        self._open_edit_dialog(selection[0])
    
    def _open_edit_dialog(self, task_id: str):
        """
        Open a dialog to edit the ticket number and title of a task.
        
        Args:
            task_id: The task identifier (Treeview iid)
        """
        item = self.task_tree.item(task_id)
        values = item['values']
        current_title = values[1]
        current_ticket = values[2]
        
        dialog = tk.Toplevel(self)
        dialog.title("Edit Task")
        dialog.configure(bg=theme.WINDOW_BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        
        # Centre the dialog relative to the parent window
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 180) // 2
        dialog.geometry(f"400x180+{x}+{y}")
        
        pad = {'padx': 10, 'pady': 6}
        
        # Ticket field
        ticket_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        ticket_frame.pack(fill='x', **pad)
        tk.Label(
            ticket_frame, text="Ticket:", width=10, anchor='w',
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        ticket_var = tk.StringVar(value=current_ticket)
        tk.Entry(
            ticket_frame, textvariable=ticket_var,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left', fill='x', expand=True)
        
        # Title / message field
        title_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        title_frame.pack(fill='x', **pad)
        tk.Label(
            title_frame, text="Message:", width=10, anchor='w',
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left')
        title_var = tk.StringVar(value=current_title)
        tk.Entry(
            title_frame, textvariable=title_var,
            bg=theme.INPUT_BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        ).pack(side='left', fill='x', expand=True)
        
        def _save():
            new_ticket = ticket_var.get().strip()
            new_title = title_var.get().strip()
            if not new_title:
                messagebox.showwarning("Validation", "Message cannot be empty", parent=dialog)
                return
            if self.data_repository.update_task_fields(task_id, new_ticket, new_title):
                updated_values = list(values)
                updated_values[1] = new_title
                updated_values[2] = new_ticket
                self.task_tree.item(task_id, values=updated_values)
                self.status_label.config(text="Task updated successfully")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update task", parent=dialog)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_frame.pack(fill='x', **pad)
        theme.RoundedButton(
            btn_frame, text="Save", command=_save,
            bg=theme.PRIMARY, fg=theme.TEXT, width=8, cursor='hand2',
        ).pack(side='left', padx=5)
        theme.RoundedButton(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg=theme.SURFACE_BG, fg=theme.TEXT, width=8, cursor='hand2',
        ).pack(side='left', padx=5)
        
        dialog.bind('<Return>', lambda e: _save())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _mark_resolved(self):
        """Mark selected task(s) as resolved"""
        self._update_selected_status("Yes")
    
    def _mark_unresolved(self):
        """Mark selected task(s) as unresolved"""
        self._update_selected_status("No")
    
    def _update_selected_status(self, resolved: str):
        """
        Update the resolved status of selected task(s).
        
        Args:
            resolved: "Yes" or "No"
        """
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select one or more tasks to update")
            return
        
        updated_count = 0
        for task_id in selection:
            if self.data_repository.update_task_resolved_status(task_id, resolved):
                # Update in tree
                item = self.task_tree.item(task_id)
                values = list(item['values'])
                values[4] = resolved
                self.task_tree.item(task_id, values=values)
                updated_count += 1
        
        status_text = "resolved" if resolved == "Yes" else "unresolved"
        self.status_label.config(text=f"Marked {updated_count} task(s) as {status_text}")
    
    def refresh(self):
        """Refresh the page (called when navigating to this page)"""
        self._set_today()
