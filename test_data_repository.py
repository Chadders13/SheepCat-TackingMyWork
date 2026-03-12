"""
Tests for the data repository implementations.
"""
import json
import os
import shutil
import sys
import tempfile
import datetime
import unittest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_data_repository import CSVDataRepository
from settings_manager import SettingsManager
from todo_repository import TodoRepository


def _make_settings_manager(temp_dir: str, date_format: str = "") -> SettingsManager:
    """Create a SettingsManager backed by a temp directory for testing."""
    settings_file = os.path.join(temp_dir, "test_settings.json")
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "log_file_directory": temp_dir,
                "log_file_name": "work_log",
                "log_file_date_format": date_format,
            },
            f,
        )
    return SettingsManager(settings_file)


class TestCSVDataRepository(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory and settings manager for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_manager = _make_settings_manager(self.temp_dir)
        # Derive the expected single-file path (no date format)
        self.csv_path = os.path.join(self.temp_dir, "work_log.csv")
        self.repo = CSVDataRepository(self.settings_manager)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialize_creates_file(self):
        """Test that initialize creates a CSV file with headers"""
        self.repo.initialize()
        self.assertTrue(os.path.exists(self.csv_path))
        
        # Check headers
        with open(self.csv_path, 'r') as f:
            headers = f.readline().strip()
            expected = "Start Time,End Time,Duration (Min),Ticket,Title,System Info,AI Summary,Resolved"
            self.assertEqual(headers, expected)
    
    def test_log_task(self):
        """Test logging a task"""
        self.repo.initialize()
        
        task_data = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-123',
            'title': 'Test Task',
            'system_info': 'Test System',
            'ai_summary': 'Task summary',
            'resolved': 'Yes'
        }
        
        result = self.repo.log_task(task_data)
        self.assertTrue(result)
        
        # Verify task was logged
        tasks = self.repo.get_all_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['Title'], 'Test Task')
        self.assertEqual(tasks[0]['Ticket'], 'TEST-123')
        self.assertEqual(tasks[0]['Resolved'], 'Yes')
    
    def test_get_tasks_by_date(self):
        """Test retrieving tasks by date"""
        self.repo.initialize()
        
        # Add tasks on different dates
        task1 = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-1',
            'title': 'Task 1',
            'system_info': 'Test',
            'ai_summary': 'Summary 1',
            'resolved': 'Yes'
        }
        
        task2 = {
            'start_time': '2024-01-16 11:00:00',
            'end_time': '2024-01-16 11:30:00',
            'duration': 30.0,
            'ticket': 'TEST-2',
            'title': 'Task 2',
            'system_info': 'Test',
            'ai_summary': 'Summary 2',
            'resolved': 'No'
        }
        
        self.repo.log_task(task1)
        self.repo.log_task(task2)
        
        # Get tasks for specific date
        date1 = datetime.date(2024, 1, 15)
        tasks_on_date1 = self.repo.get_tasks_by_date(date1)
        
        self.assertEqual(len(tasks_on_date1), 1)
        self.assertEqual(tasks_on_date1[0]['Title'], 'Task 1')
        
        date2 = datetime.date(2024, 1, 16)
        tasks_on_date2 = self.repo.get_tasks_by_date(date2)
        
        self.assertEqual(len(tasks_on_date2), 1)
        self.assertEqual(tasks_on_date2[0]['Title'], 'Task 2')
    
    def test_update_task_resolved_status(self):
        """Test updating the resolved status of a task"""
        self.repo.initialize()
        
        # Log a task
        task_data = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-123',
            'title': 'Test Task',
            'system_info': 'Test System',
            'ai_summary': 'Task summary',
            'resolved': 'No'
        }
        self.repo.log_task(task_data)
        
        # Get the task
        tasks = self.repo.get_all_tasks()
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0]['task_id']
        
        # Update status
        result = self.repo.update_task_resolved_status(task_id, 'Yes')
        self.assertTrue(result)
        
        # Verify update
        tasks = self.repo.get_all_tasks()
        self.assertEqual(tasks[0]['Resolved'], 'Yes')
    
    def test_get_tasks_since(self):
        """Test retrieving tasks since a specific datetime"""
        self.repo.initialize()
        
        # Add tasks at different times
        task1 = {
            'start_time': '2024-01-15 09:00:00',
            'end_time': '2024-01-15 09:30:00',
            'duration': 30.0,
            'ticket': 'TEST-1',
            'title': 'Task 1',
            'system_info': 'Test',
            'ai_summary': 'Summary 1',
            'resolved': 'Yes'
        }
        
        task2 = {
            'start_time': '2024-01-15 10:00:00',
            'end_time': '2024-01-15 10:30:00',
            'duration': 30.0,
            'ticket': 'TEST-2',
            'title': 'Task 2',
            'system_info': 'Test',
            'ai_summary': 'Summary 2',
            'resolved': 'No'
        }
        
        task3 = {
            'start_time': '2024-01-15 11:00:00',
            'end_time': '2024-01-15 11:30:00',
            'duration': 30.0,
            'ticket': 'TEST-3',
            'title': 'Task 3',
            'system_info': 'Test',
            'ai_summary': 'Summary 3',
            'resolved': 'Yes'
        }
        
        self.repo.log_task(task1)
        self.repo.log_task(task2)
        self.repo.log_task(task3)
        
        # Get tasks since 10:00
        since_time = datetime.datetime(2024, 1, 15, 10, 0, 0)
        tasks = self.repo.get_tasks_since(since_time)
        
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]['Title'], 'Task 2')
        self.assertEqual(tasks[1]['Title'], 'Task 3')

    def _make_marker(self, dt_str, title):
        return {
            'start_time': dt_str,
            'end_time': dt_str,
            'duration': 0,
            'ticket': '',
            'title': title,
            'system_info': 'Test',
            'ai_summary': '',
            'resolved': ''
        }

    def _find_unfinished_session(self, tasks):
        """Mirror of WorkLoggerApp.find_unfinished_session for unit-testing."""
        last_start_time = None
        for task in tasks:
            title = task.get('Title', '')
            if 'DAY STARTED' in title:
                last_start_time = task.get('start_time_obj')
            elif 'DAY ENDED' in title and last_start_time is not None:
                last_start_time = None
        return last_start_time

    def test_find_unfinished_session_detects_missing_end(self):
        """If DAY STARTED has no DAY ENDED, unfinished session is detected."""
        self.repo.initialize()
        today = datetime.date.today()
        dt_str = today.strftime('%Y-%m-%d') + ' 09:00:00'
        self.repo.log_task(self._make_marker(dt_str, 'DAY STARTED'))

        tasks = self.repo.get_tasks_by_date(today)
        result = self._find_unfinished_session(tasks)
        self.assertIsNotNone(result)
        self.assertEqual(result.date(), today)

    def test_find_unfinished_session_none_when_ended(self):
        """If DAY STARTED is followed by DAY ENDED, no unfinished session."""
        self.repo.initialize()
        today = datetime.date.today()
        dt_start = today.strftime('%Y-%m-%d') + ' 09:00:00'
        dt_end = today.strftime('%Y-%m-%d') + ' 17:00:00'
        self.repo.log_task(self._make_marker(dt_start, 'DAY STARTED'))
        self.repo.log_task(self._make_marker(dt_end, 'DAY ENDED'))

        tasks = self.repo.get_tasks_by_date(today)
        result = self._find_unfinished_session(tasks)
        self.assertIsNone(result)

    def test_find_unfinished_session_none_when_no_entries(self):
        """Empty log means no unfinished session."""
        self.repo.initialize()
        today = datetime.date.today()
        tasks = self.repo.get_tasks_by_date(today)
        result = self._find_unfinished_session(tasks)
        self.assertIsNone(result)

    def test_find_unfinished_session_last_session_takes_precedence(self):
        """When multiple sessions exist, only the last unclosed one is returned."""
        self.repo.initialize()
        today = datetime.date.today()
        base = today.strftime('%Y-%m-%d')
        # First session: properly ended
        self.repo.log_task(self._make_marker(base + ' 08:00:00', 'DAY STARTED'))
        self.repo.log_task(self._make_marker(base + ' 12:00:00', 'DAY ENDED'))
        # Second session: no end marker
        self.repo.log_task(self._make_marker(base + ' 13:00:00', 'DAY STARTED'))

        tasks = self.repo.get_tasks_by_date(today)
        result = self._find_unfinished_session(tasks)
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 13)

    # ── search_tasks tests ────────────────────────────────────────────────────

    def _log_sample_tasks(self):
        """Helper: log a set of varied tasks for search tests."""
        self.repo.initialize()
        tasks = [
            {
                'start_time': '2024-03-01 09:00:00',
                'end_time': '2024-03-01 09:30:00',
                'duration': 30,
                'ticket': 'PROJ-1',
                'title': 'Standup meeting',
                'system_info': '',
                'ai_summary': 'Team aligned on sprint goals.',
                'resolved': 'Yes',
            },
            {
                'start_time': '2024-03-01 10:00:00',
                'end_time': '2024-03-01 11:00:00',
                'duration': 60,
                'ticket': 'PROJ-2',
                'title': 'Bug fix in payment module',
                'system_info': '',
                'ai_summary': 'Resolved null-pointer in checkout flow.',
                'resolved': 'Yes',
            },
            {
                'start_time': '2024-03-02 14:00:00',
                'end_time': '2024-03-02 15:00:00',
                'duration': 60,
                'ticket': 'PROJ-3',
                'title': 'Code review for payment feature',
                'system_info': '',
                'ai_summary': 'Reviewed PR, left comments on error handling.',
                'resolved': 'No',
            },
            {
                'start_time': '2024-03-02 16:00:00',
                'end_time': '2024-03-02 16:30:00',
                'duration': 30,
                'ticket': '',
                'title': 'Daily standup notes',
                'system_info': '',
                'ai_summary': '',
                'resolved': 'No',
            },
        ]
        for t in tasks:
            self.repo.log_task(t)

    def test_search_tasks_by_title_keyword(self):
        """search_tasks finds entries whose title contains the keyword."""
        self._log_sample_tasks()
        results = self.repo.search_tasks('standup')
        titles = [r['Title'] for r in results]
        self.assertEqual(len(results), 2)
        self.assertIn('Standup meeting', titles)
        self.assertIn('Daily standup notes', titles)

    def test_search_tasks_by_summary_keyword(self):
        """search_tasks matches entries whose AI summary contains the keyword."""
        self._log_sample_tasks()
        results = self.repo.search_tasks('payment')
        # 'Bug fix in payment module' (title match) and
        # 'Code review for payment feature' (title match) should be found.
        # 'Resolved null-pointer in checkout flow.' (summary of PROJ-2) also
        # contains no 'payment' but title does — let's be precise.
        titles = [r['Title'] for r in results]
        self.assertIn('Bug fix in payment module', titles)
        self.assertIn('Code review for payment feature', titles)

    def test_search_tasks_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        self._log_sample_tasks()
        results_lower = self.repo.search_tasks('standup')
        results_upper = self.repo.search_tasks('STANDUP')
        self.assertEqual(len(results_lower), len(results_upper))

    def test_search_tasks_date_range_filter(self):
        """search_tasks respects start_date / end_date filters."""
        self._log_sample_tasks()
        start = datetime.date(2024, 3, 2)
        end = datetime.date(2024, 3, 2)
        results = self.repo.search_tasks('standup', start_date=start, end_date=end)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Title'], 'Daily standup notes')

    def test_search_tasks_no_match_returns_empty(self):
        """search_tasks returns an empty list when nothing matches."""
        self._log_sample_tasks()
        results = self.repo.search_tasks('zzznomatch')
        self.assertEqual(results, [])

    def test_search_tasks_summary_only_match(self):
        """Entries are returned when only the AI summary matches, not the title."""
        self._log_sample_tasks()
        # 'null-pointer' only appears in the AI summary of PROJ-2
        results = self.repo.search_tasks('null-pointer')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Ticket'], 'PROJ-2')

    def test_search_tasks_start_date_only(self):
        """Providing only start_date returns tasks from that date onwards."""
        self._log_sample_tasks()
        start = datetime.date(2024, 3, 2)
        results = self.repo.search_tasks('standup', start_date=start)
        self.assertEqual(len(results), 1)
        self.assertIn('2024-03-02', results[0]['Start Time'])

    def test_search_tasks_end_date_only(self):
        """Providing only end_date returns tasks up to and including that date."""
        self._log_sample_tasks()
        end = datetime.date(2024, 3, 1)
        results = self.repo.search_tasks('standup', end_date=end)
        self.assertEqual(len(results), 1)
        self.assertIn('2024-03-01', results[0]['Start Time'])


class TestCSVDataRepositoryMultiFile(unittest.TestCase):
    """Tests for CSVDataRepository when a date-based file naming scheme is used.

    Each day's work is stored in a separate file named
    ``work_log_{yyyyMMdd}.csv``.  Reads must resolve the correct file for the
    requested date; writes always target today's file.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Use {yyyyMMdd} date format so each date gets its own CSV file
        self.settings_manager = _make_settings_manager(self.temp_dir, date_format="{yyyyMMdd}")
        self.repo = CSVDataRepository(self.settings_manager)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _write_file_for_date(self, date: datetime.date, tasks):
        """Write a pre-populated CSV file for a specific date directly to disk."""
        headers = [
            "Start Time", "End Time", "Duration (Min)",
            "Ticket", "Title", "System Info", "AI Summary", "Resolved",
        ]
        date_str = date.strftime("%Y%m%d")
        path = os.path.join(self.temp_dir, f"work_log_{date_str}.csv")
        import csv as _csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.writer(f)
            writer.writerow(headers)
            for t in tasks:
                writer.writerow([
                    t.get("start_time", ""), t.get("end_time", ""),
                    t.get("duration", 0), t.get("ticket", ""),
                    t.get("title", ""), t.get("system_info", ""),
                    t.get("ai_summary", ""), t.get("resolved", "No"),
                ])
        return path

    def _task(self, date: datetime.date, hour: int, title: str, **kwargs):
        """Return a task dict for the given date/hour."""
        dt_str = f"{date.strftime('%Y-%m-%d')} {hour:02d}:00:00"
        return {
            "start_time": dt_str, "end_time": dt_str, "duration": 30,
            "ticket": kwargs.get("ticket", ""), "title": title,
            "system_info": "", "ai_summary": kwargs.get("ai_summary", ""),
            "resolved": kwargs.get("resolved", "No"),
        }

    # ── get_tasks_by_date ─────────────────────────────────────────────────────

    def test_get_tasks_by_date_reads_correct_file(self):
        """get_tasks_by_date returns only tasks from the matching date file."""
        date_a = datetime.date(2024, 5, 1)
        date_b = datetime.date(2024, 5, 2)
        self._write_file_for_date(date_a, [self._task(date_a, 9, "Task A")])
        self._write_file_for_date(date_b, [self._task(date_b, 10, "Task B")])

        tasks_a = self.repo.get_tasks_by_date(date_a)
        tasks_b = self.repo.get_tasks_by_date(date_b)

        self.assertEqual(len(tasks_a), 1)
        self.assertEqual(tasks_a[0]["Title"], "Task A")
        self.assertEqual(len(tasks_b), 1)
        self.assertEqual(tasks_b[0]["Title"], "Task B")

    def test_get_tasks_by_date_missing_file_returns_empty(self):
        """get_tasks_by_date returns [] when no file exists for that date."""
        result = self.repo.get_tasks_by_date(datetime.date(2020, 1, 1))
        self.assertEqual(result, [])

    # ── get_tasks_since ───────────────────────────────────────────────────────

    def test_get_tasks_since_spans_multiple_files(self):
        """get_tasks_since aggregates tasks across multiple date files."""
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        self._write_file_for_date(yesterday, [self._task(yesterday, 8, "Old task")])
        self._write_file_for_date(today, [self._task(today, 9, "New task")])

        since = datetime.datetime.combine(yesterday, datetime.time(7, 0))
        tasks = self.repo.get_tasks_since(since)

        titles = [t["Title"] for t in tasks]
        self.assertIn("Old task", titles)
        self.assertIn("New task", titles)

    def test_get_tasks_since_excludes_tasks_before_cutoff(self):
        """Tasks before the cutoff time are not returned."""
        today = datetime.date.today()
        self._write_file_for_date(
            today,
            [
                self._task(today, 8, "Before cutoff"),
                self._task(today, 10, "After cutoff"),
            ],
        )
        since = datetime.datetime.combine(today, datetime.time(9, 0))
        tasks = self.repo.get_tasks_since(since)
        titles = [t["Title"] for t in tasks]
        self.assertNotIn("Before cutoff", titles)
        self.assertIn("After cutoff", titles)

    # ── get_all_tasks ─────────────────────────────────────────────────────────

    def test_get_all_tasks_aggregates_all_files(self):
        """get_all_tasks returns tasks from every date file in the directory."""
        d1 = datetime.date(2024, 6, 1)
        d2 = datetime.date(2024, 6, 2)
        self._write_file_for_date(d1, [self._task(d1, 9, "Day1 Task")])
        self._write_file_for_date(d2, [self._task(d2, 10, "Day2 Task")])

        all_tasks = self.repo.get_all_tasks()
        titles = [t["Title"] for t in all_tasks]
        self.assertIn("Day1 Task", titles)
        self.assertIn("Day2 Task", titles)
        self.assertEqual(len(all_tasks), 2)

    # ── update_task_resolved_status ───────────────────────────────────────────

    def test_update_task_resolved_status_in_past_file(self):
        """Resolved status can be updated for a task in a historical date file."""
        past_date = datetime.date(2024, 7, 15)
        self._write_file_for_date(past_date, [self._task(past_date, 9, "Historical task")])

        tasks = self.repo.get_tasks_by_date(past_date)
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0]["task_id"]

        result = self.repo.update_task_resolved_status(task_id, "Yes")
        self.assertTrue(result)

        updated = self.repo.get_tasks_by_date(past_date)
        self.assertEqual(updated[0]["Resolved"], "Yes")

    # ── search_tasks ──────────────────────────────────────────────────────────

    def test_search_tasks_across_multiple_files(self):
        """search_tasks finds results from all date files."""
        d1 = datetime.date(2024, 8, 1)
        d2 = datetime.date(2024, 8, 2)
        self._write_file_for_date(d1, [self._task(d1, 9, "Payment review")])
        self._write_file_for_date(d2, [self._task(d2, 10, "Standup meeting")])

        results = self.repo.search_tasks("payment")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Title"], "Payment review")

    def test_search_tasks_date_range_limits_files(self):
        """search_tasks with a date range only reads files in that range."""
        d1 = datetime.date(2024, 9, 1)
        d2 = datetime.date(2024, 9, 2)
        d3 = datetime.date(2024, 9, 3)
        self._write_file_for_date(d1, [self._task(d1, 9, "Day1 standup")])
        self._write_file_for_date(d2, [self._task(d2, 9, "Day2 standup")])
        self._write_file_for_date(d3, [self._task(d3, 9, "Day3 standup")])

        results = self.repo.search_tasks("standup", start_date=d1, end_date=d2)
        titles = [r["Title"] for r in results]
        self.assertIn("Day1 standup", titles)
        self.assertIn("Day2 standup", titles)
        self.assertNotIn("Day3 standup", titles)

    # ── task_id routing ───────────────────────────────────────────────────────

    def test_task_id_routes_update_to_correct_file(self):
        """task_id from get_tasks_by_date correctly routes updates to the right file.

        This verifies the file-path encoding indirectly: if the task_id encodes
        the wrong file (or no file), the update would either fail or modify the
        wrong file, and the re-read would not show the change.
        """
        date_a = datetime.date(2024, 10, 1)
        date_b = datetime.date(2024, 10, 2)
        self._write_file_for_date(date_a, [self._task(date_a, 9, "Task A")])
        self._write_file_for_date(date_b, [self._task(date_b, 10, "Task B")])

        # Update a task in the date_a file
        tasks_a = self.repo.get_tasks_by_date(date_a)
        self.assertEqual(len(tasks_a), 1)
        result = self.repo.update_task_resolved_status(tasks_a[0]["task_id"], "Yes")
        self.assertTrue(result)

        # Only date_a's task should be resolved; date_b's should be unchanged
        updated_a = self.repo.get_tasks_by_date(date_a)
        updated_b = self.repo.get_tasks_by_date(date_b)
        self.assertEqual(updated_a[0]["Resolved"], "Yes")
        self.assertEqual(updated_b[0]["Resolved"], "No")


class TestTodoRepository(unittest.TestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        os.remove(self.csv_path)
        self.repo = TodoRepository(self.csv_path)

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_initialize_creates_file(self):
        """initialize() should create the CSV with the correct headers."""
        self.repo.initialize()
        self.assertTrue(os.path.exists(self.csv_path))
        with open(self.csv_path, 'r') as f:
            headers = f.readline().strip()
        self.assertEqual(headers, "ID,Task,Priority,Status,Created,Notes,Repeat,Days,CommittedAt,LastCompleted")

    def test_add_and_get_todos(self):
        """add_todo() should persist items retrievable by get_all_todos()."""
        self.repo.initialize()
        self.repo.add_todo("Fix authentication bug", "High", "Blocking release")
        todos = self.repo.get_all_todos()
        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0]['Task'], 'Fix authentication bug')
        self.assertEqual(todos[0]['Priority'], 'High')
        self.assertEqual(todos[0]['Status'], 'Pending')
        self.assertEqual(todos[0]['Notes'], 'Blocking release')

    def test_add_multiple_todos_unique_ids(self):
        """Each added todo should receive a unique, incrementing ID."""
        self.repo.initialize()
        self.repo.add_todo("Task A")
        self.repo.add_todo("Task B")
        todos = self.repo.get_all_todos()
        self.assertEqual(len(todos), 2)
        self.assertNotEqual(todos[0]['ID'], todos[1]['ID'])

    def test_update_todo_status(self):
        """update_todo_status() should change a todo's Status field."""
        self.repo.initialize()
        self.repo.add_todo("Write tests")
        todos = self.repo.get_all_todos()
        todo_id = todos[0]['ID']

        result = self.repo.update_todo_status(todo_id, "Done")
        self.assertTrue(result)

        updated = self.repo.get_all_todos()
        self.assertEqual(updated[0]['Status'], 'Done')

    def test_update_nonexistent_todo_returns_false(self):
        """update_todo_status() should return False when the ID is not found."""
        self.repo.initialize()
        result = self.repo.update_todo_status("999", "Done")
        self.assertFalse(result)

    def test_delete_todo(self):
        """delete_todo() should remove the item from the repository."""
        self.repo.initialize()
        self.repo.add_todo("Task to delete")
        todos = self.repo.get_all_todos()
        todo_id = todos[0]['ID']

        result = self.repo.delete_todo(todo_id)
        self.assertTrue(result)

        remaining = self.repo.get_all_todos()
        self.assertEqual(len(remaining), 0)

    def test_delete_preserves_other_todos(self):
        """delete_todo() should only remove the specified item."""
        self.repo.initialize()
        self.repo.add_todo("Keep me")
        self.repo.add_todo("Delete me")
        todos = self.repo.get_all_todos()
        delete_id = todos[1]['ID']

        self.repo.delete_todo(delete_id)

        remaining = self.repo.get_all_todos()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['Task'], 'Keep me')

    # ── Recurring-task tests ───────────────────────────────────────────────────

    def test_add_todo_with_repeat_daily(self):
        """add_todo() should persist repeat='daily' and retrieve it."""
        self.repo.initialize()
        self.repo.add_todo("Stand-up", repeat="daily")
        todos = self.repo.get_all_todos()
        self.assertEqual(todos[0]['Repeat'], 'daily')
        self.assertEqual(todos[0]['Days'], '')

    def test_add_todo_with_specific_days(self):
        """add_todo() should persist repeat='specific_days' with days list."""
        self.repo.initialize()
        self.repo.add_todo("Weekly review", repeat="specific_days", days="0,4")
        todos = self.repo.get_all_todos()
        self.assertEqual(todos[0]['Repeat'], 'specific_days')
        self.assertEqual(todos[0]['Days'], '0,4')

    def test_get_todos_due_today_daily(self):
        """Daily tasks should appear in get_todos_due_today() every day."""
        self.repo.initialize()
        self.repo.add_todo("Daily stand-up", repeat="daily")
        self.repo.add_todo("One-off task")  # should NOT appear
        due = self.repo.get_todos_due_today()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]['Task'], 'Daily stand-up')

    def test_get_todos_due_today_specific_days(self):
        """Tasks with specific_days should appear only on matching weekdays."""
        self.repo.initialize()
        today_wd = datetime.date.today().weekday()
        tomorrow_wd = (today_wd + 1) % 7
        # Task for today
        self.repo.add_todo("Today task", repeat="specific_days", days=str(today_wd))
        # Task for tomorrow only
        self.repo.add_todo("Tomorrow task", repeat="specific_days", days=str(tomorrow_wd))
        due = self.repo.get_todos_due_today()
        due_tasks = [t['Task'] for t in due]
        self.assertIn("Today task", due_tasks)
        self.assertNotIn("Tomorrow task", due_tasks)

    def test_get_todos_due_today_no_repeat(self):
        """Tasks with repeat='none' must not appear in get_todos_due_today()."""
        self.repo.initialize()
        self.repo.add_todo("One-off task")  # default repeat='none'
        due = self.repo.get_todos_due_today()
        self.assertEqual(len(due), 0)

    def test_set_and_get_committed(self):
        """set_committed() should mark a task; get_committed_todos() should return it."""
        self.repo.initialize()
        self.repo.add_todo("Look at this later", repeat="daily")
        todos = self.repo.get_all_todos()
        todo_id = todos[0]['ID']

        result = self.repo.set_committed(todo_id)
        self.assertTrue(result)

        committed = self.repo.get_committed_todos()
        self.assertEqual(len(committed), 1)
        self.assertEqual(committed[0]['ID'], todo_id)
        self.assertNotEqual(committed[0]['CommittedAt'], '')

    def test_clear_committed(self):
        """clear_committed() should remove the CommittedAt value."""
        self.repo.initialize()
        self.repo.add_todo("Look at this later", repeat="daily")
        todos = self.repo.get_all_todos()
        todo_id = todos[0]['ID']

        self.repo.set_committed(todo_id)
        self.assertEqual(len(self.repo.get_committed_todos()), 1)

        self.repo.clear_committed(todo_id)
        self.assertEqual(len(self.repo.get_committed_todos()), 0)

    def test_backward_compat_short_rows(self):
        """Repositories with old 6-column CSVs should still update correctly."""
        # Write a legacy CSV with only 6 columns
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            import csv as _csv
            writer = _csv.writer(f)
            writer.writerow(["ID", "Task", "Priority", "Status", "Created", "Notes"])
            writer.writerow(["1", "Old task", "Medium", "Pending", "2024-01-01 08:00:00", ""])

        result = self.repo.update_todo_status("1", "Done")
        self.assertTrue(result)
        todos = self.repo.get_all_todos()
        self.assertEqual(todos[0]['Status'], 'Done')


    def test_archive_done_todos(self):
        """archive_done_todos() should write done items to a file and remove them."""
        self.repo.initialize()
        self.repo.add_todo("Done task", "High", "completed work")
        self.repo.add_todo("Still pending", "Low", "")
        todos = self.repo.get_all_todos()
        self.repo.update_todo_status(todos[0]['ID'], "Done")

        fd, archive_path = tempfile.mkstemp(suffix='.md')
        os.close(fd)
        os.remove(archive_path)
        try:
            count = self.repo.archive_done_todos(archive_path)
            self.assertEqual(count, 1)

            # Archive file should exist and contain the done task
            self.assertTrue(os.path.exists(archive_path))
            with open(archive_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("Done task", content)
            self.assertNotIn("Still pending", content)

            # Active list should only contain the pending task
            remaining = self.repo.get_all_todos()
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0]['Task'], 'Still pending')
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)

    def test_archive_done_todos_no_done_items(self):
        """archive_done_todos() should return 0 when there are no done items."""
        self.repo.initialize()
        self.repo.add_todo("Pending task")

        fd, archive_path = tempfile.mkstemp(suffix='.md')
        os.close(fd)
        os.remove(archive_path)
        try:
            count = self.repo.archive_done_todos(archive_path)
            self.assertEqual(count, 0)
            self.assertFalse(os.path.exists(archive_path))
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)


if __name__ == '__main__':
    unittest.main()
