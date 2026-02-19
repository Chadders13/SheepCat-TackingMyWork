import tkinter as tk
from tkinter import simpledialog, messagebox
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
            response = requests.post(OLLAMA_URL, json=payload, timeout=1000)
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
            response = requests.post(OLLAMA_URL, json=payload, timeout=1000)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"LLM Connection Failed: {str(e)}"
 
    def start_tracking(self):
        # Log start of day
        start_time = datetime.datetime.now()
        self.log_day_marker(start_time, "DAY STARTED")
        
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
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
                resolved,
                task_details.get('title'),
                task_details.get('system_info'),
                ai_summary
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
            hourly_summary
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
        
        # Log end of day
        self.log_day_marker(end_time, "DAY ENDED")
        
        # Schedule UI updates back on the main thread
        self.root.after(0, self.finalize_stop_ui)
 
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
                    ""
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
