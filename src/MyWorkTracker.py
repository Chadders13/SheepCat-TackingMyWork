import tkinter as tk
from tkinter import messagebox, scrolledtext
import csv
import datetime
import os
import platform
import requests
import json
import threading
from csv_data_repository import CSVDataRepository
from review_log_page import ReviewLogPage
from settings_manager import SettingsManager
from settings_page import SettingsPage
import theme
 
_NO_TICKET_LABEL = "(no ticket)"


class WorkLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SheepCat — Tracking My Work")
        self.root.geometry("800x600")
        self.root.configure(bg=theme.WINDOW_BG)

        # Apply SheepCat brand theme to all ttk widgets
        theme.setup_ttk_styles(root)
        
        # Load settings
        self.settings_manager = SettingsManager()
        
        # Initialize data repository using the configured log file path
        self.data_repository = CSVDataRepository(self.settings_manager.get_log_file_path())
        self.data_repository.initialize()
        
        # State variables
        self.is_running = False
        self.hourly_tasks = []  # Track tasks for the current hour
        self.hour_start_time = None
        self.session_start_time = None  # Track when the session started
        self.timer_id = None
        self.countdown_id = None
        self.next_checkin_time = None
        
        # Create menu bar
        self._create_menu()
        
        # Create main container for pages
        self.container = tk.Frame(root, bg=theme.WINDOW_BG)
        self.container.pack(fill='both', expand=True)
        
        # Create pages
        self.pages = {}
        self._create_tracker_page()
        self._create_review_page()
        self._create_settings_page()
        
        # Show tracker page by default
        self.show_page("tracker")
    
    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(
            self.root,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            activebackground=theme.PRIMARY_D, activeforeground=theme.TEXT,
            borderwidth=0,
        )
        self.root.config(menu=menubar)

        # Pages menu
        pages_menu = tk.Menu(
            menubar, tearoff=0,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            activebackground=theme.PRIMARY_D, activeforeground=theme.TEXT,
        )
        menubar.add_cascade(label="Pages", menu=pages_menu)
        pages_menu.add_command(label="Task Tracker", command=lambda: self.show_page("tracker"))
        pages_menu.add_command(label="Review Work Log", command=lambda: self.show_page("review"))
        pages_menu.add_command(label="Settings", command=lambda: self.show_page("settings"))
        pages_menu.add_separator()
        pages_menu.add_command(label="Exit", command=self.root.quit)
    
    def _create_tracker_page(self):
        """Create the tracker page (original functionality)"""
        page = tk.Frame(self.container, bg=theme.WINDOW_BG)
        self.pages["tracker"] = page

        # UI Elements
        status_label = tk.Label(
            page, text="Ready to track",
            font=theme.FONT_H3, bg=theme.WINDOW_BG, fg=theme.TEXT,
        )
        status_label.pack(pady=20)
        self.status_label = status_label

        countdown_label = tk.Label(
            page, text="",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.PRIMARY,
        )
        countdown_label.pack(pady=5)
        self.countdown_label = countdown_label

        info_label = tk.Label(
            page, text=f"Model: {self.settings_manager.get('ai_model')}",
            font=theme.FONT_SMALL, bg=theme.WINDOW_BG, fg=theme.MUTED,
        )
        info_label.pack(pady=0)
        self.info_label = info_label

        btn_start = tk.Button(
            page, text="Start Day", command=self.start_tracking,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY_BOLD, width=20,
            relief='flat', cursor='hand2', padx=8, pady=6,
        )
        btn_start.pack(pady=5)
        self.btn_start = btn_start

        btn_add_task = tk.Button(
            page, text="Add Task", command=self.add_task,
            bg=theme.PRIMARY, fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD, width=20,
            state=tk.DISABLED, relief='flat', cursor='hand2', padx=8, pady=6,
        )
        btn_add_task.pack(pady=5)
        self.btn_add_task = btn_add_task

        btn_stop = tk.Button(
            page, text="Stop / End Day", command=self.stop_tracking,
            bg=theme.RED, fg=theme.TEXT,
            font=theme.FONT_BODY_BOLD, width=20,
            state=tk.DISABLED, relief='flat', cursor='hand2', padx=8, pady=6,
        )
        btn_stop.pack(pady=5)
        self.btn_stop = btn_stop
    
    def _create_review_page(self):
        """Create the review log page"""
        page = ReviewLogPage(self.container, self.data_repository)
        self.pages["review"] = page
    
    def _create_settings_page(self):
        """Create the settings page"""
        page = SettingsPage(self.container, self.settings_manager,
                            on_settings_changed=self._on_settings_changed)
        self.pages["settings"] = page
    
    def _on_settings_changed(self):
        """Called after settings are saved; refreshes dependent state."""
        # Update the model info label on the tracker page
        self.info_label.config(text=f"Model: {self.settings_manager.get('ai_model')}")
        
        # Reinitialise the data repository with the (possibly new) log file path
        new_path = self.settings_manager.get_log_file_path()
        self.data_repository = CSVDataRepository(new_path)
        self.data_repository.initialize()
        
        # Update the review page to use the new repository
        self.pages["review"].data_repository = self.data_repository
    
    def show_page(self, page_name):
        """
        Show the specified page.
        
        Args:
            page_name: Name of the page to show ("tracker" or "review")
        """
        # Hide all pages
        for page in self.pages.values():
            page.pack_forget()
        
        # Show selected page
        if page_name in self.pages:
            page = self.pages[page_name]
            page.pack(fill='both', expand=True)
            
            # Refresh the page if it has a refresh method
            if hasattr(page, 'refresh'):
                page.refresh()
    
    def get_system_context(self):
        return f"OS: {platform.system()} | Node: {platform.node()}"
 
    def ask_task_details(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Task")
        dialog.geometry("460x520")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=theme.WINDOW_BG)

        # ── Notes section ────────────────────────────────────────────────────
        tk.Label(
            dialog, text="Task Notes:",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
            anchor='w',
        ).pack(fill='x', padx=15, pady=(15, 2))

        notes_text = tk.Text(
            dialog, height=6, wrap=tk.WORD,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat', padx=6, pady=4,
        )
        notes_text.pack(fill='x', padx=15, pady=(0, 10))

        # ── Ticket section ───────────────────────────────────────────────────
        tk.Label(
            dialog, text="Ticket ID(s) (comma-separated for multiple):",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
            anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 2))

        ticket_var = tk.StringVar()
        ticket_entry = tk.Entry(
            dialog, textvariable=ticket_var,
            font=theme.FONT_BODY,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief='flat',
        )
        ticket_entry.pack(fill='x', padx=15, pady=(0, 10))

        # ── Resolved section (per-ticket checkboxes) ─────────────────────────
        tk.Label(
            dialog, text="Resolved Status (tick each resolved ticket):",
            font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
            anchor='w',
        ).pack(fill='x', padx=15, pady=(0, 2))

        resolved_outer = tk.Frame(dialog, bg=theme.SURFACE_BG, pady=6)
        resolved_outer.pack(fill='x', padx=15, pady=(0, 10))

        resolved_vars = {}

        def _refresh_resolved_checkboxes(*_):
            for widget in resolved_outer.winfo_children():
                widget.destroy()
            resolved_vars.clear()

            tickets_raw = ticket_var.get()
            tickets = [t.strip() for t in tickets_raw.split(',') if t.strip()]
            if not tickets:
                tickets = [_NO_TICKET_LABEL]

            for tkt in tickets:
                var = tk.BooleanVar(value=False)
                key = '' if tkt == _NO_TICKET_LABEL else tkt
                resolved_vars[key] = var
                tk.Checkbutton(
                    resolved_outer,
                    text=f"Resolved: {tkt}",
                    variable=var,
                    font=theme.FONT_BODY,
                    bg=theme.SURFACE_BG, fg=theme.TEXT,
                    selectcolor=theme.INPUT_BG,
                    activebackground=theme.SURFACE_BG, activeforeground=theme.TEXT,
                    anchor='w',
                ).pack(fill='x', padx=10, pady=1)

        ticket_var.trace_add('write', _refresh_resolved_checkboxes)
        _refresh_resolved_checkboxes()

        # ── OK / Cancel buttons ───────────────────────────────────────────────
        result = {"cancelled": True}

        def on_ok():
            notes = notes_text.get('1.0', 'end-1c').strip()
            if not notes:
                messagebox.showwarning("Input Required", "Please enter task notes.", parent=dialog)
                return
            result.update({
                "title": notes,
                "ticket": ticket_var.get().strip(),
                "resolved": {k: v.get() for k, v in resolved_vars.items()},
                "cancelled": False,
            })
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=theme.WINDOW_BG)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="OK", command=on_ok,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=10, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)
        tk.Button(
            btn_frame, text="Cancel", command=on_cancel,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=10, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)

        notes_text.focus_set()
        self.root.wait_window(dialog)

        if result.get("cancelled"):
            return None
        return result
 
    def generate_ai_markdown(self, task_info, duration):
        """
        Calls the local Ollama instance to generate a markdown log.
        """
        prompt = (
            f"I just worked for {duration} minutes on a task.\n"
            f"Title: {task_info.get('title')}\n"
            f"Ticket: {task_info.get('ticket')}\n"
            f"Context: {task_info.get('system_info')}\n"
            "Write a very brief, professional single-sentence log entry for this in Markdown format."
        )

        payload = {
            "model": self.settings_manager.get("ai_model"),
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(
                self.settings_manager.get("ai_api_url"),
                json=payload,
                timeout=self.settings_manager.get("llm_request_timeout"))
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"LLM Connection Failed: {str(e)}"
    
    def generate_hourly_summary(self, tasks):
        """
        Generates a summary of all tasks completed in the hour.
        """
        if not tasks:
            return "No tasks completed this hour."
        
        task_list = "\n".join([f"- {t.get('title')} ({t.get('ticket')}) - {t.get('duration')} min" for t in tasks])
        prompt = (
            f"Summarize the following tasks completed in the last hour:\n"
            f"{task_list}\n"
            "Write a brief 2-3 sentence summary of the work accomplished."
        )

        payload = {
            "model": self.settings_manager.get("ai_model"),
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(
                self.settings_manager.get("ai_api_url"),
                json=payload,
                timeout=self.settings_manager.get("llm_request_timeout"))
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"LLM Connection Failed: {str(e)}"
    
    def read_todays_summaries(self, start_time):
        """
        Read all summaries and tasks from today's session from the CSV file.
        Returns a dict with summaries, tickets, and tasks.
        """
        summaries = []
        tickets = set()
        tasks = []
        
        # Use repository to get tasks since start_time
        rows = self.data_repository.get_tasks_since(start_time)
        
        for row in rows:
            ai_summary = row.get('AI Summary', '').strip()
            title = row.get('Title', '').strip()
            ticket = row.get('Ticket', '').strip()
            
            # Collect summaries (skip markers and empty summaries)
            if ai_summary and 'DAY STARTED' not in title and 'DAY ENDED' not in title:
                summaries.append(ai_summary)
            
            # Collect tickets
            if ticket:
                # Split comma-separated tickets
                for t in ticket.split(','):
                    t = t.strip()
                    if t:
                        tickets.add(t)
            
            # Collect task info
            if title and 'DAY STARTED' not in title and 'DAY ENDED' not in title:
                tasks.append({
                    'title': title,
                    'ticket': ticket,
                    'duration': row.get('Duration (Min)', '0')
                })
        
        return {
            'summaries': summaries,
            'tickets': sorted(list(tickets)),
            'tasks': tasks
        }
    
    def chunk_text(self, text, max_chars=None):
        """
        Split text into chunks for LLM processing.
        Tries to split at sentence boundaries when possible.
        """
        if max_chars is None:
            max_chars = self.settings_manager.get("max_chunk_size")
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')
        
        for i, sentence in enumerate(sentences):
            # Add period back if it was removed (but not for the last sentence which may already have one)
            if i < len(sentences) - 1 and not sentence.endswith('.'):
                sentence = sentence + '.'
            
            # If adding this sentence would exceed limit
            if len(current_chunk) + len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def generate_day_summary(self, day_data):
        """
        Generate a comprehensive end-of-day summary from all summaries.
        Handles large text by chunking if necessary.
        """
        summaries = day_data.get('summaries', [])
        tickets = day_data.get('tickets', [])
        tasks = day_data.get('tasks', [])
        
        if not summaries and not tasks:
            return "No work logged today."
        
        # Prepare the content to summarize
        content = "\n\n".join(summaries) if summaries else ""
        
        # Add task list
        if tasks:
            task_list = "\n".join([f"- {t.get('title')} ({t.get('ticket', 'N/A')}) - {t.get('duration')} min" for t in tasks])
            content += f"\n\nTasks completed:\n{task_list}"
        
        # Check if we need to chunk
        chunks = self.chunk_text(content, max_chars=self.settings_manager.get("max_chunk_size"))
        
        if len(chunks) == 1:
            # Single chunk - process normally
            prompt = (
                f"Create a comprehensive end-of-day summary based on the following work:\n\n"
                f"{content}\n\n"
                f"Tickets worked on: {', '.join(tickets) if tickets else 'None'}\n\n"
                "Write a professional summary that:\n"
                "1. Highlights key accomplishments\n"
                "2. Lists the tickets/references addressed\n"
                "3. Provides a cohesive overview of the day's work\n"
                "Format in Markdown with clear sections."
            )
            
            return self._call_llm_for_summary(prompt)
        else:
            # Multiple chunks - summarize incrementally
            partial_summaries = []
            
            for i, chunk in enumerate(chunks):
                prompt = (
                    f"Summarize this portion ({i+1}/{len(chunks)}) of the day's work:\n\n"
                    f"{chunk}\n\n"
                    "Provide a concise summary of the key points."
                )
                partial = self._call_llm_for_summary(prompt)
                partial_summaries.append(partial)
            
            # Final comprehensive summary
            combined = "\n\n".join(partial_summaries)
            final_prompt = (
                f"Create a comprehensive end-of-day summary from these partial summaries:\n\n"
                f"{combined}\n\n"
                f"Tickets worked on: {', '.join(tickets) if tickets else 'None'}\n\n"
                "Write a professional summary that:\n"
                "1. Highlights key accomplishments\n"
                "2. Lists the tickets/references addressed\n"
                "3. Provides a cohesive overview of the day's work\n"
                "Format in Markdown with clear sections."
            )
            
            return self._call_llm_for_summary(final_prompt)
    
    def _call_llm_for_summary(self, prompt):
        """Helper method to call LLM API"""
        payload = {
            "model": self.settings_manager.get("ai_model"),
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.settings_manager.get("ai_api_url"),
                json=payload,
                timeout=self.settings_manager.get("llm_request_timeout"))
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"LLM Connection Failed: {str(e)}"
    
    def show_summary_editor(self, summary_text, tickets):
        """
        Display a window to view and edit the day summary before saving.
        """
        editor = tk.Toplevel(self.root)
        editor.title("End of Day Summary")
        editor.geometry("700x600")
        editor.transient(self.root)
        editor.grab_set()
        editor.configure(bg=theme.WINDOW_BG)
        
        # Header
        tk.Label(
            editor, text="End of Day Summary",
            font=theme.FONT_H2, bg=theme.WINDOW_BG, fg=theme.TEXT,
        ).pack(pady=10)
        
        # Tickets section
        if tickets:
            ticket_frame = tk.Frame(editor, bg=theme.WINDOW_BG)
            ticket_frame.pack(fill='x', padx=10, pady=5)
            tk.Label(
                ticket_frame, text="Tickets Worked On:",
                font=theme.FONT_BODY_BOLD, bg=theme.WINDOW_BG, fg=theme.TEXT,
            ).pack(anchor='w')
            tk.Label(
                ticket_frame, text=", ".join(tickets),
                font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
                wraplength=650, justify='left',
            ).pack(anchor='w', padx=20)
        
        # Instructions
        tk.Label(
            editor, text="Review and edit the summary below:",
            font=theme.FONT_BODY, bg=theme.WINDOW_BG, fg=theme.MUTED,
        ).pack(pady=5)
        
        # Text editor with scrollbar
        text_frame = tk.Frame(editor, bg=theme.WINDOW_BG)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_editor = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD,
            font=theme.FONT_MONO,
            bg=theme.INPUT_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT,
        )
        text_editor.pack(fill='both', expand=True)
        text_editor.insert('1.0', summary_text)
        
        # Result variable to capture the edited summary
        result = {'summary': None, 'saved': False}
        
        def on_save():
            result['summary'] = text_editor.get('1.0', 'end-1c')
            result['saved'] = True
            editor.destroy()
        
        def on_cancel():
            result['saved'] = False
            editor.destroy()
        
        # Buttons
        button_frame = tk.Frame(editor, bg=theme.WINDOW_BG)
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame, text="Save Summary", command=on_save,
            bg=theme.GREEN, fg=theme.WINDOW_BG,
            font=theme.FONT_BODY, width=15, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)
        tk.Button(
            button_frame, text="Cancel", command=on_cancel,
            bg=theme.SURFACE_BG, fg=theme.TEXT,
            font=theme.FONT_BODY, width=15, relief='flat', cursor='hand2',
        ).pack(side='left', padx=5)
        
        # Wait for the window to close
        self.root.wait_window(editor)
        
        return result
 
    def start_tracking(self):
        # Log start of day
        start_time = datetime.datetime.now()
        self.session_start_time = start_time  # Track session start
        self.log_day_marker(start_time, "DAY STARTED")
        
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_add_task.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        self.next_checkin_time = start_time + datetime.timedelta(
            minutes=self.settings_manager.get("checkin_interval_minutes"))
        
        self.status_label.config(text=f"Day started - Add your first task")
        
        # Start countdown timer
        self.update_countdown()
        
        self.hour_start_time = start_time
        self.hourly_tasks = []
        
        self.status_label.config(text=f"Day started - Add your first task")
        
        # Add first task
        self.add_task()

        # Timer using configured interval
        interval_ms = self.settings_manager.get("checkin_interval_minutes") * 60 * 1000
        self.timer_id = self.root.after(interval_ms, self.hourly_checkin)
    
    def add_task(self):
        """Add and immediately save a task"""
        if not self.is_running:
            return
        
        details = self.ask_task_details()
        if not details:
            return
        
        task_time = datetime.datetime.now()
        details['timestamp'] = task_time
        details['system_info'] = self.get_system_context()
        
        # Calculate duration from last task or hour start
        if self.hourly_tasks:
            last_task_time = self.hourly_tasks[-1]['timestamp']
            duration = (task_time - last_task_time).total_seconds() / 60
        elif self.hour_start_time is not None:
            duration = (task_time - self.hour_start_time).total_seconds() / 60
        else:
            duration = 0
        
        details['duration'] = duration
        
        # Save to list for hourly summary
        self.hourly_tasks.append(details)
        
        self.status_label.config(text=f"Logging: {details['title']}...")
        
        # Save immediately in background thread
        threading.Thread(target=self.save_task_immediately, args=(details, task_time, duration)).start()
        
        self.status_label.config(text=f"Tracking: {len(self.hourly_tasks)} task(s) this hour")
    
    def save_task_immediately(self, task_details, task_time, duration):
        """Save a single task immediately with LLM summary"""
        # Generate AI summary for this task
        ai_summary = self.generate_ai_markdown(task_details, round(duration, 2))
        
        # Parse tickets
        tickets_raw = task_details.get('ticket', '')
        tickets = [t.strip() for t in tickets_raw.split(',') if t.strip()]
        if not tickets:
            tickets = ['']

        # resolved may be a per-ticket dict (new format) or a bool (legacy)
        resolved_info = task_details.get('resolved', False)

        # Write each ticket row immediately using repository
        for ticket in tickets:
            if isinstance(resolved_info, dict):
                resolved = "Yes" if resolved_info.get(ticket, False) else "No"
            else:
                resolved = "Yes" if resolved_info else "No"

            task_data = {
                'start_time': task_time.strftime("%Y-%m-%d %H:%M:%S"),
                'end_time': task_time.strftime("%Y-%m-%d %H:%M:%S"),
                'duration': round(duration, 2),
                'ticket': ticket,
                'title': task_details.get('title'),
                'system_info': task_details.get('system_info'),
                'ai_summary': ai_summary,
                'resolved': resolved
            }
            
            if self.data_repository.log_task(task_data):
                print(f"Task logged: {task_data}")
            else:
                print(f"Failed to log task: {task_data}")
 
    def hourly_checkin(self):
        if not self.is_running: return

        end_time = datetime.datetime.now()
        
        # Generate hourly summary in background
        threading.Thread(target=self.save_hourly_summary, args=(end_time,)).start()
 
        self.root.deiconify()
        messagebox.showinfo("Hourly Check-in", f"Hour complete! {len(self.hourly_tasks)} task(s) logged. Add your next task.")
        self.next_checkin_time = end_time + datetime.timedelta(
            minutes=self.settings_manager.get("checkin_interval_minutes"))
        
        # Reset for next hour
        self.hour_start_time = end_time
        self.hourly_tasks = []
        
        self.status_label.config(text=f"New hour started - Add a task")
        
        # Prompt for first task of new hour
        self.add_task()
        
        # Restart timer
        interval_ms = self.settings_manager.get("checkin_interval_minutes") * 60 * 1000
        self.timer_id = self.root.after(interval_ms, self.hourly_checkin)
    
    def save_hourly_summary(self, end_time):
        """Generate and save a summary of all tasks from the hour"""
        if not self.hourly_tasks or self.hour_start_time is None:
            return
        
        # Generate summary
        hourly_summary = self.generate_hourly_summary(self.hourly_tasks)
        
        # Calculate total duration
        total_duration = sum(task.get('duration', 0) for task in self.hourly_tasks)
        
        # Collect all ticket numbers
        all_tickets = []
        for task in self.hourly_tasks:
            tickets_raw = task.get('ticket', '')
            tickets = [t.strip() for t in tickets_raw.split(',') if t.strip()]
            all_tickets.extend(tickets)
        
        ticket_summary = ", ".join(all_tickets) if all_tickets else "Multiple"
        
        # Log the hourly summary using repository
        task_data = {
            'start_time': self.hour_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': round(total_duration, 2),
            'ticket': ticket_summary,
            'title': f"HOURLY SUMMARY ({len(self.hourly_tasks)} tasks)",
            'system_info': self.get_system_context(),
            'ai_summary': hourly_summary,
            'resolved': ""
        }
        
        if self.data_repository.log_task(task_data):
            print(f"Hourly summary logged")
        else:
            print(f"Failed to log hourly summary")
 
    def stop_tracking(self):
        if self.is_running:
            end_time = datetime.datetime.now()
            
            self.status_label.config(text="Stopping & Generating AI Log...")
            
            # Use thread to prevent freeze on exit
            threading.Thread(target=self.stop_tracking_thread, args=(end_time,)).start()
 
    def stop_tracking_thread(self, end_time):
        """Helper to run log generation in background then update UI"""
        # Generate final hourly summary if there are tasks
        if self.hourly_tasks:
            self.save_hourly_summary(end_time)
        
        # Generate end-of-day summary
        if self.session_start_time:
            self.status_label.config(text="Generating end-of-day summary...")
            
            # Read all summaries from today's session
            day_data = self.read_todays_summaries(self.session_start_time)
            
            # Generate comprehensive summary
            day_summary = self.generate_day_summary(day_data)
            
            # Schedule showing the editor on main thread
            self.root.after(0, lambda: self.show_summary_and_finish(day_summary, day_data['tickets'], end_time))
        else:
            # No session start time, just finish normally
            self.log_day_marker(end_time, "DAY ENDED")
            self.root.after(0, self.finalize_stop_ui)
    
    def show_summary_and_finish(self, day_summary, tickets, end_time):
        """Show the summary editor and save if user confirms"""
        # Show editor dialog
        result = self.show_summary_editor(day_summary, tickets)
        
        if result['saved'] and result['summary']:
            # Save the edited summary to CSV
            self.save_day_summary(result['summary'], tickets, end_time)
        
        # Log end of day marker
        self.log_day_marker(end_time, "DAY ENDED")
        
        # Finalize UI
        self.finalize_stop_ui()
    
    def save_day_summary(self, summary, tickets, end_time):
        """Save the end-of-day summary to the CSV file and optionally to a standalone file."""
        ticket_list = ", ".join(tickets) if tickets else "All"
        
        task_data = {
            'start_time': self.session_start_time.strftime("%Y-%m-%d %H:%M:%S") if self.session_start_time else "",
            'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 0,  # Duration not applicable for day summary
            'ticket': ticket_list,
            'title': "END OF DAY SUMMARY",
            'system_info': self.get_system_context(),
            'ai_summary': summary,
            'resolved': ""
        }
        
        if self.data_repository.log_task(task_data):
            print(f"Day summary saved: {len(summary)} characters")
        else:
            print(f"Error saving day summary")

        # Optionally save as a standalone Markdown file
        if self.settings_manager.get("summary_save_to_file"):
            summary_path = self.settings_manager.get_summary_file_path()
            try:
                parent_dir = os.path.dirname(summary_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Daily Summary — {end_time.strftime('%Y-%m-%d')}\n\n")
                    if tickets:
                        f.write(f"**Tickets:** {ticket_list}\n\n")
                    f.write("---\n\n")
                    f.write(summary)
                    f.write("\n")
                print(f"Standalone summary saved to: {summary_path}")
            except Exception as e:
                print(f"Error saving standalone summary: {e}")
 
    def finalize_stop_ui(self):
        self.is_running = False

        if self.countdown_id:
            self.root.after_cancel(self.countdown_id)
        
        self.countdown_label.config(text="")
        self.status_label.config(text="Stopped")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_add_task.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        messagebox.showinfo("Done", "Tracking stopped and saved.")
    
    def update_countdown(self):
        """Update the countdown timer display"""
        if not self.is_running or not self.next_checkin_time:
            return
        
        now = datetime.datetime.now()
        time_remaining = self.next_checkin_time - now
        
        if time_remaining.total_seconds() <= 0:
            self.countdown_label.config(text="Check-in time!")
        else:
            minutes, seconds = divmod(int(time_remaining.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                countdown_text = f"Next check-in in: {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                countdown_text = f"Next check-in in: {minutes:02d}:{seconds:02d}"
            
            self.countdown_label.config(text=countdown_text)
        
        # Schedule next update in 1 second
        self.countdown_id = self.root.after(1000, self.update_countdown)
 
    def log_day_marker(self, timestamp, marker_text):
        """Log a special row for day start/end"""
        task_data = {
            'start_time': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'duration': 0,
            'ticket': "",
            'title': marker_text,
            'system_info': self.get_system_context(),
            'ai_summary': "",
            'resolved': ""
        }
        
        if self.data_repository.log_task(task_data):
            print(f"Day marker logged: {marker_text}")
        else:
            print(f"Failed to log day marker: {marker_text}")
 
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkLoggerApp(root)
    root.mainloop()
