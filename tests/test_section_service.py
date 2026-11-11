import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from models.section import Section
from services.class_service import create_class
from services.section_service import (
    create_section,
    get_section,
    get_sections,
    update_section,
)


def sample_section(**overrides):
    data = {
        "class_id": 1,
        "name": "A",
    }
    data.update(overrides)
    return data


from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
class SectionServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()

        self.database_path = (
            Path(self.temp_directory.name) / "test_school.db"
        )

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
        self.staff_id = create_user(
            "staff1", "StaffPass123", "Test Staff", "staff", self.admin_id
        )

        self.class_one = create_class({
            "name": "Grade 1",
            "description": "First grade",
        }, actor_user_id=self.admin_id)

        self.class_two = create_class({
            "name": "Grade 2",
            "description": "Second grade",
        }, actor_user_id=self.admin_id)

    def test_01_create_and_retrieve_section(self):
        section_id = create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        section = get_section(section_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(section)
        self.assertEqual(section["class_id"], self.class_one)
        self.assertEqual(section["name"], "A")
        self.assertEqual(section["class_name"], "Grade 1")

    def test_02_normalize_section_name(self):
        section_id = create_section(
            sample_section(
                class_id=self.class_one,
                name="  Section B  "
            )
        , actor_user_id=self.admin_id)

        self.assertEqual(
            get_section(section_id, actor_user_id=self.admin_id)["name"],
            "Section B"
        )

    def test_03_reject_invalid_section_data(self):
        invalid_cases = [
            ("zero class ID", {"class_id": 0}),
            ("negative class ID", {"class_id": -1}),
            ("invalid class ID", {"class_id": "invalid"}),
            ("boolean class ID", {"class_id": True}),
            ("empty name", {"name": ""}),
            ("whitespace name", {"name": "   "}),
            ("long name", {"name": "A" * 101}),
            ("non-text name", {"name": 123}),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                with self.assertRaises(ValueError):
                    data = sample_section(
                        class_id=self.class_one
                    )
                    data.update(overrides)

                    Section(**data).validate()

        self.assertEqual(len(get_sections(actor_user_id=self.admin_id)), 0)

    def test_04_reject_section_for_missing_class(self):
        with self.assertRaisesRegex(
            ValueError,
            "Selected class was not found"
        ):
            create_section(
                sample_section(class_id=999999)
            , actor_user_id=self.admin_id)

        self.assertEqual(len(get_sections(actor_user_id=self.admin_id)), 0)

    def test_05_reject_duplicate_name_within_class(self):
        create_section(
            sample_section(class_id=self.class_one, name="A")
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            create_section(
                sample_section(class_id=self.class_one, name="A")
            , actor_user_id=self.admin_id)

        self.assertEqual(len(get_sections(actor_user_id=self.admin_id)), 1)

    def test_06_same_name_allowed_in_different_classes(self):
        first_id = create_section(
            sample_section(class_id=self.class_one, name="A")
        , actor_user_id=self.admin_id)

        second_id = create_section(
            sample_section(class_id=self.class_two, name="A")
        , actor_user_id=self.admin_id)

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(len(get_sections(actor_user_id=self.admin_id)), 2)

    def test_07_retrieve_missing_section(self):
        self.assertIsNone(get_section(999999, actor_user_id=self.admin_id))

    def test_08_search_by_section_name(self):
        create_section(
            sample_section(class_id=self.class_one, name="Alpha")
        , actor_user_id=self.admin_id)

        create_section(
            sample_section(class_id=self.class_one, name="Beta")
        , actor_user_id=self.admin_id)

        results = get_sections("Alpha", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alpha")

    def test_09_search_by_class_name(self):
        create_section(
            sample_section(class_id=self.class_one, name="A")
        , actor_user_id=self.admin_id)

        create_section(
            sample_section(class_id=self.class_two, name="B")
        , actor_user_id=self.admin_id)

        results = get_sections("Grade 2", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["class_name"], "Grade 2")

    def test_10_search_without_match(self):
        create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        self.assertEqual(
            get_sections("not-found", actor_user_id=self.admin_id),
            []
        )

    def test_11_filter_sections_by_class(self):
        create_section(
            sample_section(class_id=self.class_one, name="A")
        , actor_user_id=self.admin_id)

        create_section(
            sample_section(class_id=self.class_two, name="B")
        , actor_user_id=self.admin_id)

        results = get_sections(class_id=self.class_two, actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "B")

    def test_12_update_section_name(self):
        section_id = create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        update_section(
            section_id,
            sample_section(
                class_id=self.class_one,
                name="Updated Section"
            )
        , actor_user_id=self.admin_id)

        section = get_section(section_id, actor_user_id=self.admin_id)

        self.assertEqual(
            section["name"],
            "Updated Section"
        )

    def test_13_move_section_to_another_class(self):
        section_id = create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        update_section(
            section_id,
            sample_section(
                class_id=self.class_two,
                name="A"
            )
        , actor_user_id=self.admin_id)

        section = get_section(section_id, actor_user_id=self.admin_id)

        self.assertEqual(section["class_id"], self.class_two)
        self.assertEqual(section["class_name"], "Grade 2")

    def test_14_reject_duplicate_name_during_update(self):
        first_id = create_section(
            sample_section(class_id=self.class_one, name="A")
        , actor_user_id=self.admin_id)

        create_section(
            sample_section(class_id=self.class_one, name="B")
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            update_section(
                first_id,
                sample_section(
                    class_id=self.class_one,
                    name="B"
                )
            , actor_user_id=self.admin_id)

        self.assertEqual(
            get_section(first_id, actor_user_id=self.admin_id)["name"],
            "A"
        )

    def test_15_reject_update_for_missing_section(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found"
        ):
            update_section(
                999999,
                sample_section(class_id=self.class_one)
            , actor_user_id=self.admin_id)

    def test_16_reject_update_with_missing_class(self):
        section_id = create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "Selected class was not found"
        ):
            update_section(
                section_id,
                sample_section(class_id=999999)
            , actor_user_id=self.admin_id)

        self.assertEqual(
            get_section(section_id, actor_user_id=self.admin_id)["class_id"],
            self.class_one
        )

    def test_17_reject_invalid_section_ids(self):
        for invalid_id in (0, -1, "invalid", None, True):
            with self.subTest(section_id=invalid_id):
                with self.assertRaises(ValueError):
                    get_section(invalid_id, actor_user_id=self.admin_id)

    def test_18_database_enforces_section_foreign_key(self):
        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO sections (class_id, name)
                        VALUES (?, ?)
                        """,
                        (999999, "Invalid")
                    )

    def test_19_enrollment_history_prevents_section_deletion(self):
        section_id = create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            with connection:
                student_cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("STU-SECTION-001", "Test", "Student")
                )

                student_id = student_cursor.lastrowid

                year_cursor = connection.execute(
                    """
                    INSERT INTO academic_years (
                        name,
                        start_date,
                        end_date
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        "2090-2091",
                        "2090-09-01",
                        "2091-06-30"
                    )
                )

                year_id = year_cursor.lastrowid

                connection.execute(
                    """
                    INSERT INTO enrollments (
                        student_id,
                        section_id,
                        academic_year_id,
                        enrolled_on
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        section_id,
                        year_id,
                        "2090-09-01"
                    )
                )

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        "DELETE FROM sections WHERE id = ?",
                        (section_id,)
                    )

        self.assertIsNotNone(get_section(section_id, actor_user_id=self.admin_id))

    def test_20_sqlite_database_integrity(self):
        create_section(
            sample_section(class_id=self.class_one)
        , actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    def test_21_staff_can_read_but_cannot_modify_sections(self):
        section_id = create_section(
            sample_section(class_id=self.class_one),
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(
            get_section(section_id, actor_user_id=self.staff_id)
        )
        self.assertEqual(
            len(get_sections(actor_user_id=self.staff_id)),
            1,
        )

        with self.assertRaises(PermissionError):
            create_section(
                sample_section(class_id=self.class_one, name="B"),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_section(
                section_id,
                sample_section(class_id=self.class_one, name="Modified"),
                actor_user_id=self.staff_id,
            )

        unchanged = get_section(section_id, actor_user_id=self.admin_id)
        self.assertEqual(unchanged["name"], "A")


if __name__ == "__main__":
    unittest.main(verbosity=2)
