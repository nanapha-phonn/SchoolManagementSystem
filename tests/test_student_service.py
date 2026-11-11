import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user, update_user_status
from models.student import VALID_STATUSES
from services.student_service import (
    create_student,
    get_student,
    get_students,
    update_student,
    update_student_status,
)


def sample_student(**overrides):
    data = {
        "admission_no": "STU-1001",
        "first_name": "Alian",
        "last_name": "Elle",
        "date_of_birth": "2010-05-15",
        "gender": "Male",
        "phone": "012345678",
        "email": "alian@example.com",
        "address": "Phnom Penh",
        "guardian_name": "Parent Elle",
        "guardian_phone": "098765432",
        "status": "active",
    }
    data.update(overrides)
    return data


class StudentServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test_school.db"

        self.db_path_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path
        )
        self.db_path_patcher.start()

        self.addCleanup(self.db_path_patcher.stop)
        self.addCleanup(self.temp_directory.cleanup)

        initialize_database()

        create_initial_admin(
            "admin1", "AdminPass123", "Test Administrator"
        )
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]

    def test_01_create_and_persist_student(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        # get_student opens a separate database connection.
        student = get_student(student_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(student)
        self.assertEqual(student["admission_no"], "STU-1001")
        self.assertEqual(student["first_name"], "Alian")
        self.assertEqual(student["last_name"], "Elle")
        self.assertEqual(student["status"], "active")
        self.assertIsNotNone(student["created_at"])

    def test_02_reject_duplicate_admission_number(self):
        create_student(sample_student(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "admission number already exists"
        ):
            create_student(sample_student(), actor_user_id=self.admin_id)

    def test_03_reject_invalid_student_data(self):
        invalid_cases = [
            ("empty admission number", {"admission_no": ""}),
            ("empty first name", {"first_name": ""}),
            ("empty last name", {"last_name": ""}),
            ("invalid date", {"date_of_birth": "15-05-2010"}),
            ("future date", {"date_of_birth": "2999-01-01"}),
            ("invalid gender", {"gender": "Unknown"}),
            ("invalid email", {"email": "not-an-email"}),
            ("invalid phone", {"phone": "abc123"}),
            ("invalid guardian phone", {"guardian_phone": "abc123"}),
            ("invalid status", {"status": "unknown"}),
            ("long admission number", {"admission_no": "A" * 31}),
            ("long student name", {"first_name": "A" * 101}),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                with self.assertRaises(ValueError):
                    create_student(sample_student(**overrides), actor_user_id=self.admin_id)

        self.assertEqual(len(get_students(actor_user_id=self.admin_id)), 0)

    def test_04_retrieve_missing_student(self):
        self.assertIsNone(get_student(999999, actor_user_id=self.admin_id))

    def test_05_search_by_admission_and_name(self):
        create_student(sample_student(), actor_user_id=self.admin_id)

        admission_results = get_students("STU-1001", actor_user_id=self.admin_id)
        first_name_results = get_students("Alian", actor_user_id=self.admin_id)
        last_name_results = get_students("Elle", actor_user_id=self.admin_id)
        partial_results = get_students("STU-10", actor_user_id=self.admin_id)

        self.assertEqual(len(admission_results), 1)
        self.assertEqual(len(first_name_results), 1)
        self.assertEqual(len(last_name_results), 1)
        self.assertEqual(len(partial_results), 1)

        self.assertEqual(
            admission_results[0]["admission_no"],
            "STU-1001"
        )

    def test_06_update_student(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        updated_data = sample_student(
            first_name="Updated",
            last_name="Student",
            phone="011223344",
        )

        update_student(student_id, updated_data, actor_user_id=self.admin_id)

        student = get_student(student_id, actor_user_id=self.admin_id)

        self.assertEqual(student["first_name"], "Updated")
        self.assertEqual(student["last_name"], "Student")
        self.assertEqual(student["phone"], "011223344")

    def test_07_reject_duplicate_admission_number_during_update(self):
        first_id = create_student(sample_student(), actor_user_id=self.admin_id)

        create_student(
            sample_student(
                admission_no="STU-1002",
                first_name="Second",
                last_name="Student",
            ),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(
            ValueError,
            "admission number already exists"
        ):
            update_student(
                first_id,
                sample_student(admission_no="STU-1002"),
                actor_user_id=self.admin_id,
            )

        # The failed update must not overwrite the original record.
        self.assertEqual(
            get_student(first_id, actor_user_id=self.admin_id)["admission_no"],
            "STU-1001"
        )

    def test_08_reject_update_with_invalid_data(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        with self.assertRaises(ValueError):
            update_student(
                student_id,
                sample_student(email="invalid-email"),
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_student(student_id, actor_user_id=self.admin_id)["email"],
            "alian@example.com"
        )

    def test_09_reject_update_for_missing_student(self):
        with self.assertRaisesRegex(
            ValueError,
            "Student record was not found"
        ):
            update_student(
                999999,
                sample_student(),
                actor_user_id=self.admin_id,
            )

    def test_10_test_all_valid_status_changes(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        for status in sorted(VALID_STATUSES):
            with self.subTest(status=status):
                update_student_status(student_id, status, actor_user_id=self.admin_id)

                student = get_student(student_id, actor_user_id=self.admin_id)

                self.assertIsNotNone(student)
                self.assertEqual(student["status"], status)

    def test_11_reject_invalid_status_change(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "Invalid student status"
        ):
            update_student_status(student_id, "deleted", actor_user_id=self.admin_id)

        self.assertEqual(
            get_student(student_id, actor_user_id=self.admin_id)["status"],
            "active"
        )

    def test_12_reject_status_change_for_missing_student(self):
        with self.assertRaisesRegex(
            ValueError,
            "Student record was not found"
        ):
            update_student_status(999999, "inactive", actor_user_id=self.admin_id)

    def test_13_preserve_creation_timestamp(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        original = get_student(student_id, actor_user_id=self.admin_id)
        original_timestamp = original["created_at"]

        update_student(
            student_id,
            sample_student(first_name="Changed"),
            actor_user_id=self.admin_id,
        )

        updated = get_student(student_id, actor_user_id=self.admin_id)

        self.assertEqual(
            updated["created_at"],
            original_timestamp
        )

    def test_14_status_change_preserves_student_record(self):
        student_id = create_student(sample_student(), actor_user_id=self.admin_id)

        original = get_student(student_id, actor_user_id=self.admin_id)

        update_student_status(student_id, "graduated", actor_user_id=self.admin_id)

        updated = get_student(student_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(updated)
        self.assertEqual(updated["id"], original["id"])
        self.assertEqual(
            updated["admission_no"],
            original["admission_no"]
        )
        self.assertEqual(updated["status"], "graduated")
        self.assertEqual(len(get_students(actor_user_id=self.admin_id)), 1)

    def test_15_staff_can_use_student_service(self):
        staff_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id
        )

        student_id = create_student(
            sample_student(),
            actor_user_id=staff_id
        )

        self.assertIsNotNone(
            get_student(student_id, actor_user_id=staff_id)
        )
        self.assertEqual(
            len(get_students(actor_user_id=staff_id)),
            1
        )

        update_student(
            student_id,
            sample_student(first_name="StaffUpdated"),
            actor_user_id=staff_id
        )

        update_student_status(
            student_id,
            "inactive",
            actor_user_id=staff_id
        )

        student = get_student(student_id, actor_user_id=staff_id)
        self.assertEqual(student["first_name"], "StaffUpdated")
        self.assertEqual(student["status"], "inactive")

    def test_16_missing_and_inactive_actors_are_rejected(self):
        operations = [
            lambda actor_id: create_student(
                sample_student(),
                actor_user_id=actor_id
            ),
            lambda actor_id: get_student(
                999999,
                actor_user_id=actor_id
            ),
            lambda actor_id: get_students(actor_user_id=actor_id),
            lambda actor_id: update_student(
                999999,
                sample_student(),
                actor_user_id=actor_id
            ),
            lambda actor_id: update_student_status(
                999999,
                "inactive",
                actor_user_id=actor_id
            ),
        ]

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(PermissionError):
                    operation(999999)

        staff_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id
        )
        update_user_status(staff_id, False, self.admin_id)

        for operation in operations:
            with self.subTest(operation=operation, actor="inactive"):
                with self.assertRaises(PermissionError):
                    operation(staff_id)

    def test_17_sqlite_database_integrity(self):
        create_student(sample_student(), actor_user_id=self.admin_id)

        from contextlib import closing

        with closing(database_module.get_connection()) as connection:
            integrity_result = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_key_results = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity_result, "ok")
        self.assertEqual(foreign_key_results, [])

    def test_18_database_enforces_duplicate_constraint(self):
        create_student(sample_student(), actor_user_id=self.admin_id)

        from contextlib import closing
        import sqlite3

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
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
                        ("STU-1001", "Duplicate", "Student")
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
