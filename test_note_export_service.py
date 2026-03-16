"""
Tests for NoteExportService implementations (Obsidian, Notable) and the
extended APIServiceFactory methods.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from external_api_service import (
    NoteExportService,
    ObsidianAPIService,
    NotableService,
    APIServiceFactory,
    _safe_filename,
)


# ---------------------------------------------------------------------------
# _safe_filename helper
# ---------------------------------------------------------------------------

class TestSafeFilename(unittest.TestCase):
    def test_strips_invalid_chars(self):
        result = _safe_filename('Note: "today" <work>')
        self.assertNotIn(":", result)
        self.assertNotIn('"', result)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_normal_title_unchanged(self):
        self.assertEqual(_safe_filename("Daily Summary 2024-01-15"), "Daily Summary 2024-01-15")

    def test_empty_returns_note(self):
        self.assertEqual(_safe_filename(""), "note")

    def test_backslash_replaced(self):
        result = _safe_filename("path\\to\\note")
        self.assertNotIn("\\", result)


# ---------------------------------------------------------------------------
# ObsidianAPIService
# ---------------------------------------------------------------------------

class TestObsidianAPIService(unittest.TestCase):

    def _make_service(self, host="http://localhost:27123", api_key="secretkey",
                      notes_folder="SheepCat"):
        return ObsidianAPIService(host=host, api_key=api_key, notes_folder=notes_folder)

    def test_name(self):
        self.assertEqual(self._make_service().name, "Obsidian")

    def test_is_configured_all_fields(self):
        self.assertTrue(self._make_service().is_configured)

    def test_is_configured_missing_host(self):
        svc = self._make_service(host="")
        self.assertFalse(svc.is_configured)

    def test_is_configured_missing_api_key(self):
        svc = self._make_service(api_key="")
        self.assertFalse(svc.is_configured)

    def test_send_note_success_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("external_api_service.requests.put", return_value=mock_resp):
            result = self._make_service().send_note("My Note", "# Content")
        self.assertTrue(result)

    def test_send_note_success_204(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        with patch("external_api_service.requests.put", return_value=mock_resp):
            result = self._make_service().send_note("My Note", "# Content")
        self.assertTrue(result)

    def test_send_note_failure(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("external_api_service.requests.put", return_value=mock_resp):
            result = self._make_service().send_note("My Note", "# Content")
        self.assertFalse(result)

    def test_send_note_network_error(self):
        with patch("external_api_service.requests.put", side_effect=Exception("refused")):
            result = self._make_service().send_note("My Note", "# Content")
        self.assertFalse(result)

    def test_send_note_unconfigured(self):
        svc = ObsidianAPIService(host="", api_key="")
        self.assertFalse(svc.send_note("title", "content"))

    def test_send_note_url_includes_folder_and_title(self):
        """Verify that the PUT URL contains the notes folder and safe title."""
        captured = {}

        def fake_put(url, **kwargs):
            captured["url"] = url
            m = MagicMock()
            m.status_code = 200
            return m

        with patch("external_api_service.requests.put", side_effect=fake_put):
            self._make_service(notes_folder="Work").send_note("Today's Summary", "body")

        self.assertIn("Work/", captured["url"])
        self.assertIn("Today", captured["url"])

    def test_auth_header_uses_bearer(self):
        svc = self._make_service(api_key="mytoken")
        headers = svc._auth_headers()
        self.assertEqual(headers["Authorization"], "Bearer mytoken")

    def test_is_a_note_export_service(self):
        self.assertIsInstance(self._make_service(), NoteExportService)


# ---------------------------------------------------------------------------
# NotableService
# ---------------------------------------------------------------------------

class TestNotableService(unittest.TestCase):

    def test_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            self.assertEqual(svc.name, "Notable")

    def test_is_configured_valid_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            self.assertTrue(svc.is_configured)

    def test_is_configured_empty_directory(self):
        svc = NotableService(notes_directory="")
        self.assertFalse(svc.is_configured)

    def test_is_configured_nonexistent_directory(self):
        svc = NotableService(notes_directory="/nonexistent/path/that/does/not/exist")
        self.assertFalse(svc.is_configured)

    def test_send_note_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            result = svc.send_note("Test Note", "# Hello\n\nThis is a test note.")
            self.assertTrue(result)
            files = os.listdir(tmpdir)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith(".md"))

    def test_send_note_file_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            content = "# My Summary\n\nWork done today."
            svc.send_note("Daily Summary", content)
            files = os.listdir(tmpdir)
            with open(os.path.join(tmpdir, files[0]), encoding="utf-8") as fh:
                written = fh.read()
            self.assertEqual(written, content)

    def test_send_note_title_sanitised(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            svc.send_note('Note: "today" <work>', "body")
            files = os.listdir(tmpdir)
            self.assertEqual(len(files), 1)
            name = files[0]
            self.assertNotIn(":", name)
            self.assertNotIn('"', name)

    def test_send_note_unconfigured(self):
        svc = NotableService(notes_directory="")
        self.assertFalse(svc.send_note("title", "content"))

    def test_send_note_write_error(self):
        """send_note returns False when the file cannot be written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = NotableService(notes_directory=tmpdir)
            with patch("builtins.open", side_effect=PermissionError("denied")):
                result = svc.send_note("title", "body")
            self.assertFalse(result)

    def test_is_a_note_export_service(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsInstance(NotableService(notes_directory=tmpdir), NoteExportService)


# ---------------------------------------------------------------------------
# APIServiceFactory — note service methods
# ---------------------------------------------------------------------------

class TestAPIServiceFactoryNotes(unittest.TestCase):

    class _MockSettings:
        def __init__(self, data):
            self._data = data

        def get(self, key, default=""):
            return self._data.get(key, default)

        def get_credential(self, key):
            return self._data.get(key, "")

    def _settings(self, **kwargs):
        return self._MockSettings(kwargs)

    def test_create_obsidian_service(self):
        sm = self._settings(
            obsidian_host="http://localhost:27123",
            obsidian_api_key="mykey",
            obsidian_notes_folder="Work",
        )
        svc = APIServiceFactory.create_obsidian_service(sm)
        self.assertIsInstance(svc, ObsidianAPIService)
        self.assertTrue(svc.is_configured)

    def test_create_notable_service(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = self._settings(notable_notes_directory=tmpdir)
            svc = APIServiceFactory.create_notable_service(sm)
            self.assertIsInstance(svc, NotableService)
            self.assertTrue(svc.is_configured)

    def test_get_configured_note_services_obsidian_only(self):
        sm = self._settings(
            obsidian_enabled=True,
            obsidian_host="http://localhost:27123",
            obsidian_api_key="mykey",
            obsidian_notes_folder="Work",
            notable_enabled=False,
        )
        services = APIServiceFactory.get_configured_note_services(sm)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "Obsidian")

    def test_get_configured_note_services_notable_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = self._settings(
                obsidian_enabled=False,
                notable_enabled=True,
                notable_notes_directory=tmpdir,
            )
            services = APIServiceFactory.get_configured_note_services(sm)
            self.assertEqual(len(services), 1)
            self.assertEqual(services[0].name, "Notable")

    def test_get_configured_note_services_both(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = self._settings(
                obsidian_enabled=True,
                obsidian_host="http://localhost:27123",
                obsidian_api_key="mykey",
                obsidian_notes_folder="Work",
                notable_enabled=True,
                notable_notes_directory=tmpdir,
            )
            services = APIServiceFactory.get_configured_note_services(sm)
            self.assertEqual(len(services), 2)
            names = [s.name for s in services]
            self.assertIn("Obsidian", names)
            self.assertIn("Notable", names)

    def test_get_configured_note_services_none(self):
        sm = self._settings()
        services = APIServiceFactory.get_configured_note_services(sm)
        self.assertEqual(services, [])

    def test_get_configured_note_services_obsidian_disabled(self):
        sm = self._settings(
            obsidian_enabled=False,
            obsidian_host="http://localhost:27123",
            obsidian_api_key="mykey",
        )
        services = APIServiceFactory.get_configured_note_services(sm)
        self.assertEqual(services, [])

    def test_get_configured_note_services_notable_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = self._settings(
                notable_enabled=False,
                notable_notes_directory=tmpdir,
            )
            services = APIServiceFactory.get_configured_note_services(sm)
            self.assertEqual(services, [])


if __name__ == "__main__":
    unittest.main()
