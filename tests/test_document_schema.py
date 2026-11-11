import sqlite3
import tempfile
import unittest
from pathlib import Path

import database.database as database_module


class DocumentSchemaTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_schema_test_"
        )
        self.original_db_path = database_module.DB_PATH

        database_module.DB_PATH = (
            Path(self.temp_dir.name) / "document_test.db"
        )

        database_module.initialize_database()
        self.connection = database_module.get_connection()

        self.user_id = self.connection.execute("""
            INSERT INTO users (
                username, password_hash, full_name, role
            )
            VALUES ('admin', 'test_hash', 'Test Admin', 'admin')
        """).lastrowid

        self.student_id = self.connection.execute("""
            INSERT INTO students (
                admission_no, first_name, last_name
            )
            VALUES ('STU-001', 'Test', 'Student')
        """).lastrowid

        self.teacher_id = self.connection.execute("""
            INSERT INTO teachers (
                employee_no, first_name, last_name
            )
            VALUES ('TCH-001', 'Test', 'Teacher')
        """).lastrowid

        self.transport_staff_id = self.connection.execute("""
            INSERT INTO transport_staff (
                employee_no, first_name, last_name, role
            )
            VALUES ('TR-001', 'Test', 'Driver', 'driver')
        """).lastrowid

        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        database_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def document_values(self, owner="student", **overrides):
        values = {
            "student_id": None,
            "teacher_id": None,
            "transport_staff_id": None,
            "category": {
                "student": "birth_certificate",
                "teacher": "qualification_certificate",
                "transport_staff": "drivers_license",
            }[owner],
            "title": "Test Document",
            "description": "Document schema test",
            "original_filename": "test_document.pdf",
            "storage_key": f"{owner}/1/test-document.pdf",
            "mime_type": "application/pdf",
            "file_extension": ".pdf",
            "size_bytes": 1024,
            "sha256": "a" * 64,
            "uploaded_by": self.user_id,
            "status": "active",
            "archived_by": None,
            "archived_at": None,
        }

        owner_ids = {
            "student": self.student_id,
            "teacher": self.teacher_id,
            "transport_staff": self.transport_staff_id,
        }

        if owner in owner_ids:
            values[f"{owner}_id"] = owner_ids[owner]

        values.update(overrides)
        return values

    def insert_document(self, values):
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)

        cursor = self.connection.execute(
            f"""
            INSERT INTO documents ({columns})
            VALUES ({placeholders})
            """,
            tuple(values.values()),
        )

        return cursor.lastrowid

    def assert_rejected(self, values):
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_document(values)

        self.connection.rollback()

    # --------------------------------------------------
    # SCHEMA STRUCTURE
    # --------------------------------------------------

    def test_01_document_table_columns_indexes_and_foreign_keys(self):
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(documents)"
            )
        }

        expected_columns = {
            "id", "student_id", "teacher_id",
            "transport_staff_id", "category", "title",
            "description", "original_filename", "storage_key",
            "mime_type", "file_extension", "size_bytes",
            "sha256", "uploaded_by", "created_at",
            "status", "archived_by", "archived_at",
        }

        self.assertEqual(columns, expected_columns)

        foreign_keys = self.connection.execute(
            "PRAGMA foreign_key_list(documents)"
        ).fetchall()

        self.assertEqual(len(foreign_keys), 5)

        indexes = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND tbl_name = 'documents'
            """)
        }

        expected_indexes = {
            "idx_documents_student_status_created_at",
            "idx_documents_teacher_status_created_at",
            "idx_documents_transport_staff_status_created_at",
            "idx_documents_category_status_created_at",
            "idx_documents_sha256",
            "idx_documents_uploaded_by_created_at",
        }

        self.assertTrue(expected_indexes.issubset(indexes))

    # --------------------------------------------------
    # VALID OWNERS
    # --------------------------------------------------

    def test_02_documents_can_belong_to_all_supported_owners(self):
        for owner in ("student", "teacher", "transport_staff"):
            with self.subTest(owner=owner):
                values = self.document_values(owner)
                document_id = self.insert_document(values)

                row = self.connection.execute("""
                    SELECT id, status
                    FROM documents
                    WHERE id = ?
                """, (document_id,)).fetchone()

                self.assertIsNotNone(row)
                self.assertEqual(row["status"], "active")

    # --------------------------------------------------
    # OWNER CONSTRAINTS
    # --------------------------------------------------

    def test_03_document_requires_exactly_one_owner(self):
        values = self.document_values()
        values["student_id"] = None

        self.assert_rejected(values)

    def test_04_document_rejects_multiple_owners(self):
        values = self.document_values(
            teacher_id=self.teacher_id,
            category="identity_document",
        )

        self.assert_rejected(values)

    def test_05_document_category_must_match_owner(self):
        values = self.document_values(
            category="drivers_license",
        )

        self.assert_rejected(values)

    def test_06_nonexistent_owner_is_rejected(self):
        invalid_cases = (
            ("student_id", "birth_certificate"),
            ("teacher_id", "qualification_certificate"),
            ("transport_staff_id", "drivers_license"),
        )

        for owner_field, category in invalid_cases:
            with self.subTest(owner=owner_field):
                values = self.document_values()
                values["student_id"] = None
                values["category"] = category
                values[owner_field] = 999999

                self.assert_rejected(values)

    # --------------------------------------------------
    # USER FOREIGN KEYS
    # --------------------------------------------------

    def test_07_nonexistent_uploader_is_rejected(self):
        values = self.document_values(uploaded_by=999999)
        self.assert_rejected(values)

    def test_08_nonexistent_archiving_user_is_rejected(self):
        values = self.document_values(
            status="archived",
            archived_by=999999,
            archived_at="2026-11-10T18:00:00",
        )

        self.assert_rejected(values)

    # --------------------------------------------------
    # FILE METADATA CONSTRAINTS
    # --------------------------------------------------

    def test_09_mime_type_and_extension_must_match(self):
        values = self.document_values(file_extension=".png")
        self.assert_rejected(values)

    def test_10_document_size_must_be_within_limit(self):
        values = self.document_values(size_bytes=10485761)
        self.assert_rejected(values)

    def test_11_empty_document_is_rejected(self):
        values = self.document_values(size_bytes=0)
        self.assert_rejected(values)

    def test_12_invalid_sha256_is_rejected(self):
        values = self.document_values(sha256="invalid")
        self.assert_rejected(values)

    def test_13_storage_path_traversal_is_rejected(self):
        unsafe_paths = (
            "../outside.pdf",
            "student/1/../outside.pdf",
            "/absolute/path.pdf",
            r"student\1\outside.pdf",
        )

        for path in unsafe_paths:
            with self.subTest(path=path):
                values = self.document_values(storage_key=path)
                self.assert_rejected(values)

    def test_14_original_filename_cannot_contain_a_path(self):
        values = self.document_values(
            original_filename="../outside.pdf"
        )

        self.assert_rejected(values)

    def test_15_storage_key_must_be_unique(self):
        values = self.document_values()
        self.insert_document(values)

        duplicate = self.document_values(
            teacher_id=self.teacher_id,
            category="qualification_certificate",
            storage_key=values["storage_key"],
        )

        self.assert_rejected(duplicate)

    # --------------------------------------------------
    # ARCHIVE CONSTRAINTS
    # --------------------------------------------------

    def test_16_active_document_cannot_have_archive_metadata(self):
        values = self.document_values(
            archived_by=self.user_id,
        )

        self.assert_rejected(values)

    def test_17_archived_document_requires_archive_metadata(self):
        values = self.document_values(
            status="archived",
        )

        self.assert_rejected(values)

    def test_18_valid_archived_document_is_accepted(self):
        values = self.document_values(
            status="archived",
            archived_by=self.user_id,
            archived_at="2026-11-10T18:00:00",
        )

        document_id = self.insert_document(values)

        row = self.connection.execute("""
            SELECT status, archived_by, archived_at
            FROM documents
            WHERE id = ?
        """, (document_id,)).fetchone()

        self.assertEqual(row["status"], "archived")
        self.assertEqual(row["archived_by"], self.user_id)
        self.assertEqual(
            row["archived_at"],
            "2026-11-10T18:00:00",
        )

    # --------------------------------------------------
    # REFERENTIAL INTEGRITY
    # --------------------------------------------------

    def test_19_owner_records_cannot_be_deleted_with_documents(self):
        owners = (
            ("students", self.student_id, "student"),
            ("teachers", self.teacher_id, "teacher"),
            (
                "transport_staff",
                self.transport_staff_id,
                "transport_staff",
            ),
        )

        for table, owner_id, owner_type in owners:
            with self.subTest(owner=owner_type):
                self.insert_document(
                    self.document_values(owner_type)
                )

                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(
                        f"DELETE FROM {table} WHERE id = ?",
                        (owner_id,),
                    )

                self.connection.rollback()

    def test_20_users_cannot_be_deleted_while_referenced(self):
        self.insert_document(self.document_values())

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "DELETE FROM users WHERE id = ?",
                (self.user_id,),
            )

        self.connection.rollback()

    def test_21_foreign_key_check_passes(self):
        violations = self.connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        self.assertEqual(violations, [])

    # --------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------

    def test_22_database_initialization_is_idempotent(self):
        database_module.initialize_database()

        exists = self.connection.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'documents'
        """).fetchone()

        self.assertIsNotNone(exists)

        integrity = self.connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        self.assertEqual(integrity, "ok")


if __name__ == "__main__":
    unittest.main()
