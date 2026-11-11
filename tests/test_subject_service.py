import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from models.subject import Subject
from services.subject_service import (
    create_subject,
    get_subject,
    get_subjects,
    update_subject,
    update_subject_status,
)


def sample_subject(**overrides):
    data = {
        "subject_code": "MATH101",
        "name": "Mathematics",
        "description": "Mathematics and problem solving",
        "status": "active",
    }
    data.update(overrides)
    return data


from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
class SubjectServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temp_directory.name) / "test_school.db"
        )

        self.db_path_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path,
        )
        self.db_path_patcher.start()

        self.addCleanup(self.db_path_patcher.stop)
        self.addCleanup(self.temp_directory.cleanup)

        initialize_database()
        create_initial_admin("admin1", "AdminPass123", "Test Administrator")
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]
        self.staff_id = create_user(
            "staff1", "StaffPass123", "Test Staff", "staff", self.admin_id
        )

    def test_01_create_and_retrieve_subject(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)
        subject = get_subject(subject_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(subject)
        self.assertEqual(subject["subject_code"], "MATH101")
        self.assertEqual(subject["name"], "Mathematics")
        self.assertEqual(
            subject["description"],
            "Mathematics and problem solving",
        )
        self.assertEqual(subject["status"], "active")

    def test_02_normalize_subject_data(self):
        subject_id = create_subject(
            sample_subject(
                subject_code=" math201 ",
                name=" Mathematics Advanced ",
                description=" Advanced mathematics ",
            )
        , actor_user_id=self.admin_id)

        subject = get_subject(subject_id, actor_user_id=self.admin_id)

        self.assertEqual(subject["subject_code"], "MATH201")
        self.assertEqual(subject["name"], "Mathematics Advanced")
        self.assertEqual(
            subject["description"],
            "Advanced mathematics",
        )

    def test_03_allow_optional_description(self):
        subject_id = create_subject(
            sample_subject(description="")
        , actor_user_id=self.admin_id)

        self.assertIsNone(get_subject(subject_id, actor_user_id=self.admin_id)["description"])

    def test_04_reject_invalid_subject_data(self):
        invalid_cases = [
            ("missing code", {"subject_code": ""}),
            ("whitespace code", {"subject_code": "   "}),
            ("long code", {"subject_code": "A" * 31}),
            ("non-text code", {"subject_code": 123}),
            ("missing name", {"name": ""}),
            ("whitespace name", {"name": "   "}),
            ("long name", {"name": "A" * 151}),
            ("non-text name", {"name": 123}),
            ("non-text description", {"description": 123}),
            ("long description", {"description": "A" * 501}),
            ("invalid status", {"status": "deleted"}),
        ]

        for label, overrides in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    Subject(
                        **sample_subject(**overrides)
                    ).validate()

        self.assertEqual(get_subjects(actor_user_id=self.admin_id), [])

    def test_05_reject_duplicate_subject_code(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "subject code already exists",
        ):
            create_subject(
                sample_subject(
                    subject_code="math101",
                    name="Different Subject",
                )
            , actor_user_id=self.admin_id)

        self.assertEqual(len(get_subjects(actor_user_id=self.admin_id)), 1)

    def test_06_reject_duplicate_subject_name(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "subject name already exists",
        ):
            create_subject(
                sample_subject(
                    subject_code="MATH102",
                    name="mathematics",
                )
            , actor_user_id=self.admin_id)

        self.assertEqual(len(get_subjects(actor_user_id=self.admin_id)), 1)

    def test_07_retrieve_missing_subject(self):
        self.assertIsNone(get_subject(999999, actor_user_id=self.admin_id))

    def test_08_reject_invalid_subject_ids(self):
        for invalid_id in (0, -1, "invalid", None, True):
            with self.subTest(subject_id=invalid_id):
                with self.assertRaises(ValueError):
                    get_subject(invalid_id, actor_user_id=self.admin_id)

    def test_09_search_by_code_name_and_description(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        create_subject(
            sample_subject(
                subject_code="SCI101",
                name="Science",
                description="General science",
            )
        , actor_user_id=self.admin_id)

        self.assertEqual(len(get_subjects("MATH101", actor_user_id=self.admin_id)), 1)
        self.assertEqual(len(get_subjects("Science", actor_user_id=self.admin_id)), 1)
        self.assertEqual(len(get_subjects("problem solving", actor_user_id=self.admin_id)), 1)
        self.assertEqual(len(get_subjects("not-found", actor_user_id=self.admin_id)), 0)

    def test_10_filter_by_status(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        create_subject(
            sample_subject(
                subject_code="SCI101",
                name="Science",
                status="inactive",
            )
        , actor_user_id=self.admin_id)

        self.assertEqual(len(get_subjects(status="active", actor_user_id=self.admin_id)), 1)
        self.assertEqual(len(get_subjects(status="inactive", actor_user_id=self.admin_id)), 1)

    def test_11_reject_invalid_status_filter(self):
        with self.assertRaisesRegex(ValueError, "status filter"):
            get_subjects(status="deleted", actor_user_id=self.admin_id)

    def test_12_update_subject(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        update_subject(
            subject_id,
            sample_subject(
                subject_code="MATH102",
                name="Advanced Mathematics",
                description="Updated description",
            ),
         actor_user_id=self.admin_id)

        subject = get_subject(subject_id, actor_user_id=self.admin_id)

        self.assertEqual(subject["subject_code"], "MATH102")
        self.assertEqual(subject["name"], "Advanced Mathematics")
        self.assertEqual(
            subject["description"],
            "Updated description",
        )

    def test_13_reject_duplicate_code_during_update(self):
        first_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        create_subject(
            sample_subject(
                subject_code="SCI101",
                name="Science",
            )
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "code already exists"):
            update_subject(
                first_id,
                sample_subject(subject_code="SCI101"),
             actor_user_id=self.admin_id)

        self.assertEqual(
            get_subject(first_id, actor_user_id=self.admin_id)["subject_code"],
            "MATH101",
        )

    def test_14_reject_duplicate_name_during_update(self):
        first_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        create_subject(
            sample_subject(
                subject_code="SCI101",
                name="Science",
            )
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "name already exists"):
            update_subject(
                first_id,
                sample_subject(name="Science"),
             actor_user_id=self.admin_id)

        self.assertEqual(
            get_subject(first_id, actor_user_id=self.admin_id)["name"],
            "Mathematics",
        )

    def test_15_reject_update_for_missing_subject(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found",
        ):
            update_subject(999999, sample_subject(), actor_user_id=self.admin_id)

    def test_16_reject_invalid_update_without_modifying_record(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        with self.assertRaises(ValueError):
            update_subject(
                subject_id,
                sample_subject(name=""),
             actor_user_id=self.admin_id)

        self.assertEqual(
            get_subject(subject_id, actor_user_id=self.admin_id)["name"],
            "Mathematics",
        )

    def test_17_deactivate_and_reactivate_subject(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        update_subject_status(subject_id, "inactive", actor_user_id=self.admin_id)
        self.assertEqual(
            get_subject(subject_id, actor_user_id=self.admin_id)["status"],
            "inactive",
        )

        update_subject_status(subject_id, "active", actor_user_id=self.admin_id)
        self.assertEqual(
            get_subject(subject_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_18_reject_invalid_subject_status_change(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "status"):
            update_subject_status(subject_id, "deleted", actor_user_id=self.admin_id)

        self.assertEqual(
            get_subject(subject_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_19_reject_status_change_for_missing_subject(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found",
        ):
            update_subject_status(999999, "inactive", actor_user_id=self.admin_id)

    def test_20_database_enforces_unique_subject_fields(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO subjects (
                            subject_code, name
                        )
                        VALUES (?, ?)
                        """,
                        ("math101", "Another Subject"),
                    )

    def test_21_database_prevents_subject_deletion(self):
        subject_id = create_subject(sample_subject(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        "DELETE FROM subjects WHERE id = ?",
                        (subject_id,),
                    )

        self.assertIsNotNone(get_subject(subject_id, actor_user_id=self.admin_id))

    def test_22_sqlite_database_integrity(self):
        create_subject(sample_subject(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    def test_23_staff_can_read_but_cannot_modify_subjects(self):
        subject_id = create_subject(
            sample_subject(),
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(
            get_subject(subject_id, actor_user_id=self.staff_id)
        )
        self.assertEqual(
            len(get_subjects(actor_user_id=self.staff_id)),
            1,
        )

        with self.assertRaises(PermissionError):
            create_subject(
                sample_subject(subject_code="SCI101", name="Science"),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_subject(
                subject_id,
                sample_subject(name="Modified Mathematics"),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_subject_status(
                subject_id,
                "inactive",
                actor_user_id=self.staff_id,
            )

        unchanged = get_subject(subject_id, actor_user_id=self.admin_id)
        self.assertEqual(unchanged["name"], "Mathematics")
        self.assertEqual(unchanged["status"], "active")


if __name__ == "__main__":
    unittest.main(verbosity=2)
