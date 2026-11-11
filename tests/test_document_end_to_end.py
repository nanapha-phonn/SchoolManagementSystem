import hashlib
import shutil
import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import get_connection, initialize_database
from services.auth_service import create_initial_admin, authenticate_user
from services.document_service import (
    archive_document,
    get_document,
    get_documents,
    open_document,
    upload_document,
    verify_document,
)
from storage.document_storage import DocumentStorage


PDF_CONTENT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"%%EOF\n"
)


class DocumentEndToEndTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_e2e_test_"
        )

        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "test_school.db"
        self.storage_path = self.root / "documents"
        self.input_path = self.root / "input"
        self.input_path.mkdir()

        self.db_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path,
        )
        self.db_patcher.start()

        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(self.db_patcher.stop)

        initialize_database()

        create_initial_admin(
            "e2e_admin",
            "AdminPass123",
            "E2E Administrator",
        )

        self.admin_id = authenticate_user(
            "e2e_admin",
            "AdminPass123",
        )["id"]

        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("E2E-STU-001", "Test", "Student"),
                )
                self.student_id = cursor.lastrowid

        self.storage = DocumentStorage(self.storage_path)

    def test_complete_document_upload_verify_download_archive_lifecycle(self):
        # 1. Create a source PDF in the isolated temporary directory.
        source_path = self.input_path / "birth_certificate.pdf"
        source_path.write_bytes(PDF_CONTENT)

        # 2. Upload through the actual document service.
        document = upload_document(
            source_path,
            "student",
            self.student_id,
            "birth_certificate",
            "Student Birth Certificate",
            "End-to-end verification document.",
            actor_user_id=self.admin_id,
            storage=self.storage,
        )

        document_id = document["id"]
        storage_path = self.storage_path / document["storage_key"]

        self.assertGreater(document_id, 0)
        self.assertEqual(document["student_id"], self.student_id)
        self.assertEqual(document["status"], "active")
        self.assertTrue(storage_path.is_file())
        self.assertEqual(storage_path.read_bytes(), PDF_CONTENT)

        # 3. Confirm database registration and metadata.
        stored_document = get_document(
            document_id,
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(stored_document)
        self.assertEqual(
            stored_document["original_filename"],
            "birth_certificate.pdf",
        )
        self.assertEqual(
            stored_document["sha256"],
            hashlib.sha256(PDF_CONTENT).hexdigest(),
        )
        self.assertEqual(
            stored_document["size_bytes"],
            len(PDF_CONTENT),
        )

        # 4. Verify the stored file against its registered metadata.
        self.assertTrue(
            verify_document(
                document_id,
                actor_user_id=self.admin_id,
                storage=self.storage,
            )
        )

        # 5. Download using the same verified stream used by the UI.
        download_path = self.root / "downloaded_birth_certificate.pdf"

        with open_document(
            document_id,
            actor_user_id=self.admin_id,
            storage=self.storage,
        ) as verified_stream:
            with download_path.open("wb") as destination:
                shutil.copyfileobj(
                    verified_stream,
                    destination,
                )
                destination.flush()

        self.assertTrue(download_path.is_file())
        self.assertEqual(
            download_path.read_bytes(),
            PDF_CONTENT,
        )

        # 6. Archive the database record without deleting the file.
        archived_document = archive_document(
            document_id,
            actor_user_id=self.admin_id,
        )

        self.assertEqual(archived_document["status"], "archived")
        self.assertEqual(
            archived_document["archived_by"],
            self.admin_id,
        )
        self.assertIsNotNone(archived_document["archived_at"])
        self.assertTrue(storage_path.is_file())

        # 7. Confirm active listings exclude the archived document.
        active_documents = get_documents(
            owner_type="student",
            owner_id=self.student_id,
            status="active",
            actor_user_id=self.admin_id,
        )

        self.assertFalse(
            any(item["id"] == document_id for item in active_documents)
        )

        # 8. Confirm archived listings retain the document metadata.
        archived_documents = get_documents(
            owner_type="student",
            owner_id=self.student_id,
            status="archived",
            actor_user_id=self.admin_id,
        )

        self.assertTrue(
            any(item["id"] == document_id for item in archived_documents)
        )

        # 9. Confirm archived files remain verifiable and downloadable.
        self.assertTrue(
            verify_document(
                document_id,
                actor_user_id=self.admin_id,
                storage=self.storage,
            )
        )

        with open_document(
            document_id,
            actor_user_id=self.admin_id,
            storage=self.storage,
        ) as archived_stream:
            self.assertEqual(
                archived_stream.read(),
                PDF_CONTENT,
            )

        print("\nDocument lifecycle verification:")
        print("  Upload:             PASS")
        print("  Database record:    PASS")
        print("  SHA-256 integrity:  PASS")
        print("  Download:           PASS")
        print("  Archive:            PASS")
        print("  Archived retrieval: PASS")
        print("  File retention:     PASS")

    def test_temporary_database_remains_integral(self):
        with closing(get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_key_violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_key_violations, [])


if __name__ == "__main__":
    unittest.main()
