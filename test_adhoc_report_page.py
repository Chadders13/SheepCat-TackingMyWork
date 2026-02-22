"""
Tests for the AdHocReportPage helper methods (non-GUI logic).

These tests exercise collect_tasks, build_plain_report, and _parse_dates
without spinning up a Tk root, keeping them fast and headless.
"""
import os
import sys
import datetime
import tempfile
import types
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out tkinter before importing anything that depends on it.
# ---------------------------------------------------------------------------

def _make_tk_stub():
    """Return a minimal tkinter stub module."""
    tk = types.ModuleType('tkinter')
    tk.Frame = object
    tk.WORD = 'word'
    tk.DISABLED = 'disabled'
    tk.NORMAL = 'normal'
    tk.END = 'end'
    for name in ('Label', 'Button', 'Entry', 'StringVar', 'BooleanVar',
                 'Scrollbar', 'Text'):
        setattr(tk, name, MagicMock)

    # tkinter.ttk
    ttk = types.ModuleType('tkinter.ttk')
    for name in ('Treeview', 'Scrollbar', 'Style', 'Frame', 'Label'):
        setattr(ttk, name, MagicMock)
    tk.ttk = ttk

    # tkinter.messagebox
    mb = types.ModuleType('tkinter.messagebox')
    mb.showerror = MagicMock()
    mb.showinfo = MagicMock()
    tk.messagebox = mb

    # tkinter.scrolledtext
    st = types.ModuleType('tkinter.scrolledtext')
    st.ScrolledText = MagicMock
    tk.scrolledtext = st

    # tkinter.filedialog
    fd = types.ModuleType('tkinter.filedialog')
    fd.asksaveasfilename = MagicMock(return_value='')
    tk.filedialog = fd

    return tk


_tk_stub = _make_tk_stub()
sys.modules['tkinter'] = _tk_stub
sys.modules['tkinter.ttk'] = _tk_stub.ttk
sys.modules['tkinter.messagebox'] = _tk_stub.messagebox
sys.modules['tkinter.scrolledtext'] = _tk_stub.scrolledtext
sys.modules['tkinter.filedialog'] = _tk_stub.filedialog

# ---------------------------------------------------------------------------
# Now safe to import src modules that depend on tkinter.
# ---------------------------------------------------------------------------

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from csv_data_repository import CSVDataRepository
import adhoc_report_page as arp


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

class _StubSettingsManager:
    """Minimal stub that satisfies AdHocReportPage's settings_manager usage."""
    def get(self, key, default=None):
        defaults = {
            "ai_model": "test-model",
            "ai_api_url": "http://localhost:11434/api/generate",
            "llm_request_timeout": 5,
            "summary_file_directory": ".",
        }
        return defaults.get(key, default)


class _ReportHelper:
    """
    Thin wrapper that exposes the pure helpers from AdHocReportPage without
    needing a Tk window.
    """
    def __init__(self, repo):
        self.data_repository = repo
        self.settings_manager = _StubSettingsManager()

    # Borrow the pure methods directly from the class
    collect_tasks = arp.AdHocReportPage.collect_tasks
    build_plain_report = arp.AdHocReportPage.build_plain_report
    _parse_dates = arp.AdHocReportPage._parse_dates


class TestAdHocReportCollectTasks(unittest.TestCase):
    """Tests for AdHocReportPage.collect_tasks"""

    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        os.remove(self.csv_path)
        self.repo = CSVDataRepository(self.csv_path)
        self.repo.initialize()
        self.helper = _ReportHelper(self.repo)

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def _task(self, date_str, title, ticket='T-1', duration=30, resolved='No'):
        return {
            'start_time': f"{date_str} 10:00:00",
            'end_time': f"{date_str} 10:30:00",
            'duration': duration,
            'ticket': ticket,
            'title': title,
            'system_info': 'Test',
            'ai_summary': 'summary',
            'resolved': resolved,
        }

    def test_returns_tasks_for_single_date(self):
        self.repo.log_task(self._task('2024-03-01', 'Fix login bug'))
        result = self.helper.collect_tasks(
            datetime.date(2024, 3, 1),
            datetime.date(2024, 3, 1),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Title'], 'Fix login bug')

    def test_returns_tasks_across_date_range(self):
        self.repo.log_task(self._task('2024-03-01', 'Day 1 task'))
        self.repo.log_task(self._task('2024-03-02', 'Day 2 task'))
        self.repo.log_task(self._task('2024-03-03', 'Day 3 task'))

        result = self.helper.collect_tasks(
            datetime.date(2024, 3, 1),
            datetime.date(2024, 3, 3),
        )
        self.assertEqual(len(result), 3)

    def test_excludes_marker_rows(self):
        self.repo.log_task(self._task('2024-03-01', 'DAY STARTED'))
        self.repo.log_task(self._task('2024-03-01', 'DAY ENDED'))
        self.repo.log_task(self._task('2024-03-01', 'HOURLY SUMMARY (3 tasks)'))
        self.repo.log_task(self._task('2024-03-01', 'END OF DAY SUMMARY'))
        self.repo.log_task(self._task('2024-03-01', 'Real Task'))

        result = self.helper.collect_tasks(
            datetime.date(2024, 3, 1),
            datetime.date(2024, 3, 1),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Title'], 'Real Task')

    def test_returns_empty_list_for_date_with_no_tasks(self):
        result = self.helper.collect_tasks(
            datetime.date(2024, 3, 1),
            datetime.date(2024, 3, 1),
        )
        self.assertEqual(result, [])

    def test_excludes_tasks_outside_range(self):
        self.repo.log_task(self._task('2024-03-01', 'Before range'))
        self.repo.log_task(self._task('2024-03-02', 'In range'))
        self.repo.log_task(self._task('2024-03-05', 'After range'))

        result = self.helper.collect_tasks(
            datetime.date(2024, 3, 2),
            datetime.date(2024, 3, 4),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['Title'], 'In range')


class TestAdHocReportBuildPlainReport(unittest.TestCase):
    """Tests for AdHocReportPage.build_plain_report"""

    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        os.remove(self.csv_path)
        repo = CSVDataRepository(self.csv_path)
        repo.initialize()
        self.helper = _ReportHelper(repo)

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def _make_task(self, title, ticket='', duration='30', resolved='No'):
        return {
            'Title': title,
            'Ticket': ticket,
            'Duration (Min)': duration,
            'Resolved': resolved,
        }

    def test_single_date_heading(self):
        tasks = [self._make_task('Task A')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertIn('2024-03-01', report)
        # Should NOT contain an en-dash for a single date
        self.assertNotIn('\u2013', report)

    def test_date_range_heading(self):
        tasks = [self._make_task('Task A')]
        from_date = datetime.date(2024, 3, 1)
        to_date = datetime.date(2024, 3, 5)
        report = self.helper.build_plain_report(tasks, from_date, to_date)
        self.assertIn('2024-03-01', report)
        self.assertIn('2024-03-05', report)

    def test_includes_ticket_line(self):
        tasks = [self._make_task('Task A', ticket='ABC-42')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertIn('ABC-42', report)
        self.assertIn('**Tickets:**', report)

    def test_no_ticket_line_when_no_tickets(self):
        tasks = [self._make_task('Task A', ticket='')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertNotIn('**Tickets:**', report)

    def test_resolved_marker_present(self):
        tasks = [self._make_task('Task A', resolved='Yes')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertIn('\u2713', report)

    def test_unresolved_has_no_check_mark(self):
        tasks = [self._make_task('Task A', resolved='No')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertNotIn('\u2713', report)

    def test_task_title_in_report(self):
        tasks = [self._make_task('Implement OAuth login')]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        self.assertIn('Implement OAuth login', report)

    def test_multiple_tasks_listed(self):
        tasks = [
            self._make_task('Task A'),
            self._make_task('Task B'),
            self._make_task('Task C'),
        ]
        date = datetime.date(2024, 3, 1)
        report = self.helper.build_plain_report(tasks, date, date)
        for label in ('Task A', 'Task B', 'Task C'):
            self.assertIn(label, report)


class TestAdHocReportParseDates(unittest.TestCase):
    """Tests for AdHocReportPage._parse_dates (via a minimal stub frame)."""

    class _FakeFrame:
        """
        Minimal stub that mimics the StringVar accessors used by _parse_dates.
        """
        def __init__(self, from_str, to_str):
            self.from_var = type('V', (), {'get': lambda s: from_str})()
            self.to_var = type('V', (), {'get': lambda s: to_str})()

        def parse_dates(self):
            return arp.AdHocReportPage._parse_dates(self)

    def test_valid_dates_returned(self):
        frame = self._FakeFrame('2024-03-01', '2024-03-05')
        from_date, to_date = frame.parse_dates()
        self.assertEqual(from_date, datetime.date(2024, 3, 1))
        self.assertEqual(to_date, datetime.date(2024, 3, 5))

    def test_same_dates_accepted(self):
        frame = self._FakeFrame('2024-03-01', '2024-03-01')
        from_date, to_date = frame.parse_dates()
        self.assertEqual(from_date, to_date)

    def test_invalid_from_date_raises(self):
        frame = self._FakeFrame('not-a-date', '2024-03-05')
        with self.assertRaises(ValueError):
            frame.parse_dates()

    def test_invalid_to_date_raises(self):
        frame = self._FakeFrame('2024-03-01', '99/99/9999')
        with self.assertRaises(ValueError):
            frame.parse_dates()

    def test_from_after_to_raises(self):
        frame = self._FakeFrame('2024-03-10', '2024-03-05')
        with self.assertRaises(ValueError) as ctx:
            frame.parse_dates()
        self.assertIn("'From' date must be on or before", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
