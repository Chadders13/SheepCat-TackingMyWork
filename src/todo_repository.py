"""
CSV-based repository for personal todo items.
"""
import csv
import os
import datetime
from typing import List, Dict


class TodoRepository:
    """CSV file-based repository for personal todo items."""

    HEADERS = ["ID", "Task", "Priority", "Status", "Created", "Notes"]

    def __init__(self, csv_file_path: str):
        """
        Initialize the Todo repository.

        Args:
            csv_file_path: Path to the todo CSV file
        """
        self.csv_file_path = csv_file_path

    def initialize(self):
        """Create the CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(self.HEADERS)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _read_rows(self) -> List[List[str]]:
        """Return all raw rows (including header) from the CSV file."""
        if not os.path.exists(self.csv_file_path):
            return [list(self.HEADERS)]
        with open(self.csv_file_path, mode='r', encoding='utf-8') as f:
            return list(csv.reader(f))

    def _write_rows(self, rows: List[List[str]]):
        """Write all rows back to the CSV file."""
        with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows(rows)

    def _next_id(self, rows: List[List[str]]) -> str:
        """Return the next available integer ID as a string."""
        ids = []
        for row in rows[1:]:  # skip header
            if row:
                try:
                    ids.append(int(row[0]))
                except ValueError:
                    pass
        return str(max(ids) + 1) if ids else "1"

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_todo(self, task: str, priority: str = "Medium", notes: str = "") -> bool:
        """
        Add a new todo item.

        Args:
            task: Description of the task
            priority: Priority level ("High", "Medium", or "Low")
            notes: Optional extra notes

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            rows = self._read_rows()
            todo_id = self._next_id(rows)
            created = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [todo_id, task, priority, "Pending", created, notes]
            with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(new_row)
            return True
        except Exception as e:
            print(f"Error adding todo: {e}")
            return False

    def get_all_todos(self) -> List[Dict]:
        """
        Get all todo items.

        Returns:
            List of todo dictionaries
        """
        todos = []
        try:
            with open(self.csv_file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    todos.append(dict(row))
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading todos: {e}")
        return todos

    def update_todo_status(self, todo_id: str, status: str) -> bool:
        """
        Update the status of a todo item.

        Args:
            todo_id: The ID of the todo item
            status: New status ("Pending" or "Done")

        Returns:
            bool: True if found and updated, False otherwise
        """
        try:
            rows = self._read_rows()
            updated = False
            for i, row in enumerate(rows):
                if i == 0:
                    continue  # skip header
                if row and row[0] == todo_id:
                    rows[i][3] = status  # Status is column index 3
                    updated = True
                    break
            if updated:
                self._write_rows(rows)
            return updated
        except Exception as e:
            print(f"Error updating todo status: {e}")
            return False

    def delete_todo(self, todo_id: str) -> bool:
        """
        Delete a todo item by ID.

        Args:
            todo_id: The ID of the todo item to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            rows = self._read_rows()
            new_rows = [rows[0]] + [r for r in rows[1:] if r and r[0] != todo_id]
            self._write_rows(new_rows)
            return True
        except Exception as e:
            print(f"Error deleting todo: {e}")
            return False
