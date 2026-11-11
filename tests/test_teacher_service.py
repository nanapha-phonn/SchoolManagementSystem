import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from services.auth_service import (
    create_initial_admin,
    authenticate_user,
)
from services.user_service import create_user

from services.teacher_service import (
    create_teacher,
    get_teacher,
    get_teachers,
    search_teachers,
    update_teacher,
    update_teacher_status,
)


class TestTeacherService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_school.db"

        self.db_patcher = patch.object(
            database_module, "DB_PATH", str(self.db_path)
        )
        self.db_patcher.start()
        database_module.initialize_database()

        create_initial_admin(
            "admin1", "AdminPass123", "Test Administrator"
        )
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]
        self.staff_id = create_user(
            "staff1", "StaffPass123", "Test Staff",
            "staff", self.admin_id
        )

    def tearDown(self):
        self.db_patcher.stop()
        self.temp_dir.cleanup()

    def teacher_data(self, **overrides):
        data = {
            "employee_no": "TCH-001",
            "first_name": "John",
            "last_name": "Smith",
            "date_of_birth": "1990-05-15",
            "gender": "Male",
            "phone": "012345678",
            "email": "john@example.com",
            "address": "Phnom Penh",
            "qualification": "Bachelor of Education",
            "specialization": "Mathematics",
            "department": "Science",
            "employment_date": "2020-01-10",
            "status": "active",
        }
        data.update(overrides)
        return data

    def test_create_and_retrieve_teacher(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        teacher = get_teacher(teacher_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(teacher)
        self.assertEqual(teacher["employee_no"], "TCH-001")
        self.assertEqual(teacher["first_name"], "John")
        self.assertEqual(teacher["department"], "Science")
        self.assertEqual(teacher["status"], "active")

    def test_duplicate_employee_number_rejected(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "already exists"):
            create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

    def test_invalid_teacher_data_rejected(self):
        invalid_cases = [
            {"employee_no": ""},
            {"first_name": ""},
            {"last_name": ""},
            {"employee_no": "X" * 31},
            {"first_name": "A" * 101},
            {"last_name": "B" * 101},
            {"date_of_birth": "15-05-1990"},
            {"date_of_birth": "2999-01-01"},
            {"employment_date": "2999-01-01"},
            {"gender": "Unknown"},
            {"email": "invalid-email"},
            {"phone": "abc123"},
            {"status": "unknown"},
            {"date_of_birth": "2000-01-01",
             "employment_date": "1999-01-01"},
            {"address": "A" * 501},
            {"qualification": "Q" * 151},
            {"specialization": "S" * 151},
            {"department": "D" * 101},
        ]

        for invalid_data in invalid_cases:
            with self.subTest(invalid_data=invalid_data):
                with self.assertRaises(ValueError):
                    create_teacher(self.teacher_data(**invalid_data), actor_user_id=self.admin_id)

    def test_get_missing_teacher_returns_none(self):
        self.assertIsNone(get_teacher(9999, actor_user_id=self.admin_id))

    def test_get_all_teachers(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)
        create_teacher(self.teacher_data(
            employee_no="TCH-002",
            first_name="Alice",
            last_name="Brown",
        ), actor_user_id=self.admin_id)

        teachers = get_teachers(actor_user_id=self.admin_id)

        self.assertEqual(len(teachers), 2)

    def test_search_by_employee_number(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        results = search_teachers("TCH-001", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["employee_no"], "TCH-001")

    def test_search_by_name(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        results = search_teachers("John", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["first_name"], "John")

    def test_search_by_department(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        results = search_teachers("Science", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)

    def test_search_without_match_returns_empty_list(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        self.assertEqual(search_teachers("NotFound", actor_user_id=self.admin_id), [])

    def test_update_teacher(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        updated_data = self.teacher_data(
            first_name="Jonathan",
            department="Mathematics",
        )
        update_teacher(teacher_id, updated_data, actor_user_id=self.admin_id)

        teacher = get_teacher(teacher_id, actor_user_id=self.admin_id)

        self.assertEqual(teacher["first_name"], "Jonathan")
        self.assertEqual(teacher["department"], "Mathematics")

    def test_duplicate_employee_number_update_rejected(self):
        first_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)
        create_teacher(self.teacher_data(
            employee_no="TCH-002",
            first_name="Alice",
            last_name="Brown",
        ), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "already exists"):
            update_teacher(
                first_id,
                self.teacher_data(employee_no="TCH-002"),
                actor_user_id=self.admin_id,
            )

        # Original record must remain unchanged.
        self.assertEqual(
            get_teacher(first_id, actor_user_id=self.admin_id)["employee_no"],
            "TCH-001",
        )

    def test_invalid_update_does_not_modify_record(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        with self.assertRaises(ValueError):
            update_teacher(
                teacher_id,
                self.teacher_data(email="invalid-email"),
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_teacher(teacher_id, actor_user_id=self.admin_id)["email"],
            "john@example.com",
        )

    def test_update_missing_teacher_rejected(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            update_teacher(9999, self.teacher_data(), actor_user_id=self.admin_id)

    def test_update_all_valid_statuses(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        for status in ("inactive", "resigned", "terminated", "active"):
            with self.subTest(status=status):
                update_teacher_status(teacher_id, status, actor_user_id=self.admin_id)
                self.assertEqual(
                    get_teacher(teacher_id, actor_user_id=self.admin_id)["status"],
                    status,
                )

    def test_invalid_status_rejected(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        with self.assertRaises(ValueError):
            update_teacher_status(teacher_id, "unknown", actor_user_id=self.admin_id)

        self.assertEqual(
            get_teacher(teacher_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_status_update_for_missing_teacher_rejected(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            update_teacher_status(9999, "inactive", actor_user_id=self.admin_id)

    def test_created_at_preserved_after_update(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)
        original_created_at = get_teacher(teacher_id, actor_user_id=self.admin_id)["created_at"]

        update_teacher(
            teacher_id,
            self.teacher_data(first_name="Updated"),
            actor_user_id=self.admin_id,
        )

        self.assertEqual(
            get_teacher(teacher_id, actor_user_id=self.admin_id)["created_at"],
            original_created_at,
        )

    def test_status_change_preserves_teacher_record(self):
        teacher_id = create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        update_teacher_status(teacher_id, "inactive", actor_user_id=self.admin_id)
        teacher = get_teacher(teacher_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(teacher)
        self.assertEqual(teacher["employee_no"], "TCH-001")
        self.assertEqual(teacher["first_name"], "John")

    def test_database_integrity(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        with sqlite3.connect(self.db_path) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])

    def test_database_unique_constraint(self):
        create_teacher(self.teacher_data(), actor_user_id=self.admin_id)

        with sqlite3.connect(self.db_path) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO teachers (
                        employee_no, first_name, last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("TCH-001", "Another", "Teacher"),
                )


    def test_staff_can_manage_teacher_records(self):
        teacher_id = create_teacher(
            self.teacher_data(),
            actor_user_id=self.staff_id,
        )

        teacher = get_teacher(
            teacher_id,
            actor_user_id=self.staff_id,
        )
        self.assertEqual(teacher["first_name"], "John")

        self.assertEqual(
            len(get_teachers(actor_user_id=self.staff_id)),
            1,
        )
        self.assertEqual(
            len(search_teachers(
                "TCH-001",
                actor_user_id=self.staff_id,
            )),
            1,
        )

        update_teacher(
            teacher_id,
            self.teacher_data(first_name="Jonathan"),
            actor_user_id=self.staff_id,
        )
        self.assertEqual(
            get_teacher(
                teacher_id,
                actor_user_id=self.staff_id,
            )["first_name"],
            "Jonathan",
        )

        update_teacher_status(
            teacher_id,
            "inactive",
            actor_user_id=self.staff_id,
        )
        self.assertEqual(
            get_teacher(
                teacher_id,
                actor_user_id=self.staff_id,
            )["status"],
            "inactive",
        )

    def test_invalid_actor_cannot_access_teacher_records(self):
        teacher_id = create_teacher(
            self.teacher_data(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaises(PermissionError):
            create_teacher(
                self.teacher_data(
                    employee_no="TCH-002",
                    first_name="Unauthorized",
                ),
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            get_teacher(teacher_id, actor_user_id=None)

        with self.assertRaises(PermissionError):
            get_teachers(actor_user_id=None)

        with self.assertRaises(PermissionError):
            search_teachers("John", actor_user_id=None)

        with self.assertRaises(PermissionError):
            update_teacher(
                teacher_id,
                self.teacher_data(first_name="Unauthorized"),
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            update_teacher_status(
                teacher_id,
                "inactive",
                actor_user_id=None,
            )

        # Denied operations must not create or alter records.
        teacher = get_teacher(
            teacher_id,
            actor_user_id=self.admin_id,
        )
        self.assertEqual(teacher["first_name"], "John")
        self.assertEqual(teacher["status"], "active")
        self.assertEqual(
            len(get_teachers(actor_user_id=self.admin_id)),
            1,
        )


if __name__ == "__main__":
    unittest.main()
