"""
CSV-based implementation of the data repository.
"""
import csv
import glob as _glob
import os
import datetime
from typing import List, Dict, Optional, Tuple
from data_repository import DataRepository
from settings_manager import SettingsManager, DATE_FORMAT_MAP

# Separator used to encode the source file path inside a task_id string.
# The null character cannot appear in file-system paths on any supported OS.
_TASK_ID_SEP = "\x00"


class CSVDataRepository(DataRepository):
    """CSV file-based data repository.

    The repository is initialised with a :class:`SettingsManager` so that it
    can resolve the correct CSV file path for any given date.  Write
    operations (``initialize``, ``log_task``) always target *today's* file,
    while read operations derive the path from the requested date using the
    configured directory, base name and date-format settings.
    """

    def __init__(self, settings_manager: SettingsManager):
        """
        Initialize CSV repository.

        Args:
            settings_manager: Application settings manager used to resolve
                              file paths and configuration.
        """
        self.settings_manager = settings_manager
        self.headers = [
            "Start Time", "End Time", "Duration (Min)",
            "Ticket", "Title", "System Info", "AI Summary", "Resolved",
        ]

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_file_path_for_date(self, date: datetime.date) -> str:
        """Build the CSV file path for a specific date using settings."""
        directory = self.settings_manager.get("log_file_directory", ".")
        name = self.settings_manager.get("log_file_name", "work_log")
        date_format = self.settings_manager.get("log_file_date_format", "")

        if date_format and date_format in DATE_FORMAT_MAP:
            py_fmt = DATE_FORMAT_MAP[date_format]
            date_str = date.strftime(py_fmt)
            filename = f"{name}_{date_str}.csv"
        else:
            filename = f"{name}.csv"

        return os.path.join(directory, filename)

    def _get_today_file_path(self) -> str:
        """Return the CSV file path for today."""
        return self._get_file_path_for_date(datetime.date.today())

    def _get_all_log_file_paths(self) -> List[str]:
        """Return paths for all existing CSV log files in the configured directory.

        In single-file mode (no date format) this is just the one file.
        In multi-file mode the directory is scanned with a glob pattern that
        matches ``{name}_*.csv``.
        """
        directory = self.settings_manager.get("log_file_directory", ".")
        name = self.settings_manager.get("log_file_name", "work_log")
        date_format = self.settings_manager.get("log_file_date_format", "")

        if not date_format:
            return [os.path.join(directory, f"{name}.csv")]

        pattern = os.path.join(directory, f"{name}_*.csv")
        return sorted(_glob.glob(pattern))

    def _get_log_file_paths_for_date_range(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[str]:
        """Return file paths for every date from *start_date* to *end_date* (inclusive).

        Duplicate paths (which occur when no date format is configured) are
        removed while preserving order.
        """
        date_format = self.settings_manager.get("log_file_date_format", "")

        if not date_format:
            # Single-file mode — the same file covers all dates.
            return [self._get_file_path_for_date(start_date)]

        paths: List[str] = []
        seen: set = set()
        current = start_date
        while current <= end_date:
            path = self._get_file_path_for_date(current)
            if path not in seen:
                paths.append(path)
                seen.add(path)
            current += datetime.timedelta(days=1)
        return paths

    @staticmethod
    def _encode_task_id(file_path: str, row_idx: int) -> str:
        """Encode a file path and row index into a single task_id string."""
        return f"{file_path}{_TASK_ID_SEP}{row_idx}"

    @staticmethod
    def _decode_task_id(task_id: str) -> Tuple[Optional[str], int]:
        """Decode a task_id into (file_path, row_idx).

        Returns a ``(Optional[str], int)`` tuple.  If the task_id uses the
        legacy bare-integer format, ``file_path`` is ``None`` and the caller
        must supply the file path externally.
        """
        if _TASK_ID_SEP in task_id:
            file_path, row_str = task_id.rsplit(_TASK_ID_SEP, 1)
            return file_path, int(row_str)
        return None, int(task_id)

    # ── Public interface ──────────────────────────────────────────────────────

    def initialize(self):
        """Create today's CSV file with headers if it doesn't exist."""
        file_path = self._get_today_file_path()
        if not os.path.exists(file_path):
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.headers)

    def log_task(self, task_data: Dict) -> bool:
        """
        Log a single task entry to today's CSV file.

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
                task_data.get('resolved', 'No'),
            ]

            with open(self._get_today_file_path(), mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(row)
                file.flush()

            return True
        except Exception as e:
            print(f"Error logging task to CSV: {e}")
            return False

    def get_tasks_by_date(self, date: datetime.date) -> List[Dict]:
        """
        Get all tasks for a specific date from the corresponding CSV file.

        When a date-format is configured each day has its own file, so the
        correct file is derived from *date* via the settings.  In single-file
        mode the one shared file is read and filtered by date as before.

        Args:
            date: The date to retrieve tasks for

        Returns:
            List of task dictionaries
        """
        tasks = []
        file_path = self._get_file_path_for_date(date)

        try:
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    start_time_str = row.get('Start Time', '')
                    if not start_time_str:
                        continue

                    try:
                        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        if start_time.date() == date:
                            row['task_id'] = self._encode_task_id(file_path, idx + 1)
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

        Searches across all CSV files that cover the period from
        *start_time* to today.

        Args:
            start_time: The datetime to start from

        Returns:
            List of task dictionaries
        """
        tasks = []
        today = datetime.date.today()
        file_paths = self._get_log_file_paths_for_date_range(start_time.date(), today)

        for file_path in file_paths:
            try:
                with open(file_path, mode='r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for idx, row in enumerate(reader):
                        start_time_str = row.get('Start Time', '')
                        if not start_time_str:
                            continue

                        try:
                            row_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                            if row_time >= start_time:
                                row['task_id'] = self._encode_task_id(file_path, idx + 1)
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
        Update the resolved status of a task in the correct CSV file.

        The *task_id* encodes both the source file path and the 1-based row
        index (separated by a null character), as produced by the ``get_*``
        methods.  This allows tasks from historical date-named files to be
        updated correctly.

        Args:
            task_id: Encoded as ``"{file_path}\\x00{row_index}"``
            resolved: ``"Yes"`` or ``"No"``

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path, row_idx = self._decode_task_id(task_id)
            if file_path is None:
                # Bare integer — fall back to today's file (legacy safety net)
                file_path = self._get_today_file_path()

            rows = []
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)

            if 0 < row_idx < len(rows):
                rows[row_idx][7] = resolved

                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)

                return True
            else:
                print(f"Invalid task_id: {task_id}")
                return False

        except Exception as e:
            print(f"Error updating task resolved status: {e}")
            return False

    def search_tasks(self, keyword: str, start_date: Optional[datetime.date] = None,
                     end_date: Optional[datetime.date] = None) -> List[Dict]:
        """
        Search tasks by keyword in title or AI summary, optionally within a date range.

        Searches across all relevant CSV files: when a date range is supplied
        only files that could contain matching dates are read; otherwise every
        log file in the configured directory is scanned.

        Args:
            keyword: Case-insensitive substring to match against Title and AI Summary.
            start_date: If provided, only include tasks on or after this date.
            end_date: If provided, only include tasks on or before this date.

        Returns:
            List of matching task dictionaries, oldest first.
        """
        results = []
        needle = keyword.lower()

        if start_date is not None and end_date is not None:
            file_paths = self._get_log_file_paths_for_date_range(start_date, end_date)
        elif start_date is not None:
            file_paths = self._get_log_file_paths_for_date_range(start_date, datetime.date.today())
        else:
            # end_date only or no date filter — scan all available files
            file_paths = self._get_all_log_file_paths()

        for file_path in file_paths:
            try:
                with open(file_path, mode='r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for idx, row in enumerate(reader):
                        start_time_str = row.get('Start Time', '')
                        if not start_time_str:
                            continue

                        try:
                            row_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            continue

                        row_date = row_dt.date()
                        if start_date and row_date < start_date:
                            continue
                        if end_date and row_date > end_date:
                            continue

                        title = row.get('Title', '')
                        summary = row.get('AI Summary', '')
                        if needle in title.lower() or needle in summary.lower():
                            row['task_id'] = self._encode_task_id(file_path, idx + 1)
                            row['start_time_obj'] = row_dt
                            results.append(row)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error searching tasks in CSV: {e}")

        return results

    def get_all_tasks(self) -> List[Dict]:
        """
        Get all tasks from all CSV log files in the configured directory.

        Returns:
            List of task dictionaries
        """
        tasks = []

        for file_path in self._get_all_log_file_paths():
            try:
                with open(file_path, mode='r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for idx, row in enumerate(reader):
                        row['task_id'] = self._encode_task_id(file_path, idx + 1)

                        start_time_str = row.get('Start Time', '')
                        if start_time_str:
                            try:
                                row['start_time_obj'] = datetime.datetime.strptime(
                                    start_time_str, "%Y-%m-%d %H:%M:%S"
                                )
                            except ValueError:
                                pass

                        tasks.append(row)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error reading all tasks from CSV: {e}")

        return tasks
