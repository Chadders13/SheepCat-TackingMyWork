"""
Tests for the Hyper Focus feature in WorkLoggerApp.

These tests validate the state-machine logic for activating, displaying, and
deactivating Hyper Focus mode without launching a real Tk window.
"""
import datetime
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class TestHyperFocusState(unittest.TestCase):
    """Test state transitions for Hyper Focus mode."""

    def setUp(self):
        # Patch tkinter-dependent imports so no display is required
        self._patches = []
        for mod_name in ("tkinter", "tkinter.messagebox", "tkinter.scrolledtext",
                         "tkinter.ttk", "theme", "csv_data_repository",
                         "todo_repository", "settings_manager", "settings_page",
                         "review_log_page", "todo_page", "onboarding", "ollama_client"):
            p = patch.dict("sys.modules", {mod_name: MagicMock()})
            p.start()
            self._patches.append(p)

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def _make_app(self):
        """Build a minimal FakeApp with only hyper-focus state and methods."""

        class FakeSettingsManager:
            def get(self, key, default=None):
                return {"checkin_interval_minutes": 60}.get(key, default)

        class FakeApp:
            pass

        import importlib
        import src.MyWorkTracker as mwt
        importlib.reload(mwt)

        app = FakeApp()
        app.is_running = True
        app.timer_id = None
        app.countdown_id = None
        app.hyper_focus_active = False
        app.hyper_focus_end_time = None
        app.hyper_focus_timer_id = None
        app.next_checkin_time = datetime.datetime.now() + datetime.timedelta(minutes=60)
        app.btn_hyper_focus = MagicMock()
        app.countdown_label = MagicMock()
        app.root = MagicMock()
        app.root.after.return_value = "timer_id_123"
        app.root.after_cancel = MagicMock()
        app.settings_manager = FakeSettingsManager()
        app.hourly_checkin = MagicMock()
        mwt.messagebox = MagicMock()

        app._start_hyper_focus = mwt.WorkLoggerApp._start_hyper_focus.__get__(app)
        app._end_hyper_focus = mwt.WorkLoggerApp._end_hyper_focus.__get__(app)
        app.update_countdown = mwt.WorkLoggerApp.update_countdown.__get__(app)

        return app, mwt

    @staticmethod
    def _get_label_text(mock_label):
        """Extract the 'text' kwarg from the last call to mock_label.config()."""
        call_kwargs = mock_label.config.call_args
        if call_kwargs[1]:
            return call_kwargs[1].get("text", "")
        return call_kwargs[0][0] if call_kwargs[0] else ""

    # ------------------------------------------------------------------
    # _start_hyper_focus
    # ------------------------------------------------------------------

    def test_start_hyper_focus_timed_sets_state(self):
        app, _ = self._make_app()
        end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        app._start_hyper_focus(end_time)

        self.assertTrue(app.hyper_focus_active)
        self.assertEqual(app.hyper_focus_end_time, end_time)

    def test_start_hyper_focus_indefinite_sets_state(self):
        app, _ = self._make_app()
        app._start_hyper_focus(None)

        self.assertTrue(app.hyper_focus_active)
        self.assertIsNone(app.hyper_focus_end_time)

    def test_start_hyper_focus_cancels_existing_timer(self):
        app, _ = self._make_app()
        app.timer_id = "existing_timer"
        app._start_hyper_focus(None)

        app.root.after_cancel.assert_called_once_with("existing_timer")
        self.assertIsNone(app.timer_id)

    def test_start_hyper_focus_timed_schedules_resume(self):
        app, _ = self._make_app()
        end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        app._start_hyper_focus(end_time)

        # root.after should have been called to schedule the auto-resume
        app.root.after.assert_called_once()
        args = app.root.after.call_args[0]
        self.assertGreater(args[0], 0)   # delay > 0 ms
        self.assertEqual(args[1], app._end_hyper_focus)

    def test_start_hyper_focus_indefinite_no_schedule(self):
        app, _ = self._make_app()
        app._start_hyper_focus(None)

        # No auto-resume timer should have been scheduled
        app.root.after.assert_not_called()

    def test_start_hyper_focus_updates_button_text(self):
        app, _ = self._make_app()
        app._start_hyper_focus(None)

        app.btn_hyper_focus.config.assert_called_with(text="⏹ End Hyper Focus")

    # ------------------------------------------------------------------
    # _end_hyper_focus
    # ------------------------------------------------------------------

    def test_end_hyper_focus_clears_state(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app.hyper_focus_end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        app._end_hyper_focus()

        self.assertFalse(app.hyper_focus_active)
        self.assertIsNone(app.hyper_focus_end_time)

    def test_end_hyper_focus_reschedules_checkin(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app._end_hyper_focus()

        # A new check-in timer should be scheduled
        app.root.after.assert_called_once()
        args = app.root.after.call_args[0]
        expected_ms = 60 * 60 * 1000
        self.assertEqual(args[0], expected_ms)

    def test_end_hyper_focus_cancels_pending_resume_timer(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app.hyper_focus_timer_id = "focus_timer_456"
        app._end_hyper_focus()

        app.root.after_cancel.assert_called_once_with("focus_timer_456")
        self.assertIsNone(app.hyper_focus_timer_id)

    def test_end_hyper_focus_updates_button_text(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app._end_hyper_focus()

        app.btn_hyper_focus.config.assert_called_with(text="🎯 Hyper Focus")

    def test_end_hyper_focus_updates_next_checkin_time(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        before = datetime.datetime.now()
        app._end_hyper_focus()
        after = datetime.datetime.now()

        expected_min = before + datetime.timedelta(minutes=60)
        expected_max = after + datetime.timedelta(minutes=60)
        self.assertGreaterEqual(app.next_checkin_time, expected_min)
        self.assertLessEqual(app.next_checkin_time, expected_max)

    # ------------------------------------------------------------------
    # update_countdown (hyper focus path)
    # ------------------------------------------------------------------

    def test_update_countdown_shows_indefinite_focus_message(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app.hyper_focus_end_time = None
        app.update_countdown()

        text = self._get_label_text(app.countdown_label)
        self.assertIn("Hyper Focus", text)

    def test_update_countdown_shows_timed_focus_message(self):
        app, _ = self._make_app()
        app.hyper_focus_active = True
        app.hyper_focus_end_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
        app.update_countdown()

        text = self._get_label_text(app.countdown_label)
        self.assertIn("Hyper Focus", text)
        self.assertIn("resuming in", text)

    def test_update_countdown_normal_when_focus_inactive(self):
        app, _ = self._make_app()
        app.hyper_focus_active = False
        app.next_checkin_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
        app.update_countdown()

        text = self._get_label_text(app.countdown_label)
        self.assertIn("Next check-in in", text)


if __name__ == '__main__':
    unittest.main()
