import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import csv
import datetime
import os
import platform
import requests
import json
import threading
 
# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/generate"
# Swap this to "nordic-text" or "deepseek-coder" etc. as per your ollama list
OLLAMA_MODEL = "deepseek-r1:8b"
LOG_FILE = "work_log.csv"
LLM_REQUEST_TIMEOUT = 1000  # Timeout for LLM API requests in seconds
MAX_CHUNK_SIZE = 4000  # Maximum characters per chunk for LLM processing
# ---------------------
 
class WorkLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("M Work - Task tracker")
        self.root.geometry("400x280")
        
        # State variables
        self.is_running = False
        self.hourly_tasks = []  # Track tasks for the current hour
        self.hour_start_time = None
        self.session_start_time = None  # Track when the day started
        self.timer_id = None
        self.countdown_id = None
        self.next_checkin_time = None
 
        # UI Elements
        self.status_label = tk.Label(root, text="Ready to track", font=("Arial", 12))
        self.status_label.pack(pady=20)
 
        self.countdown_label = tk.Label(root, text="", font=("Arial", 10, "bold"), fg="blue")
        self.countdown_label.pack(pady=5)
 
        self.info_label = tk.Label(root, text=f"Model: {OLLAMA_MODEL}", font=("Arial", 8), fg="gray")
        self.info_label.pack(pady=0)
 
        self.btn_start = tk.Button(root, text="Start Day", command=self.start_tracking, bg="green", fg="white", width=20)
        self.btn_start.pack(pady=5)
 
        self.btn_add_task = tk.Button(root, text="Add Task", command=self.add_task, bg="blue", fg="white", state=tk.DISABLED, width=20)
        self.btn_add_task.pack(pady=5)
 
        self.btn_stop = tk.Button(root, text="Stop / End Day", command=self.stop_tracking, bg="red", fg="white", state=tk.DISABLED, width=20)
        self.btn_stop.pack(pady=5)
 
        # Initialize CSV
        self.init_csv()
 
    def init_csv(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Added 'AI Summary' and 'Resolved' columns
                writer.writerow(["Start Time", "End Time", "Duration (Min)", "Ticket", "Title", "System Info", "AI Summary", "Resolved"])
 
    def get_system_context(self):
        return f"OS: {platform.system()} | Node: {platform.node()}"
 
    def ask_task_details(self):
        title = simpledialog.askstring("Input", "What are you working on? (Title)")
        if title is None: return None
        ticket = simpledialog.askstring("Input", "Ticket ID(s) / Reference(s) (comma-separated for multiple):")
        
        # Ask if resolved
        resolved_dialog = tk.Toplevel(self.root)
        resolved_dialog.title("Task Status")
        resolved_dialog.geometry("300x150")
        resolved_dialog.transient(self.root)
        resolved_dialog.grab_set()
        
        tk.Label(resolved_dialog, text="Was this task/ticket resolved?", font=("Arial", 10)).pack(pady=20)
        
        resolved_var = tk.BooleanVar(value=False)
        tk.Checkbutton(resolved_dialog, text="Mark as Resolved", variable=resolved_var, font=("Arial", 10)).pack(pady=10)
        
        result = {"resolved": False}
        
        def on_ok():
            result["resolved"] = resolved_var.get()
            resolved_dialog.destroy()
        
        tk.Button(resolved_dialog, text="OK", command=on_ok, bg="green", fg="white", width=10).pack(pady=10)
        
        self.root.wait_window(resolved_dialog)
        
        return {"title": title, "ticket": ticket, "resolved": result["resolved"]}
 
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
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
 
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=LLM_REQUEST_TIMEOUT)
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
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=LLM_REQUEST_TIMEOUT)
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
        
        try:
            with open(LOG_FILE, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    row_time_str = row.get('Start Time', '')
                    if not row_time_str:
                        continue
                    
                    try:
                        row_time = datetime.datetime.strptime(row_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    
                    # Only include rows from today's session (after start_time)
                    if row_time >= start_time:
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
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading summaries: {e}")
        
        return {
            'summaries': summaries,
            'tickets': sorted(list(tickets)),
            'tasks': tasks
        }
    
    def chunk_text(self, text, max_chars=MAX_CHUNK_SIZE):
        """
        Split text into chunks for LLM processing.
        Tries to split at sentence boundaries when possible.
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            # Add period back if it was removed
            if not sentence.endswith('.'):
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
        chunks = self.chunk_text(content, max_chars=MAX_CHUNK_SIZE)
        
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
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=LLM_REQUEST_TIMEOUT)
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
        
        # Header
        tk.Label(editor, text="End of Day Summary", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Tickets section
        if tickets:
            ticket_frame = tk.Frame(editor)
            ticket_frame.pack(fill='x', padx=10, pady=5)
            tk.Label(ticket_frame, text="Tickets Worked On:", font=("Arial", 10, "bold")).pack(anchor='w')
            tk.Label(ticket_frame, text=", ".join(tickets), font=("Arial", 9), wraplength=650, justify='left').pack(anchor='w', padx=20)
        
        # Instructions
        tk.Label(editor, text="Review and edit the summary below:", font=("Arial", 10)).pack(pady=5)
        
        # Text editor with scrollbar
        text_frame = tk.Frame(editor)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_editor = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Arial", 10))
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
        button_frame = tk.Frame(editor)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save Summary", command=on_save, bg="green", fg="white", width=15).pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", command=on_cancel, bg="gray", fg="white", width=15).pack(side='left', padx=5)
        
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
        self.next_checkin_time = start_time + datetime.timedelta(hours=1)
        
        self.status_label.config(text=f"Day started - Add your first task")
        
        # Start countdown timer
        self.update_countdown()
        
        self.hour_start_time = start_time
        self.hourly_tasks = []
        
        self.status_label.config(text=f"Day started - Add your first task")
        
        # Add first task
        self.add_task()

        # 1 Hour Timer (3600000 ms)
        self.timer_id = self.root.after(3600000, self.hourly_checkin)
    
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
        
        resolved = "Yes" if task_details.get('resolved', False) else "No"

        # Write each ticket row immediately
        for ticket in tickets:
            row = [
                task_time.strftime("%Y-%m-%d %H:%M:%S"),
                task_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(duration, 2),
                ticket,
                task_details.get('title'),
                task_details.get('system_info'),
                ai_summary,
                resolved
            ]
            try:
                with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(row)
                    file.flush()
                    print(f"Task logged: {row}")
            except Exception as e:
                print(f"CSV Error: {e}")
 
    def hourly_checkin(self):
        if not self.is_running: return

        end_time = datetime.datetime.now()
        
        # Generate hourly summary in background
        threading.Thread(target=self.save_hourly_summary, args=(end_time,)).start()
 
        self.root.deiconify()
        messagebox.showinfo("Hourly Check-in", f"Hour complete! {len(self.hourly_tasks)} task(s) logged. Add your next task.")
        self.next_checkin_time = end_time + datetime.timedelta(hours=1)
        
        # Reset for next hour
        self.hour_start_time = end_time
        self.hourly_tasks = []
        
        self.status_label.config(text=f"New hour started - Add a task")
        
        # Prompt for first task of new hour
        self.add_task()
        
        # Restart timer
        self.timer_id = self.root.after(3600000, self.hourly_checkin)
    
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
        
        # Log the hourly summary
        row = [
            self.hour_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            round(total_duration, 2),
            ticket_summary,
            f"HOURLY SUMMARY ({len(self.hourly_tasks)} tasks)",
            self.get_system_context(),
            hourly_summary,
            ""  # Resolved column
        ]
        
        try:
            with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(row)
                file.flush()
                print(f"Hourly summary logged: {row}")
        except Exception as e:
            print(f"CSV Error: {e}")
 
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
        """Save the end-of-day summary to the CSV file"""
        ticket_list = ", ".join(tickets) if tickets else "All"
        
        row = [
            self.session_start_time.strftime("%Y-%m-%d %H:%M:%S") if self.session_start_time else "",
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            0,  # Duration not applicable for day summary
            ticket_list,
            "END OF DAY SUMMARY",
            self.get_system_context(),
            summary,
            ""  # Resolved column
        ]
        
        try:
            with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(row)
                file.flush()
                print(f"Day summary saved: {len(summary)} characters")
        except Exception as e:
            print(f"Error saving day summary: {e}")
 
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
        try:
            with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                row = [
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    0,
                    "",
                    marker_text,
                    self.get_system_context(),
                    "",
                    ""  # Resolved column
                ]
                writer.writerow(row)
                file.flush()  # Ensure immediate save
                print(f"Day marker logged: {marker_text}")
        except Exception as e:
            print(f"CSV Error: {e}")
 
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkLoggerApp(root)
    root.mainloop()
