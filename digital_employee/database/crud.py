"""
Database CRUD operations using SQLite + JSON storage.
Provides a simple document-store interface for the Digital Employee.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DatabaseCRUD:
    """
    Simple document-store backed by SQLite.
    Each collection is stored as a table with JSON documents.
    """

    def __init__(self, db_path: str = "digital_employee.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database and create core tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collection ON documents(collection)")
            conn.commit()
        logger.debug(f"Database initialized: {self.db_path}")

    # ─────────────────────────────────────────────
    # CRUD Operations
    # ─────────────────────────────────────────────

    def create(self, collection: str, document: dict) -> dict:
        """Create a new document in a collection."""
        doc_id = document.get("id", str(uuid.uuid4()))
        document["id"] = doc_id
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO documents (id, collection, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (doc_id, collection, json.dumps(document, default=str), now, now)
            )
            conn.commit()

        return document

    def get(self, collection: str, doc_id: str) -> Optional[dict]:
        """Get a document by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM documents WHERE collection = ? AND id = ?",
                (collection, doc_id)
            ).fetchone()

        if row:
            return json.loads(row["data"])
        return None

    def update(self, collection: str, doc_id: str, updates: dict) -> Optional[dict]:
        """Update specific fields in a document."""
        existing = self.get(collection, doc_id)
        if not existing:
            logger.warning(f"Document not found: {collection}/{doc_id}")
            return None

        existing.update(updates)
        existing["updated_at"] = datetime.utcnow().isoformat()
        now = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            conn.execute(
                "UPDATE documents SET data = ?, updated_at = ? WHERE collection = ? AND id = ?",
                (json.dumps(existing, default=str), now, collection, doc_id)
            )
            conn.commit()

        return existing

    def delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM documents WHERE collection = ? AND id = ?",
                (collection, doc_id)
            )
            conn.commit()
        return cursor.rowcount > 0

    def list(self, collection: str, limit: int = 1000, offset: int = 0) -> list[dict]:
        """List all documents in a collection."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT data FROM documents WHERE collection = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (collection, limit, offset)
            ).fetchall()

        return [json.loads(row["data"]) for row in rows]

    def find(self, collection: str, filters: dict) -> list[dict]:
        """Find documents matching filter criteria (simple equality check on JSON fields)."""
        all_docs = self.list(collection)
        results = []

        for doc in all_docs:
            match = all(doc.get(k) == v for k, v in filters.items())
            if match:
                results.append(doc)

        return results

    def find_one(self, collection: str, filters: dict) -> Optional[dict]:
        """Find first document matching filter criteria."""
        results = self.find(collection, filters)
        return results[0] if results else None

    def count(self, collection: str) -> int:
        """Count documents in a collection."""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) as cnt FROM documents WHERE collection = ?",
                (collection,)
            ).fetchone()
        return result["cnt"] if result else 0

    def upsert(self, collection: str, filters: dict, document: dict) -> dict:
        """Create or update a document based on filter criteria."""
        existing = self.find_one(collection, filters)
        if existing:
            return self.update(collection, existing["id"], document)
        return self.create(collection, document)

    # ─────────────────────────────────────────────
    # Collection Management
    # ─────────────────────────────────────────────

    def list_collections(self) -> list[str]:
        """List all collections in the database."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT collection FROM documents"
            ).fetchall()
        return [row["collection"] for row in rows]

    def clear_collection(self, collection: str) -> int:
        """Delete all documents in a collection (use carefully!)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM documents WHERE collection = ?",
                (collection,)
            )
            conn.commit()
        return cursor.rowcount

    def get_stats(self) -> dict:
        """Get database statistics."""
        collections = self.list_collections()
        stats = {}
        for col in collections:
            stats[col] = self.count(col)
        return {"collections": stats, "total_documents": sum(stats.values())}
