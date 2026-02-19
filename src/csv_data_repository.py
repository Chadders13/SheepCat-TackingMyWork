"""
CSV-based implementation of the data repository.
"""
import csv
import os
import datetime
from typing import List, Dict, Optional
from data_repository import DataRepository


class CSVDataRepository(DataRepository):
    """CSV file-based data repository"""
    
    def __init__(self, csv_file_path: str):
        """
        Initialize CSV repository.
        
        Args:
            csv_file_path: Path to the CSV file
        """
        self.csv_file_path = csv_file_path
        self.headers = ["Start Time", "End Time", "Duration (Min)", "Ticket", "Title", "System Info", "AI Summary", "Resolved"]
    
    def initialize(self):
        """Create the CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.headers)
    
    def log_task(self, task_data: Dict) -> bool:
        """
        Log a single task entry to CSV.
        
        Args:
            task_data: Dictionary containing task information
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            row = [
                task_data.get('start_time', ''),
                task_data.get('end_time', ''),
                task_data.get('duration', 0),
                task_data.get('ticket', ''),
                task_data.get('title', ''),
                task_data.get('system_info', ''),
                task_data.get('ai_summary', ''),
                task_data.get('resolved', 'No')
            ]
            
            with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(row)
                file.flush()
            
            return True
        except Exception as e:
            print(f"Error logging task to CSV: {e}")
            return False
    
    def get_tasks_by_date(self, date: datetime.date) -> List[Dict]:
        """
        Get all tasks for a specific date.
        
        Args:
            date: The date to retrieve tasks for
        
        Returns:
            List of task dictionaries
        """
        tasks = []
        
        try:
            with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    start_time_str = row.get('Start Time', '')
                    if not start_time_str:
                        continue
                    
                    try:
                        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        if start_time.date() == date:
                            # Add row index as task_id for updates
                            row['task_id'] = str(idx + 1)  # +1 to account for header row
                            row['start_time_obj'] = start_time
                            tasks.append(row)
                    except ValueError:
                        continue
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading tasks from CSV: {e}")
        
        return tasks
    
    def get_tasks_since(self, start_time: datetime.datetime) -> List[Dict]:
        """
        Get all tasks since a specific datetime.
        
        Args:
            start_time: The datetime to start from
        
        Returns:
            List of task dictionaries
        """
        tasks = []
        
        try:
            with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    start_time_str = row.get('Start Time', '')
                    if not start_time_str:
                        continue
                    
                    try:
                        row_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        if row_time >= start_time:
                            row['task_id'] = str(idx + 1)
                            row['start_time_obj'] = row_time
                            tasks.append(row)
                    except ValueError:
                        continue
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading tasks from CSV: {e}")
        
        return tasks
    
    def update_task_resolved_status(self, task_id: str, resolved: str) -> bool:
        """
        Update the resolved status of a task in CSV.
        
        Note: For CSV, we need to read all rows, update the specific one, and write back.
        task_id is the row index (1-based, excluding header).
        
        Args:
            task_id: Row index as string
            resolved: "Yes" or "No"
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read all rows
            rows = []
            with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
            
            # Update the specific row (convert task_id to int and account for header)
            row_idx = int(task_id)
            if 0 < row_idx < len(rows):
                # Resolved is the last column (index 7)
                rows[row_idx][7] = resolved
                
                # Write back all rows
                with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
                
                return True
            else:
                print(f"Invalid task_id: {task_id}")
                return False
                
        except Exception as e:
            print(f"Error updating task resolved status: {e}")
            return False
    
    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks in the CSV file.
        
        Returns:
            List of task dictionaries
        """
        tasks = []
        
        try:
            with open(self.csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    row['task_id'] = str(idx + 1)
                    
                    # Parse start time if available
                    start_time_str = row.get('Start Time', '')
                    if start_time_str:
                        try:
                            row['start_time_obj'] = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass
                    
                    tasks.append(row)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading all tasks from CSV: {e}")
        
        return tasks
