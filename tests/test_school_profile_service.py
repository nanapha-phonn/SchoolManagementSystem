import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database, get_connection
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
from services.school_profile_service import (
    get_school_profile,
    save_school_profile,
)


def sample_profile(**overrides):
    data = {
        "name": "Demo International School",
        "address": "Phnom Penh, Cambodia",
        "phone": "+855 12 345 678",
        "email": "info@demo-school.example",
    }
    data.update(overrides)
    return data


class SchoolProfileServiceTests(unittest.TestCase):

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

        create_initial_admin(
            "admin1",
            "AdminPass123",
            "Test Administrator",
        )
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]

        self.staff_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id,
        )

    def test_01_empty_database_has_no_school_profile(self):
        profile = get_school_profile(
            actor_user_id=self.admin_id,
        )

        self.assertIsNone(profile)

    def test_02_create_and_retrieve_school_profile(self):
        school_id = save_school_profile(
            sample_profile(),
            actor_user_id=self.admin_id,
        )

        profile = get_school_profile(
            actor_user_id=self.admin_id,
        )

        self.assertIsNotNone(profile)
        self.assertEqual(profile["id"], school_id)
        self.assertEqual(profile["name"], "Demo International School")
        self.assertEqual(profile["address"], "Phnom Penh, Cambodia")
        self.assertEqual(profile["phone"], "+855 12 345 678")
        self.assertEqual(
            profile["email"],
            "info@demo-school.example",
        )
        self.assertIsNotNone(profile["created_at"])

    def test_03_update_existing_school_profile(self):
        school_id = save_school_profile(
            sample_profile(),
            actor_user_id=self.admin_id,
        )

        updated_id = save_school_profile(
            sample_profile(
                name="Updated School Name",
                phone="+855 98 765 432",
            ),
            actor_user_id=self.admin_id,
        )

        profile = get_school_profile(
            actor_user_id=self.admin_id,
        )

        self.assertEqual(updated_id, school_id)
        self.assertEqual(profile["id"], school_id)
        self.assertEqual(profile["name"], "Updated School Name")
        self.assertEqual(profile["phone"], "+855 98 765 432")
        self.assertEqual(profile["address"], "Phnom Penh, Cambodia")

    def test_04_reject_missing_school_name(self):
        with self.assertRaisesRegex(ValueError, "School name is required"):
            save_school_profile(
                sample_profile(name="   "),
                actor_user_id=self.admin_id,
            )

        self.assertIsNone(
            get_school_profile(actor_user_id=self.admin_id)
        )

    def test_05_reject_invalid_email(self):
        with self.assertRaisesRegex(ValueError, "valid school email"):
            save_school_profile(
                sample_profile(email="not-an-email"),
                actor_user_id=self.admin_id,
            )

    def test_06_reject_non_text_values(self):
        with self.assertRaisesRegex(ValueError, "Phone must be text"):
            save_school_profile(
                sample_profile(phone=123456),
                actor_user_id=self.admin_id,
            )

    def test_07_reject_fields_that_exceed_length_limits(self):
        with self.assertRaisesRegex(ValueError, "School name must not exceed"):
            save_school_profile(
                sample_profile(name="S" * 121),
                actor_user_id=self.admin_id,
            )

    def test_08_staff_can_read_but_cannot_edit_school_profile(self):
        save_school_profile(
            sample_profile(),
            actor_user_id=self.admin_id,
        )

        profile = get_school_profile(
            actor_user_id=self.staff_id,
        )

        self.assertEqual(
            profile["name"],
            "Demo International School",
        )

        with self.assertRaises(PermissionError):
            save_school_profile(
                sample_profile(name="Unauthorized Update"),
                actor_user_id=self.staff_id,
            )

    def test_09_reject_multiple_school_profiles_when_reading(self):
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO schools (name) VALUES (?)",
                ("School One",),
            )
            connection.execute(
                "INSERT INTO schools (name) VALUES (?)",
                ("School Two",),
            )

        with self.assertRaisesRegex(ValueError, "Multiple school profiles"):
            get_school_profile(actor_user_id=self.admin_id)

    def test_10_reject_multiple_school_profiles_when_saving(self):
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO schools (name) VALUES (?)",
                ("School One",),
            )
            connection.execute(
                "INSERT INTO schools (name) VALUES (?)",
                ("School Two",),
            )

        with self.assertRaisesRegex(ValueError, "Multiple school profiles"):
            save_school_profile(
                sample_profile(),
                actor_user_id=self.admin_id,
            )


if __name__ == "__main__":
    unittest.main()
