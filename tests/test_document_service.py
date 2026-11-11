import hashlib
import sqlite3
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import get_connection, initialize_database
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user, update_user_status
from storage.document_storage import DocumentStorage

from services.document_service import (
    archive_document,
    get_document,
    get_documents,
    open_document,
    upload_document,
    verify_document,
)


PDF_CONTENT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"%%EOF\n"
)


class DocumentServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_service_test_"
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

        self.addCleanup(self.db_patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)

        initialize_database()

        create_initial_admin(
            "admin1",
            "AdminPass123",
            "Test Administrator",
        )

        self.admin_id = authenticate_user(
            "admin1",
            "AdminPass123",
        )["id"]

        self.staff_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id,
        )

        with get_connection() as connection:
            self.student_id = connection.execute("""
                INSERT INTO students (
                    admission_no,
                    first_name,
                    last_name
                )
                VALUES ('STU-001', 'Test', 'Student')
            """).lastrowid

            self.teacher_id = connection.execute("""
                INSERT INTO teachers (
                    employee_no,
                    first_name,
                    last_name
                )
                VALUES ('TCH-001', 'Test', 'Teacher')
            """).lastrowid

            self.transport_staff_id = connection.execute("""
                INSERT INTO transport_staff (
                    employee_no,
                    first_name,
                    last_name,
                    role
                )
                VALUES ('TR-001', 'Test', 'Driver', 'driver')
            """).lastrowid

        self.storage = DocumentStorage(self.storage_path)

    def create_source(self, name="certificate.pdf", content=PDF_CONTENT):
        source = self.input_path / name
        source.write_bytes(content)
        return source

    def upload_student_document(self, **overrides):
        data = {
            "source_path": self.create_source(),
            "owner_type": "student",
            "owner_id": self.student_id,
            "category": "birth_certificate",
            "title": "Birth Certificate",
            "description": "Student birth certificate",
            "actor_user_id": self.admin_id,
            "storage": self.storage,
        }
        data.update(overrides)

        return upload_document(**data)

    # --------------------------------------------------
    # UPLOAD
    # --------------------------------------------------

    def test_01_upload_student_document(self):
        document = self.upload_student_document()

        self.assertGreater(document["id"], 0)
        self.assertEqual(document["student_id"], self.student_id)
        self.assertIsNone(document["teacher_id"])
        self.assertEqual(document["category"], "birth_certificate")
        self.assertEqual(document["title"], "Birth Certificate")
        self.assertEqual(document["status"], "active")
        self.assertEqual(document["uploaded_by"], self.admin_id)

        self.assertTrue(
            (self.storage_path / document["storage_key"]).is_file()
        )

    def test_02_upload_documents_for_all_owner_types(self):
        cases = [
            (
                "student",
                self.student_id,
                "birth_certificate",
            ),
            (
                "teacher",
                self.teacher_id,
                "qualification_certificate",
            ),
            (
                "transport_staff",
                self.transport_staff_id,
                "drivers_license",
            ),
        ]

        for owner_type, owner_id, category in cases:
            with self.subTest(owner=owner_type):
                document = upload_document(
                    self.create_source(
                        f"{owner_type}.pdf"
                    ),
                    owner_type,
                    owner_id,
                    category,
                    f"{owner_type.title()} Document",
                    actor_user_id=self.admin_id,
                    storage=self.storage,
                )

                self.assertEqual(
                    document[f"{owner_type}_id"],
                    owner_id,
                )

    def test_03_staff_can_upload_documents(self):
        document = self.upload_student_document(
            actor_user_id=self.staff_id,
        )

        self.assertEqual(
            document["uploaded_by"],
            self.staff_id,
        )

    def test_04_missing_owner_is_rejected_before_storage(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.upload_student_document(owner_id=999999)

        self.assertFalse(self.storage_path.exists())

    def test_05_category_must_match_owner(self):
        with self.assertRaisesRegex(ValueError, "category"):
            self.upload_student_document(
                category="drivers_license",
            )

        self.assertFalse(self.storage_path.exists())

    def test_06_unsupported_owner_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.upload_student_document(
                owner_type="school",
            )

        self.assertFalse(self.storage_path.exists())

    # --------------------------------------------------
    # RETRIEVAL AND SEARCH
    # --------------------------------------------------

    def test_07_get_existing_document(self):
        created = self.upload_student_document()

        document = get_document(
            created["id"],
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(document)
        self.assertEqual(document["id"], created["id"])

    def test_08_get_missing_document(self):
        self.assertIsNone(
            get_document(
                999999,
                actor_user_id=self.admin_id,
            )
        )

    def test_09_staff_can_view_documents(self):
        created = self.upload_student_document()

        document = get_document(
            created["id"],
            actor_user_id=self.staff_id,
        )

        self.assertIsNotNone(document)

    def test_10_search_by_title_filename_and_description(self):
        self.upload_student_document()

        title_results = get_documents(
            "Birth Certificate",
            actor_user_id=self.admin_id,
        )

        description_results = get_documents(
            "Student birth",
            actor_user_id=self.admin_id,
        )

        filename_results = get_documents(
            "certificate.pdf",
            actor_user_id=self.admin_id,
        )

        self.assertEqual(len(title_results), 1)
        self.assertEqual(len(description_results), 1)
        self.assertEqual(len(filename_results), 1)

    def test_11_filter_by_owner_and_category(self):
        self.upload_student_document()

        results = get_documents(
            owner_type="student",
            owner_id=self.student_id,
            category="birth_certificate",
            actor_user_id=self.admin_id,
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0]["student_id"],
            self.student_id,
        )

    def test_12_filter_by_owner_type(self):
        self.upload_student_document()

        results = get_documents(
            owner_type="student",
            actor_user_id=self.admin_id,
        )

        self.assertEqual(len(results), 1)

    def test_13_owner_id_requires_owner_type(self):
        with self.assertRaisesRegex(ValueError, "Owner type"):
            get_documents(
                owner_id=self.student_id,
                actor_user_id=self.admin_id,
            )

    def test_14_invalid_document_filters_are_rejected(self):
        invalid_filters = [
            {"owner_type": "unknown"},
            {"category": "unknown"},
            {"status": "deleted"},
            {"search": None},
        ]

        for filters in invalid_filters:
            with self.subTest(filters=filters):
                with self.assertRaises(ValueError):
                    get_documents(
                        actor_user_id=self.admin_id,
                        **filters,
                    )

    # --------------------------------------------------
    # FILE ACCESS AND INTEGRITY
    # --------------------------------------------------

    def test_15_open_document_returns_verified_stream(self):
        created = self.upload_student_document()

        with open_document(
            created["id"],
            actor_user_id=self.admin_id,
            storage=self.storage,
        ) as document_file:
            content = document_file.read()

        self.assertEqual(content, PDF_CONTENT)

    def test_16_open_document_rejects_modified_file(self):
        created = self.upload_student_document()

        stored_path = (
            self.storage_path / created["storage_key"]
        )

        stored_path.write_bytes(
            b"%PDF-1.4\nmodified document"
        )

        with self.assertRaisesRegex(ValueError, "integrity"):
            open_document(
                created["id"],
                actor_user_id=self.admin_id,
                storage=self.storage,
            )

    def test_17_verify_document_returns_true_for_valid_file(self):
        created = self.upload_student_document()

        self.assertTrue(
            verify_document(
                created["id"],
                actor_user_id=self.admin_id,
                storage=self.storage,
            )
        )

    def test_18_verify_document_detects_modification(self):
        created = self.upload_student_document()

        stored_path = (
            self.storage_path / created["storage_key"]
        )

        stored_path.write_bytes(
            b"%PDF-1.4\nmodified document"
        )

        self.assertFalse(
            verify_document(
                created["id"],
                actor_user_id=self.admin_id,
                storage=self.storage,
            )
        )

    # --------------------------------------------------
    # ARCHIVING
    # --------------------------------------------------

    def test_19_admin_can_archive_document(self):
        created = self.upload_student_document()

        archived = archive_document(
            created["id"],
            actor_user_id=self.admin_id,
        )

        self.assertEqual(archived["status"], "archived")
        self.assertEqual(archived["archived_by"], self.admin_id)
        self.assertIsNotNone(archived["archived_at"])

        # Archiving must preserve the physical file.
        self.assertTrue(
            (self.storage_path / created["storage_key"]).is_file()
        )

    def test_20_staff_cannot_archive_document(self):
        created = self.upload_student_document()

        with self.assertRaises(PermissionError):
            archive_document(
                created["id"],
                actor_user_id=self.staff_id,
            )

        document = get_document(
            created["id"],
            actor_user_id=self.admin_id,
        )

        self.assertEqual(document["status"], "active")

    def test_21_archived_documents_are_excluded_by_default(self):
        created = self.upload_student_document()

        archive_document(
            created["id"],
            actor_user_id=self.admin_id,
        )

        active = get_documents(
            actor_user_id=self.admin_id,
        )

        archived = get_documents(
            status="archived",
            actor_user_id=self.admin_id,
        )

        all_documents = get_documents(
            status=None,
            actor_user_id=self.admin_id,
        )

        self.assertEqual(active, [])
        self.assertEqual(len(archived), 1)
        self.assertEqual(len(all_documents), 1)

    def test_22_archived_document_cannot_be_archived_again(self):
        created = self.upload_student_document()

        archive_document(
            created["id"],
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "already archived"):
            archive_document(
                created["id"],
                actor_user_id=self.admin_id,
            )

    # --------------------------------------------------
    # AUTHORIZATION
    # --------------------------------------------------

    def test_23_inactive_user_cannot_view_documents(self):
        created = self.upload_student_document()

        update_user_status(
            self.staff_id,
            False,
            self.admin_id,
        )

        with self.assertRaises(PermissionError):
            get_document(
                created["id"],
                actor_user_id=self.staff_id,
            )

    def test_24_staff_cannot_archive_even_when_metadata_is_accessible(self):
        created = self.upload_student_document()

        self.assertIsNotNone(
            get_document(
                created["id"],
                actor_user_id=self.staff_id,
            )
        )

        with self.assertRaises(PermissionError):
            archive_document(
                created["id"],
                actor_user_id=self.staff_id,
            )

    # --------------------------------------------------
    # FAILURE CLEANUP
    # --------------------------------------------------

    def test_25_database_insert_failure_removes_uploaded_file(self):
        with get_connection() as connection:
            connection.execute("""
                CREATE TRIGGER fail_document_registration
                BEFORE INSERT ON documents
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'Simulated document registration failure'
                    );
                END;
            """)

        with self.assertRaises(sqlite3.IntegrityError):
            self.upload_student_document()

        remaining_files = [
            path
            for path in self.storage_path.rglob("*")
            if path.is_file()
        ]

        self.assertEqual(remaining_files, [])

    def test_26_model_validation_failure_removes_uploaded_file(self):
        with self.assertRaisesRegex(ValueError, "title"):
            self.upload_student_document(
                title=" " * 10,
            )

        remaining_files = [
            path
            for path in self.storage_path.rglob("*")
            if path.is_file()
        ]

        self.assertEqual(remaining_files, [])

    def test_27_upload_by_inactive_user_is_rejected(self):
        update_user_status(
            self.staff_id,
            False,
            self.admin_id,
        )

        with self.assertRaises(PermissionError):
            self.upload_student_document(
                actor_user_id=self.staff_id,
            )

        self.assertFalse(self.storage_path.exists())


if __name__ == "__main__":
    unittest.main()
