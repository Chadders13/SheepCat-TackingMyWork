"""
Work Log Review Page - Review and update today's work log entries.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import requests
import threading
from typing import Optional
from data_repository import DataRepository
import theme


class ReviewLogPage(tk.Frame):
    """Page for reviewing and editing work log entries"""
    
    def __init__(self, parent, data_repository: DataRepository, settings_manager=None):
        """
        Initialize the Review Log page.
        
        Args:
            parent: Parent tkinter widget
            data_repository: Data repository instance
            settings_manager: Optional SettingsManager instance for AI re-run
        """
        super().__init__(parent, bg=theme.WINDOW_BG)
        self.data_repository = data_repository
        self.settings_manager = settings_manager
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
        self.task_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
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
        
        # Bind selection to show AI summary and double-click to edit
        self.task_tree.bind('<<TreeviewSelect>>', self._on_task_select)
        self.task_tree.bind('<Double-1>', self._on_task_double_click)
        
        # AI Summary panel
        summary_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        summary_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        tk.Label(
            summary_frame, text="AI Summary:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(anchor='w')
        
        self.ai_summary_text = tk.Text(
            summary_frame, height=3, wrap=tk.WORD,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat', padx=6, pady=4,
            state='disabled',
        )
        self.ai_summary_text.pack(fill='x')
        
        # Action buttons
        button_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        button_frame.pack(fill='x', padx=10, pady=5)
        
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
        
        # Re-run with model section
        rerun_frame = tk.Frame(self, bg=theme.WINDOW_BG)
        rerun_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            rerun_frame, text="Re-run with model:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(side='left', padx=(0, 5))
        
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            rerun_frame, textvariable=self.model_var,
            width=22, state='readonly',
        )
        self.model_combo.pack(side='left', padx=5)
        
        theme.RoundedButton(
            rerun_frame, text="Refresh Models", command=self._refresh_models,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=14, cursor='hand2',
        ).pack(side='left', padx=5)
        
        theme.RoundedButton(
            rerun_frame, text="Re-generate AI Summaries", command=self._rerun_with_model,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY, width=22, cursor='hand2',
        ).pack(side='left', padx=5)
        
        # Status label
        self.status_label = tk.Label(
            self, text="",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        self.status_label.pack(pady=5)
        
        # Populate model list on creation if settings_manager is available
        self._refresh_models()
    
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
        
        # Clear AI summary display
        self._set_ai_summary_display("")
        
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
    
    def _set_ai_summary_display(self, text: str):
        """Update the AI summary text widget (handles state toggling)."""
        self.ai_summary_text.config(state='normal')
        self.ai_summary_text.delete('1.0', 'end')
        self.ai_summary_text.insert('1.0', text)
        self.ai_summary_text.config(state='disabled')
    
    def _on_task_select(self, event):
        """Show AI summary for the selected task."""
        selection = self.task_tree.selection()
        if not selection:
            return
        task_id = selection[0]
        for task in self.tasks:
            if task.get('task_id') == task_id:
                self._set_ai_summary_display(task.get('AI Summary', ''))
                break
    
    def _on_task_double_click(self, event):
        """Handle double-click on a task to toggle resolved status"""
        selection = self.task_tree.selection()
        if not selection:
            return
        
        task_id = selection[0]
        item = self.task_tree.item(task_id)
        current_resolved = item['values'][4]  # Resolved is 5th column
        
        # Toggle resolved status
        new_resolved = "No" if current_resolved == "Yes" else "Yes"
        
        # Update in repository
        if self.data_repository.update_task_resolved_status(task_id, new_resolved):
            # Update in tree
            values = list(item['values'])
            values[4] = new_resolved
            self.task_tree.item(task_id, values=values)
            self.status_label.config(text=f"Updated task to Resolved={new_resolved}")
        else:
            messagebox.showerror("Error", "Failed to update task status")
    
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
    
    def _refresh_models(self):
        """Fetch available models from the Ollama server and populate the combobox."""
        if not self.settings_manager:
            return
        
        try:
            from urllib.parse import urlparse
            from ollama_client import check_connection, DEFAULT_OLLAMA_BASE_URL
            
            api_url = self.settings_manager.get("ai_api_url", "")
            parsed = urlparse(api_url)
            if parsed.scheme and parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"
            else:
                base_url = DEFAULT_OLLAMA_BASE_URL
            
            result = check_connection(base_url)
            if result.success and result.models:
                self.model_combo['values'] = result.models
                # Pre-select the currently configured model if available
                current_model = self.settings_manager.get("ai_model", "")
                if current_model in result.models:
                    self.model_var.set(current_model)
                elif result.models:
                    self.model_var.set(result.models[0])
            else:
                self.model_combo['values'] = []
                self.status_label.config(text="Could not reach Ollama server to fetch models.")
        except Exception as e:
            self.model_combo['values'] = []
            self.status_label.config(text=f"Error fetching models: {e}")
    
    def _rerun_with_model(self):
        """Re-generate AI summaries for all tasks on the current date using the selected model."""
        if not self.settings_manager:
            messagebox.showwarning(
                "Not Available",
                "Settings manager not configured. Cannot re-run AI summaries.",
            )
            return
        
        selected_model = self.model_var.get()
        if not selected_model:
            messagebox.showwarning("No Model Selected", "Please select a model from the list.")
            return
        
        # Get display tasks (non-marker rows)
        rerun_tasks = [
            task for task in self.tasks
            if 'DAY STARTED' not in task.get('Title', '')
            and 'DAY ENDED' not in task.get('Title', '')
            and 'HOURLY SUMMARY' not in task.get('Title', '')
            and 'END OF DAY SUMMARY' not in task.get('Title', '')
        ]
        
        if not rerun_tasks:
            messagebox.showinfo("No Tasks", "No tasks found for the selected date.")
            return
        
        if not messagebox.askyesno(
            "Re-generate AI Summaries",
            f"Re-generate AI summaries for {len(rerun_tasks)} task(s) on "
            f"{self.date_var.get()} using model '{selected_model}'?\n\n"
            "This will overwrite the existing AI summaries.",
        ):
            return
        
        self.status_label.config(text=f"Re-generating summaries with '{selected_model}'…")
        self.update_idletasks()
        
        threading.Thread(
            target=self._rerun_thread,
            args=(rerun_tasks, selected_model),
            daemon=True,
        ).start()
    
    def _rerun_thread(self, tasks, model: str):
        """Background thread: call LLM for each task and update the CSV."""
        api_url = self.settings_manager.get("ai_api_url")
        timeout = self.settings_manager.get("llm_request_timeout", 120)
        
        completed = 0
        failed = 0
        
        for task in tasks:
            task_id = task.get('task_id')
            title = task.get('Title', '')
            ticket = task.get('Ticket', '')
            duration = task.get('Duration (Min)', '0')
            system_info = task.get('System Info', '')
            
            prompt = (
                f"I just worked for {duration} minutes on a task.\n"
                f"Title: {title}\n"
                f"Ticket: {ticket}\n"
                f"Context: {system_info}\n"
                "Write a very brief, professional single-sentence log entry for this in Markdown format."
            )
            
            payload = {"model": model, "prompt": prompt, "stream": False}
            
            try:
                response = requests.post(api_url, json=payload, timeout=timeout)
                if response.status_code == 200:
                    new_summary = response.json().get("response", "").strip()
                else:
                    new_summary = f"Error: {response.status_code}"
                    failed += 1
            except Exception as e:
                new_summary = f"LLM Connection Failed: {str(e)}"
                failed += 1
            
            if self.data_repository.update_task_ai_summary(task_id, new_summary):
                # Update cached task data
                task['AI Summary'] = new_summary
                completed += 1
                self.after(
                    0,
                    lambda c=completed, t=len(tasks): self.status_label.config(
                        text=f"Re-generating… {c}/{t} done"
                    ),
                )
            else:
                failed += 1
        
        word = "summary" if completed == 1 else "summaries"
        summary_msg = f"Re-generated {completed} AI {word} with '{model}'."
        if failed:
            summary_msg += f" {failed} failed."
        self.after(0, lambda: self.status_label.config(text=summary_msg))
    
    def refresh(self):
        """Refresh the page (called when navigating to this page)"""
        self._set_today()

