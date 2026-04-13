"""
Graph repository for SheepCat Work Tracker.

Provides SQLite-backed storage for task tags, categories, timing notes,
documents, and task-document relationships — forming a lightweight
graph-style knowledge store alongside the CSV work log.
"""
import sqlite3
import os
import datetime
from typing import List, Dict, Optional


class GraphRepository:
    """SQLite-based graph repository for task categorisation and document management.

    Each *task_id* used here corresponds to the ``Start Time`` string of a
    work-log entry (e.g. ``"2024-01-15 10:00:00"``), which is the natural
    primary key of a CSV row.
    """

    def __init__(self, db_path: str):
        """
        Initialise the graph repository.

        Args:
            db_path: Absolute path to the SQLite database file.
                     The file and its parent directory are created on first
                     :meth:`initialize` call.
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self):
        """Create all required database tables if they do not already exist."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tags (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT    NOT NULL UNIQUE COLLATE NOCASE
                );

                CREATE TABLE IF NOT EXISTS task_tags (
                    task_id  TEXT    NOT NULL,
                    tag_id   INTEGER NOT NULL REFERENCES tags(id),
                    added_at TEXT    NOT NULL,
                    PRIMARY KEY (task_id, tag_id)
                );

                CREATE TABLE IF NOT EXISTS timing_notes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id    TEXT NOT NULL,
                    note       TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    name      TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    content   TEXT,
                    added_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_documents (
                    task_id     TEXT    NOT NULL,
                    document_id INTEGER NOT NULL REFERENCES documents(id),
                    note        TEXT,
                    linked_at   TEXT NOT NULL,
                    PRIMARY KEY (task_id, document_id)
                );
            """)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a cached SQLite connection, creating it on first call."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Tags ──────────────────────────────────────────────────────────────────

    def get_all_tags(self) -> List[Dict]:
        """Return all tags sorted by name.

        Returns:
            List of ``{"id": int, "name": str}`` dicts.
        """
        rows = self._get_conn().execute(
            "SELECT id, name FROM tags ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def add_tag(self, name: str) -> Optional[int]:
        """Add a tag, returning its id (or the existing id if already present).

        Args:
            name: Tag name (whitespace is stripped; empty strings are rejected).

        Returns:
            The integer tag id, or ``None`` on failure.
        """
        name = name.strip()
        if not name:
            return None
        try:
            conn = self._get_conn()
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
            conn.commit()
            row = conn.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            return row["id"] if row else None
        except Exception as exc:
            print(f"Error adding tag: {exc}")
            return None

    def delete_tag(self, name: str) -> bool:
        """Delete a tag and all its task associations.

        Args:
            name: Tag name (case-insensitive).

        Returns:
            ``True`` on success (including when the tag did not exist).
        """
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if row:
                conn.execute("DELETE FROM task_tags WHERE tag_id = ?", (row["id"],))
                conn.execute("DELETE FROM tags WHERE id = ?", (row["id"],))
                conn.commit()
            return True
        except Exception as exc:
            print(f"Error deleting tag: {exc}")
            return False

    # ── Task ↔ tag relationships ───────────────────────────────────────────────

    def tag_task(self, task_id: str, tag_name: str) -> bool:
        """Associate a tag with a task, creating the tag if needed.

        Args:
            task_id:  Task identifier (``Start Time`` string from the CSV).
            tag_name: Tag name.

        Returns:
            ``True`` on success.
        """
        tag_id = self.add_tag(tag_name)
        if tag_id is None:
            return False
        try:
            added_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO task_tags (task_id, tag_id, added_at) VALUES (?, ?, ?)",
                (task_id, tag_id, added_at),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error tagging task: {exc}")
            return False

    def untag_task(self, task_id: str, tag_name: str) -> bool:
        """Remove a tag from a task.

        Args:
            task_id:  Task identifier.
            tag_name: Tag name (case-insensitive).

        Returns:
            ``True`` on success.
        """
        try:
            conn = self._get_conn()
            conn.execute(
                """DELETE FROM task_tags
                   WHERE task_id = ?
                     AND tag_id = (
                         SELECT id FROM tags WHERE name = ? COLLATE NOCASE
                     )""",
                (task_id, tag_name),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error untagging task: {exc}")
            return False

    def get_task_tags(self, task_id: str) -> List[str]:
        """Return all tag names associated with a task.

        Args:
            task_id: Task identifier.

        Returns:
            List of tag name strings, sorted alphabetically.
        """
        rows = self._get_conn().execute(
            """SELECT t.name
               FROM tags t
               JOIN task_tags tt ON tt.tag_id = t.id
               WHERE tt.task_id = ?
               ORDER BY t.name""",
            (task_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    def get_tasks_by_tag(self, tag_name: str) -> List[str]:
        """Return all task_ids that carry the given tag.

        Args:
            tag_name: Tag name (case-insensitive).

        Returns:
            List of task_id strings ordered by when they were tagged.
        """
        rows = self._get_conn().execute(
            """SELECT tt.task_id
               FROM task_tags tt
               JOIN tags t ON t.id = tt.tag_id
               WHERE t.name = ? COLLATE NOCASE
               ORDER BY tt.added_at""",
            (tag_name,),
        ).fetchall()
        return [r["task_id"] for r in rows]

    # ── Timing notes ──────────────────────────────────────────────────────────

    def add_timing_note(self, task_id: str, note: str) -> bool:
        """Add a free-text timing/context note for a task.

        Args:
            task_id: Task identifier.
            note:    Note text (whitespace is stripped; empty strings rejected).

        Returns:
            ``True`` on success.
        """
        note = note.strip()
        if not note:
            return False
        try:
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO timing_notes (task_id, note, created_at) VALUES (?, ?, ?)",
                (task_id, note, created_at),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error adding timing note: {exc}")
            return False

    def get_timing_notes(self, task_id: str) -> List[Dict]:
        """Return all timing notes for a task in chronological order.

        Args:
            task_id: Task identifier.

        Returns:
            List of ``{"id": int, "note": str, "created_at": str}`` dicts.
        """
        rows = self._get_conn().execute(
            "SELECT id, note, created_at FROM timing_notes WHERE task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_timing_note(self, note_id: int) -> bool:
        """Delete a timing note by its integer id.

        Args:
            note_id: Primary key of the note.

        Returns:
            ``True`` on success.
        """
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM timing_notes WHERE id = ?", (note_id,))
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error deleting timing note: {exc}")
            return False

    # ── Documents ─────────────────────────────────────────────────────────────

    def add_document(
        self,
        name: str,
        file_path: str,
        content: Optional[str] = None,
    ) -> Optional[int]:
        """Import a document into the store.

        If a document with the same *file_path* already exists its record is
        replaced (name, content, and added_at are refreshed).

        Args:
            name:      Human-readable document name (usually the filename).
            file_path: Absolute or relative path to the source file.
            content:   Optional extracted text content (e.g. from .txt/.md).

        Returns:
            The integer document id, or ``None`` on failure.
        """
        try:
            added_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO documents (name, file_path, content, added_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(file_path) DO UPDATE SET
                       name     = excluded.name,
                       content  = excluded.content,
                       added_at = excluded.added_at""",
                (name, file_path, content, added_at),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM documents WHERE file_path = ?", (file_path,)
            ).fetchone()
            return row["id"] if row else None
        except Exception as exc:
            print(f"Error adding document: {exc}")
            return None

    def get_all_documents(self) -> List[Dict]:
        """Return all documents, newest first.

        Returns:
            List of ``{"id", "name", "file_path", "added_at"}`` dicts.
        """
        rows = self._get_conn().execute(
            "SELECT id, name, file_path, added_at FROM documents ORDER BY added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Return full document data including content.

        Args:
            doc_id: Document primary key.

        Returns:
            Dict with ``id``, ``name``, ``file_path``, ``content``, and
            ``added_at`` keys, or ``None`` if not found.
        """
        row = self._get_conn().execute(
            "SELECT id, name, file_path, content, added_at FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        return dict(row) if row else None

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document and all its task links.

        Args:
            doc_id: Document primary key.

        Returns:
            ``True`` on success.
        """
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM task_documents WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error deleting document: {exc}")
            return False

    # ── Task ↔ document relationships ─────────────────────────────────────────

    def link_document_to_task(
        self, task_id: str, doc_id: int, note: str = ""
    ) -> bool:
        """Create (or replace) a link between a document and a task.

        Args:
            task_id: Task identifier.
            doc_id:  Document primary key.
            note:    Optional annotation describing the relationship.

        Returns:
            ``True`` on success.
        """
        try:
            linked_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO task_documents (task_id, document_id, note, linked_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(task_id, document_id) DO UPDATE SET
                       note      = excluded.note,
                       linked_at = excluded.linked_at""",
                (task_id, doc_id, note, linked_at),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error linking document to task: {exc}")
            return False

    def unlink_document_from_task(self, task_id: str, doc_id: int) -> bool:
        """Remove the link between a document and a task.

        Args:
            task_id: Task identifier.
            doc_id:  Document primary key.

        Returns:
            ``True`` on success.
        """
        try:
            conn = self._get_conn()
            conn.execute(
                "DELETE FROM task_documents WHERE task_id = ? AND document_id = ?",
                (task_id, doc_id),
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Error unlinking document: {exc}")
            return False

    def get_task_documents(self, task_id: str) -> List[Dict]:
        """Return all documents linked to a task.

        Args:
            task_id: Task identifier.

        Returns:
            List of ``{"id", "name", "file_path", "added_at", "note"}`` dicts.
        """
        rows = self._get_conn().execute(
            """SELECT d.id, d.name, d.file_path, d.added_at, td.note
               FROM documents d
               JOIN task_documents td ON td.document_id = d.id
               WHERE td.task_id = ?
               ORDER BY td.linked_at""",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_document_tasks(self, doc_id: int) -> List[Dict]:
        """Return all tasks linked to a document.

        Args:
            doc_id: Document primary key.

        Returns:
            List of ``{"task_id", "note", "linked_at"}`` dicts.
        """
        rows = self._get_conn().execute(
            """SELECT task_id, note, linked_at
               FROM task_documents
               WHERE document_id = ?
               ORDER BY linked_at""",
            (doc_id,),
        ).fetchall()
        return [dict(r) for r in rows]
