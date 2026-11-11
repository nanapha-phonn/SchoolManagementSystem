import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from models.school_class import SchoolClass
from services.class_service import (
    create_class,
    get_class,
    get_classes,
    update_class,
)


def sample_class(**overrides):
    data = {
        "name": "Grade 1",
        "description": "First grade students",
    }

    data.update(overrides)
    return data


from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
class ClassServiceTests(unittest.TestCase):

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

    def test_01_create_and_retrieve_class(self):
        class_id = create_class(sample_class(), actor_user_id=self.admin_id)

        school_class = get_class(class_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(school_class)
        self.assertEqual(school_class["name"], "Grade 1")
        self.assertEqual(
            school_class["description"],
            "First grade students"
        )

    def test_02_normalize_class_name(self):
        class_id = create_class(
            sample_class(name="  Grade 2  ")
        , actor_user_id=self.admin_id)

        self.assertEqual(
            get_class(class_id, actor_user_id=self.admin_id)["name"],
            "Grade 2"
        )

    def test_03_allow_optional_description(self):
        class_id = create_class(
            sample_class(description="")
        , actor_user_id=self.admin_id)

        self.assertIsNone(
            get_class(class_id, actor_user_id=self.admin_id)["description"]
        )

    def test_04_reject_invalid_class_data(self):
        invalid_cases = [
            ("missing name", {"name": ""}),
            ("whitespace name", {"name": "   "}),
            ("long name", {"name": "A" * 101}),
            ("non-text name", {"name": 123}),
            ("long description", {"description": "A" * 501}),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                with self.assertRaises(ValueError):
                    SchoolClass(
                        **sample_class(**overrides)
                    ).validate()

        self.assertEqual(len(get_classes(actor_user_id=self.admin_id)), 0)

    def test_05_reject_duplicate_class_name(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            create_class(sample_class(), actor_user_id=self.admin_id)

        self.assertEqual(len(get_classes(actor_user_id=self.admin_id)), 1)

    def test_06_retrieve_missing_class(self):
        self.assertIsNone(get_class(999999, actor_user_id=self.admin_id))

    def test_07_search_by_class_name(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        create_class(
            sample_class(
                name="Grade 2",
                description="Second grade",
            )
        , actor_user_id=self.admin_id)

        self.assertEqual(len(get_classes("Grade 1", actor_user_id=self.admin_id)), 1)
        self.assertEqual(len(get_classes("Grade", actor_user_id=self.admin_id)), 2)

    def test_08_search_by_description(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        create_class(
            sample_class(
                name="Grade 2",
                description="Advanced mathematics",
            )
        , actor_user_id=self.admin_id)

        results = get_classes("mathematics", actor_user_id=self.admin_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Grade 2")

    def test_09_search_without_match(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        self.assertEqual(
            get_classes("not-found", actor_user_id=self.admin_id),
            []
        )

    def test_10_update_class(self):
        class_id = create_class(sample_class(), actor_user_id=self.admin_id)

        update_class(
            class_id,
            sample_class(
                name="Grade 1 Updated",
                description="Updated description",
            )
        , actor_user_id=self.admin_id)

        school_class = get_class(class_id, actor_user_id=self.admin_id)

        self.assertEqual(
            school_class["name"],
            "Grade 1 Updated"
        )
        self.assertEqual(
            school_class["description"],
            "Updated description"
        )

    def test_11_reject_duplicate_name_during_update(self):
        first_id = create_class(sample_class(), actor_user_id=self.admin_id)

        create_class(
            sample_class(name="Grade 2")
        , actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            update_class(
                first_id,
                sample_class(name="Grade 2")
            , actor_user_id=self.admin_id)

        self.assertEqual(
            get_class(first_id, actor_user_id=self.admin_id)["name"],
            "Grade 1"
        )

    def test_12_invalid_update_preserves_original_record(self):
        class_id = create_class(sample_class(), actor_user_id=self.admin_id)

        with self.assertRaises(ValueError):
            update_class(
                class_id,
                sample_class(name="")
            , actor_user_id=self.admin_id)

        self.assertEqual(
            get_class(class_id, actor_user_id=self.admin_id)["name"],
            "Grade 1"
        )

    def test_13_reject_update_for_missing_class(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found"
        ):
            update_class(
                999999,
                sample_class()
            , actor_user_id=self.admin_id)

    def test_14_reject_invalid_class_ids(self):
        for invalid_id in (0, -1, "invalid", None, True):
            with self.subTest(class_id=invalid_id):
                with self.assertRaises(ValueError):
                    get_class(invalid_id, actor_user_id=self.admin_id)

    def test_15_database_enforces_unique_class_name(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO classes (name, description)
                        VALUES (?, ?)
                        """,
                        ("Grade 1", "Duplicate")
                    )

    def test_16_sqlite_database_integrity(self):
        create_class(sample_class(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    def test_17_staff_can_read_but_cannot_modify_classes(self):
        class_id = create_class(
            sample_class(),
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(
            get_class(class_id, actor_user_id=self.staff_id)
        )
        self.assertEqual(
            len(get_classes(actor_user_id=self.staff_id)),
            1,
        )

        with self.assertRaises(PermissionError):
            create_class(
                sample_class(name="Grade 2"),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_class(
                class_id,
                sample_class(name="Modified Grade"),
                actor_user_id=self.staff_id,
            )

        unchanged = get_class(class_id, actor_user_id=self.admin_id)
        self.assertEqual(unchanged["name"], "Grade 1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
