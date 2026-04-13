"""
Tests for the GraphRepository implementation.
"""
import os
import shutil
import sys
import tempfile
import unittest

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from graph_repository import GraphRepository


class TestGraphRepository(unittest.TestCase):
    """Unit tests for the SQLite-backed graph repository."""

    def setUp(self):
        """Create a temporary directory and an initialised GraphRepository."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_graph.db")
        self.repo = GraphRepository(self.db_path)
        self.repo.initialize()

    def tearDown(self):
        """Close the repo and delete the temp directory."""
        self.repo.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── Tags ──────────────────────────────────────────────────────────────────

    def test_initialize_creates_db_file(self):
        """initialize() must create the SQLite file on disk."""
        self.assertTrue(os.path.exists(self.db_path))

    def test_add_tag_returns_id(self):
        """add_tag() should return a positive integer id."""
        tag_id = self.repo.add_tag("backend")
        self.assertIsNotNone(tag_id)
        self.assertGreater(tag_id, 0)

    def test_add_tag_idempotent(self):
        """Adding the same tag twice returns the same id both times."""
        id1 = self.repo.add_tag("bugfix")
        id2 = self.repo.add_tag("bugfix")
        self.assertEqual(id1, id2)

    def test_add_tag_empty_string_returns_none(self):
        """add_tag() must reject empty/whitespace-only names."""
        self.assertIsNone(self.repo.add_tag(""))
        self.assertIsNone(self.repo.add_tag("   "))

    def test_get_all_tags_sorted(self):
        """get_all_tags() returns all tags sorted alphabetically."""
        self.repo.add_tag("zebra")
        self.repo.add_tag("alpha")
        self.repo.add_tag("middleware")
        tags = self.repo.get_all_tags()
        names = [t["name"] for t in tags]
        self.assertEqual(names, sorted(names))
        self.assertIn("zebra", names)
        self.assertIn("alpha", names)

    def test_delete_tag(self):
        """delete_tag() removes the tag and its task associations."""
        self.repo.add_tag("temp-tag")
        self.repo.tag_task("2024-01-15 09:00:00", "temp-tag")
        self.repo.delete_tag("temp-tag")

        tags = [t["name"] for t in self.repo.get_all_tags()]
        self.assertNotIn("temp-tag", tags)
        # Task should no longer carry the deleted tag
        task_tags = self.repo.get_task_tags("2024-01-15 09:00:00")
        self.assertNotIn("temp-tag", task_tags)

    def test_delete_nonexistent_tag_ok(self):
        """delete_tag() on a non-existent tag should return True without error."""
        self.assertTrue(self.repo.delete_tag("nonexistent-tag"))

    # ── Task ↔ tag relationships ───────────────────────────────────────────────

    def test_tag_task_and_get_task_tags(self):
        """tag_task() should associate a tag and get_task_tags() should return it."""
        task_id = "2024-01-15 10:00:00"
        self.repo.tag_task(task_id, "feature")
        self.repo.tag_task(task_id, "backend")
        tags = self.repo.get_task_tags(task_id)
        self.assertIn("feature", tags)
        self.assertIn("backend", tags)

    def test_tag_task_creates_tag_if_missing(self):
        """tag_task() should create the tag automatically when it doesn't exist."""
        task_id = "2024-02-01 08:30:00"
        result = self.repo.tag_task(task_id, "new-auto-tag")
        self.assertTrue(result)
        all_tags = [t["name"] for t in self.repo.get_all_tags()]
        self.assertIn("new-auto-tag", all_tags)

    def test_untag_task(self):
        """untag_task() should remove only the specified tag from a task."""
        task_id = "2024-01-20 14:00:00"
        self.repo.tag_task(task_id, "keep-tag")
        self.repo.tag_task(task_id, "remove-tag")
        self.repo.untag_task(task_id, "remove-tag")
        tags = self.repo.get_task_tags(task_id)
        self.assertIn("keep-tag", tags)
        self.assertNotIn("remove-tag", tags)

    def test_get_tasks_by_tag(self):
        """get_tasks_by_tag() should return all task_ids for the given tag."""
        self.repo.tag_task("2024-01-01 09:00:00", "sprint-42")
        self.repo.tag_task("2024-01-02 10:00:00", "sprint-42")
        self.repo.tag_task("2024-01-03 11:00:00", "other-tag")

        tasks = self.repo.get_tasks_by_tag("sprint-42")
        self.assertIn("2024-01-01 09:00:00", tasks)
        self.assertIn("2024-01-02 10:00:00", tasks)
        self.assertNotIn("2024-01-03 11:00:00", tasks)

    def test_get_task_tags_empty_for_unknown_task(self):
        """get_task_tags() on an untagged task should return an empty list."""
        self.assertEqual(self.repo.get_task_tags("1970-01-01 00:00:00"), [])

    # ── Timing notes ──────────────────────────────────────────────────────────

    def test_add_and_get_timing_note(self):
        """add_timing_note() and get_timing_notes() should round-trip correctly."""
        task_id = "2024-03-10 15:00:00"
        self.repo.add_timing_note(task_id, "Blocked by dependency on TICKET-99")
        notes = self.repo.get_timing_notes(task_id)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["note"], "Blocked by dependency on TICKET-99")
        self.assertIn("id", notes[0])
        self.assertIn("created_at", notes[0])

    def test_add_timing_note_empty_returns_false(self):
        """add_timing_note() must reject empty/whitespace notes."""
        self.assertFalse(self.repo.add_timing_note("2024-01-01 09:00:00", ""))
        self.assertFalse(self.repo.add_timing_note("2024-01-01 09:00:00", "   "))

    def test_multiple_timing_notes_ordered(self):
        """Multiple timing notes should be returned in creation order."""
        task_id = "2024-05-01 10:00:00"
        self.repo.add_timing_note(task_id, "Note A")
        self.repo.add_timing_note(task_id, "Note B")
        notes = self.repo.get_timing_notes(task_id)
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0]["note"], "Note A")
        self.assertEqual(notes[1]["note"], "Note B")

    def test_delete_timing_note(self):
        """delete_timing_note() should remove the note with the given id."""
        task_id = "2024-06-01 11:00:00"
        self.repo.add_timing_note(task_id, "Temp note")
        notes = self.repo.get_timing_notes(task_id)
        note_id = notes[0]["id"]
        self.repo.delete_timing_note(note_id)
        self.assertEqual(self.repo.get_timing_notes(task_id), [])

    def test_get_timing_notes_empty_for_unknown_task(self):
        """get_timing_notes() on a task with no notes returns an empty list."""
        self.assertEqual(self.repo.get_timing_notes("1970-01-01 00:00:00"), [])

    # ── Documents ─────────────────────────────────────────────────────────────

    def test_add_document_returns_id(self):
        """add_document() should return a positive integer id."""
        doc_id = self.repo.add_document("spec.txt", "/docs/spec.txt", "Content here")
        self.assertIsNotNone(doc_id)
        self.assertGreater(doc_id, 0)

    def test_add_document_upsert(self):
        """Adding the same file_path twice should update the record, not duplicate."""
        id1 = self.repo.add_document("spec.txt", "/docs/spec.txt", "v1")
        id2 = self.repo.add_document("spec_updated.txt", "/docs/spec.txt", "v2")
        self.assertEqual(id1, id2)
        doc = self.repo.get_document(id1)
        self.assertEqual(doc["content"], "v2")
        self.assertEqual(doc["name"], "spec_updated.txt")

    def test_get_all_documents_newest_first(self):
        """get_all_documents() should return all documents."""
        self.repo.add_document("first.txt", "/tmp/first.txt", None)
        self.repo.add_document("second.txt", "/tmp/second.txt", None)
        docs = self.repo.get_all_documents()
        self.assertGreaterEqual(len(docs), 2)
        names = [d["name"] for d in docs]
        self.assertIn("first.txt", names)
        self.assertIn("second.txt", names)

    def test_get_document_with_content(self):
        """get_document() should include the content field."""
        doc_id = self.repo.add_document("readme.md", "/docs/readme.md", "# Hello")
        doc = self.repo.get_document(doc_id)
        self.assertEqual(doc["content"], "# Hello")
        self.assertEqual(doc["name"], "readme.md")

    def test_get_document_unknown_id_returns_none(self):
        """get_document() for a non-existent id should return None."""
        self.assertIsNone(self.repo.get_document(99999))

    def test_delete_document(self):
        """delete_document() should remove the document record."""
        doc_id = self.repo.add_document("to_delete.txt", "/tmp/to_delete.txt", None)
        self.repo.delete_document(doc_id)
        self.assertIsNone(self.repo.get_document(doc_id))

    # ── Task ↔ document relationships ─────────────────────────────────────────

    def test_link_and_get_task_documents(self):
        """link_document_to_task() and get_task_documents() should round-trip."""
        doc_id = self.repo.add_document("design.md", "/docs/design.md", "Design doc")
        task_id = "2024-07-01 09:00:00"
        result = self.repo.link_document_to_task(task_id, doc_id, note="Related requirement")
        self.assertTrue(result)

        docs = self.repo.get_task_documents(task_id)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["name"], "design.md")
        self.assertEqual(docs[0]["note"], "Related requirement")

    def test_get_document_tasks(self):
        """get_document_tasks() should return all tasks linked to a document."""
        doc_id = self.repo.add_document("shared.txt", "/docs/shared.txt", None)
        self.repo.link_document_to_task("2024-08-01 10:00:00", doc_id)
        self.repo.link_document_to_task("2024-08-02 11:00:00", doc_id)

        tasks = self.repo.get_document_tasks(doc_id)
        task_ids = [t["task_id"] for t in tasks]
        self.assertIn("2024-08-01 10:00:00", task_ids)
        self.assertIn("2024-08-02 11:00:00", task_ids)

    def test_unlink_document_from_task(self):
        """unlink_document_from_task() should remove the link."""
        doc_id = self.repo.add_document("link_test.txt", "/tmp/link_test.txt", None)
        task_id = "2024-09-01 12:00:00"
        self.repo.link_document_to_task(task_id, doc_id)
        self.repo.unlink_document_from_task(task_id, doc_id)

        docs = self.repo.get_task_documents(task_id)
        self.assertEqual(docs, [])

    def test_delete_document_removes_task_links(self):
        """Deleting a document should also remove all its task links."""
        doc_id = self.repo.add_document("cascade.txt", "/tmp/cascade.txt", None)
        task_id = "2024-10-01 08:00:00"
        self.repo.link_document_to_task(task_id, doc_id)

        self.repo.delete_document(doc_id)

        # Task should have no linked documents
        self.assertEqual(self.repo.get_task_documents(task_id), [])

    def test_link_document_upsert(self):
        """Linking the same document-task pair twice should update rather than duplicate."""
        doc_id = self.repo.add_document("upsert_doc.txt", "/tmp/upsert_doc.txt", None)
        task_id = "2024-11-01 09:00:00"
        self.repo.link_document_to_task(task_id, doc_id, note="old note")
        self.repo.link_document_to_task(task_id, doc_id, note="updated note")

        docs = self.repo.get_task_documents(task_id)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["note"], "updated note")

    def test_get_task_documents_empty_for_unlinked_task(self):
        """get_task_documents() for a task with no linked docs returns an empty list."""
        self.assertEqual(self.repo.get_task_documents("1970-01-01 00:00:00"), [])

    def test_get_document_tasks_empty_for_unlinked_doc(self):
        """get_document_tasks() for a doc with no task links returns an empty list."""
        doc_id = self.repo.add_document("alone.txt", "/tmp/alone.txt", None)
        self.assertEqual(self.repo.get_document_tasks(doc_id), [])


if __name__ == "__main__":
    unittest.main()
