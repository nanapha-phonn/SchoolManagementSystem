import hashlib
import os
import sqlite3
import tempfile
import unittest
import zipfile

from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import get_connection, initialize_database
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
from services.backup_service import create_backup, restore_backup
from services.document_service import (
    get_document,
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


class BackupServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="backup_service_test_"
        )

        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "school.db"
        self.documents_path = self.root / "documents"
        self.backup_dir = self.root / "backups"
        self.input_dir = self.root / "input"

        self.input_dir.mkdir()

        self.db_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path,
        )
        self.db_patcher.start()

        self.addCleanup(self.db_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

        initialize_database()

        create_initial_admin(
            "backup_admin",
            "AdminPass123",
            "Backup Administrator",
        )

        self.admin_id = authenticate_user(
            "backup_admin",
            "AdminPass123",
        )["id"]

        self.staff_id = create_user(
            "backup_staff",
            "StaffPass123",
            "Backup Staff",
            "staff",
            self.admin_id,
        )

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
                    ("BACKUP-STU-001", "Backup", "Student"),
                )
                self.student_id = cursor.lastrowid

        self.storage = DocumentStorage(self.documents_path)

    def create_document(self):
        source = self.input_dir / "certificate.pdf"
        source.write_bytes(PDF_CONTENT)

        return upload_document(
            source,
            "student",
            self.student_id,
            "birth_certificate",
            "Backup Test Certificate",
            "Document used to test backup and restore.",
            actor_user_id=self.admin_id,
            storage=self.storage,
        )

    def create_backup(self):
        return create_backup(
            actor_user_id=self.admin_id,
            backup_dir=self.backup_dir,
            db_path=self.database_path,
            document_storage_dir=self.documents_path,
        )

    # --------------------------------------------------
    # BACKUP
    # --------------------------------------------------

    def test_01_backup_contains_database_documents_and_manifest(self):
        document = self.create_document()

        backup_path = self.create_backup()

        self.assertTrue(backup_path.is_file())
        self.assertEqual(
            backup_path.stat().st_mode & 0o777,
            0o600,
        )

        with zipfile.ZipFile(backup_path, "r") as archive:
            names = set(archive.namelist())

            self.assertIn("manifest.json", names)
            self.assertIn(
                "database/school_management.db",
                names,
            )
            self.assertIn(
                f"documents/{document['storage_key']}",
                names,
            )

            import json
            manifest = json.loads(
                archive.read("manifest.json")
            )

            self.assertEqual(
                manifest["format"],
                "school-management-system-backup",
            )
            self.assertEqual(manifest["version"], 1)

            document_entry = next(
                entry
                for entry in manifest["documents"]
                if entry["path"] == f"documents/{document['storage_key']}"
            )

            self.assertEqual(
                document_entry["sha256"],
                hashlib.sha256(PDF_CONTENT).hexdigest(),
            )

    def test_02_backup_requires_administrator_permission(self):
        with self.assertRaises(PermissionError):
            create_backup(
                actor_user_id=self.staff_id,
                backup_dir=self.backup_dir,
                db_path=self.database_path,
                document_storage_dir=self.documents_path,
            )

        self.assertFalse(self.backup_dir.exists())

    def test_03_backup_rejects_symlinked_document_files(self):
        self.documents_path.mkdir(parents=True, exist_ok=True)

        external_file = self.root / "external.txt"
        external_file.write_text("outside storage")

        link = self.documents_path / "external-link.txt"
        link.symlink_to(external_file)

        with self.assertRaises(ValueError):
            self.create_backup()

    def test_04_backup_rejects_missing_registered_document(self):
        document = self.create_document()

        stored_path = self.documents_path / document["storage_key"]
        stored_path.unlink()

        with self.assertRaises(ValueError):
            self.create_backup()

    # --------------------------------------------------
    # RESTORE
    # --------------------------------------------------

    def test_05_restore_recovers_database_and_document_files(self):
        document = self.create_document()
        backup_path = self.create_backup()

        # Modify both targets after the backup was created.
        with closing(get_connection()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("AFTER-BACKUP", "Changed", "Record"),
                )

        stored_path = self.documents_path / document["storage_key"]
        stored_path.write_bytes(b"modified after backup")

        result = restore_backup(
            backup_path,
            actor_user_id=self.admin_id,
            db_path=self.database_path,
            document_storage_dir=self.documents_path,
        )

        self.assertEqual(result["database_path"], self.database_path)
        self.assertEqual(
            result["document_storage_dir"],
            self.documents_path,
        )

        restored_document = get_document(
            document["id"],
            actor_user_id=self.admin_id,
        )

        self.assertEqual(
            restored_document["title"],
            "Backup Test Certificate",
        )

        self.assertTrue(
            verify_document(
                document["id"],
                actor_user_id=self.admin_id,
                storage=self.storage,
            )
        )

        restored_path = self.documents_path / document["storage_key"]

        self.assertEqual(
            restored_path.read_bytes(),
            PDF_CONTENT,
        )

        with closing(get_connection()) as connection:
            changed_record = connection.execute(
                """
                SELECT id
                FROM students
                WHERE admission_no = 'AFTER-BACKUP'
                """
            ).fetchone()

        self.assertIsNone(changed_record)

    def test_06_restore_requires_administrator_permission(self):
        backup_path = self.create_backup()

        original_database = self.database_path.read_bytes()

        with self.assertRaises(PermissionError):
            restore_backup(
                backup_path,
                actor_user_id=self.staff_id,
                db_path=self.database_path,
                document_storage_dir=self.documents_path,
            )

        self.assertEqual(
            self.database_path.read_bytes(),
            original_database,
        )

    def test_07_invalid_archive_does_not_replace_existing_data(self):
        invalid_backup = self.backup_dir / "invalid.zip"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(invalid_backup, "w") as archive:
            archive.writestr(
                "database/../../outside.db",
                b"unsafe",
            )

        original_database = self.database_path.read_bytes()

        with self.assertRaises(ValueError):
            restore_backup(
                invalid_backup,
                actor_user_id=self.admin_id,
                db_path=self.database_path,
                document_storage_dir=self.documents_path,
            )

        self.assertEqual(
            self.database_path.read_bytes(),
            original_database,
        )

    def test_08_restore_rejects_corrupted_document_backup(self):
        document = self.create_document()
        backup_path = self.create_backup()

        corrupted_backup = self.backup_dir / "corrupted.zip"

        with zipfile.ZipFile(backup_path, "r") as source:
            with zipfile.ZipFile(corrupted_backup, "w") as target:
                for item in source.infolist():
                    content = source.read(item.filename)

                    if item.filename == f"documents/{document['storage_key']}":
                        content = b"modified content"

                    target.writestr(item.filename, content)

        original_database = self.database_path.read_bytes()
        original_document = (
            self.documents_path / document["storage_key"]
        ).read_bytes()

        with self.assertRaises(ValueError):
            restore_backup(
                corrupted_backup,
                actor_user_id=self.admin_id,
                db_path=self.database_path,
                document_storage_dir=self.documents_path,
            )

        self.assertEqual(
            self.database_path.read_bytes(),
            original_database,
        )
        self.assertEqual(
            (
                self.documents_path / document["storage_key"]
            ).read_bytes(),
            original_document,
        )

    def test_09_restored_database_and_foreign_keys_are_valid(self):
        self.create_document()
        backup_path = self.create_backup()

        restore_backup(
            backup_path,
            actor_user_id=self.admin_id,
            db_path=self.database_path,
            document_storage_dir=self.documents_path,
        )

        connection = sqlite3.connect(self.database_path)

        try:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        finally:
            connection.close()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    # --------------------------------------------------
    # RESTORE ROLLBACK
    # --------------------------------------------------

    def _prepare_restore_rollback_state(self):
        self.create_document()
        backup_path = self.create_backup()

        # Add live data after the backup was created.
        with closing(get_connection()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("ROLLBACK-MARKER", "Live", "Record"),
                )

        # Add an unregistered file to verify the existing document
        # directory is preserved when installation fails.
        extra_file = self.documents_path / "local-only-note.txt"
        extra_file.write_text("preserve current document storage")

        return (
            backup_path,
            self.database_path.read_bytes(),
            extra_file,
            extra_file.read_bytes(),
        )

    def _assert_original_live_state_preserved(
        self,
        original_database,
        extra_file,
        original_extra_content,
    ):
        self.assertEqual(
            self.database_path.read_bytes(),
            original_database,
        )

        self.assertTrue(extra_file.is_file())
        self.assertEqual(
            extra_file.read_bytes(),
            original_extra_content,
        )

        with closing(get_connection()) as connection:
            marker = connection.execute(
                """
                SELECT id
                FROM students
                WHERE admission_no = 'ROLLBACK-MARKER'
                """
            ).fetchone()

        self.assertIsNotNone(marker)

        self.assertEqual(
            list(self.root.glob(".school.db.pre-restore-*")),
            [],
        )
        self.assertEqual(
            list(self.root.glob(".documents.pre-restore-*")),
            [],
        )

        self.assertEqual(
            list(self.root.glob(".school.db.restore-*")),
            [],
        )
        self.assertEqual(
            list(self.root.glob(".documents.restore-*")),
            [],
        )

    def test_10_restore_rolls_back_if_document_installation_fails(self):
        (
            backup_path,
            original_database,
            extra_file,
            original_extra_content,
        ) = self._prepare_restore_rollback_state()

        real_replace = os.replace

        def fail_document_install(source, target):
            source = Path(source)
            target = Path(target)

            if (
                target == self.documents_path
                and source.name.startswith(".documents.restore-")
            ):
                raise OSError(
                    "Injected document installation failure"
                )

            return real_replace(source, target)

        with patch(
            "services.backup_service.os.replace",
            side_effect=fail_document_install,
        ):
            with self.assertRaisesRegex(
                OSError,
                "Injected document installation failure",
            ):
                restore_backup(
                    backup_path,
                    actor_user_id=self.admin_id,
                    db_path=self.database_path,
                    document_storage_dir=self.documents_path,
                )

        self._assert_original_live_state_preserved(
            original_database,
            extra_file,
            original_extra_content,
        )

    def test_11_restore_rolls_back_if_database_installation_fails(self):
        (
            backup_path,
            original_database,
            extra_file,
            original_extra_content,
        ) = self._prepare_restore_rollback_state()

        real_replace = os.replace

        def fail_database_install(source, target):
            source = Path(source)
            target = Path(target)

            if (
                target == self.database_path
                and source.name.startswith(".school.db.restore-")
            ):
                raise OSError(
                    "Injected database installation failure"
                )

            return real_replace(source, target)

        with patch(
            "services.backup_service.os.replace",
            side_effect=fail_database_install,
        ):
            with self.assertRaisesRegex(
                OSError,
                "Injected database installation failure",
            ):
                restore_backup(
                    backup_path,
                    actor_user_id=self.admin_id,
                    db_path=self.database_path,
                    document_storage_dir=self.documents_path,
                )

        self._assert_original_live_state_preserved(
            original_database,
            extra_file,
            original_extra_content,
        )


if __name__ == "__main__":
    unittest.main()
