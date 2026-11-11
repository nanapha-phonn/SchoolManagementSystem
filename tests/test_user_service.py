import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from services.auth_service import (
    authenticate_user,
    create_initial_admin,
)
from services.user_service import (
    create_user,
    get_user,
    get_users,
    search_users,
    update_user,
    update_user_status,
)


class TestUserService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_school.db"

        self.db_patcher = patch.object(
            database_module, "DB_PATH", str(self.db_path)
        )
        self.db_patcher.start()
        database_module.initialize_database()

        create_initial_admin(
            "admin1",
            "AdminPass123",
            "Test Administrator"
        )

        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]

        self.staff_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id
        )

    def tearDown(self):
        self.db_patcher.stop()
        self.temp_dir.cleanup()

    def test_create_staff_user(self):
        user = get_user(self.staff_id, self.admin_id)

        self.assertEqual(user["username"], "staff1")
        self.assertEqual(user["full_name"], "Test Staff")
        self.assertEqual(user["role"], "staff")
        self.assertEqual(user["is_active"], 1)
        self.assertNotIn("password_hash", user)

    def test_create_admin_user(self):
        user_id = create_user(
            "admin2",
            "AnotherPass123",
            "Second Administrator",
            "admin",
            self.admin_id
        )

        user = get_user(user_id, self.admin_id)
        self.assertEqual(user["role"], "admin")

    def test_username_is_normalized(self):
        user_id = create_user(
            "  STAFF_TWO  ",
            "StaffPass123",
            "Staff Two",
            "staff",
            self.admin_id
        )

        self.assertEqual(get_user(user_id, self.admin_id)["username"], "staff_two")

    def test_invalid_usernames_rejected(self):
        for username in ("ab", "a" * 31, "bad name", "bad@name"):
            with self.subTest(username=username):
                with self.assertRaises(ValueError):
                    create_user(
                        username,
                        "StaffPass123",
                        "Invalid User",
                        "staff",
                        self.admin_id
                    )

    def test_empty_full_name_rejected(self):
        with self.assertRaises(ValueError):
            create_user(
                "stafftwo",
                "StaffPass123",
                "   ",
                "staff",
                self.admin_id
            )

    def test_invalid_role_rejected(self):
        with self.assertRaises(ValueError):
            create_user(
                "stafftwo",
                "StaffPass123",
                "Staff Two",
                "manager",
                self.admin_id
            )

    def test_weak_password_rejected(self):
        with self.assertRaises(ValueError):
            create_user(
                "stafftwo",
                "short",
                "Staff Two",
                "staff",
                self.admin_id
            )

    def test_duplicate_username_rejected(self):
        with self.assertRaises(ValueError):
            create_user(
                "STAFF1",
                "AnotherPass123",
                "Duplicate Staff",
                "staff",
                self.admin_id
            )

    def test_non_admin_cannot_create_user(self):
        with self.assertRaises(PermissionError):
            create_user(
                "stafftwo",
                "StaffPass123",
                "Staff Two",
                "staff",
                self.staff_id
            )

    def test_non_admin_cannot_list_or_search_users(self):
        with self.assertRaises(PermissionError):
            get_users(self.staff_id)

        with self.assertRaises(PermissionError):
            search_users("staff", self.staff_id)

    def test_non_admin_cannot_get_user(self):
        with self.assertRaises(PermissionError):
            get_user(self.staff_id, self.staff_id)

    def test_list_and_search_users(self):
        users = get_users(self.admin_id)

        self.assertEqual(len(users), 2)

        results = search_users("staff", self.admin_id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "staff1")

    def test_update_user_profile(self):
        original = get_user(self.staff_id, self.admin_id)

        update_user(
            self.staff_id,
            "staff_updated",
            "Updated Staff",
            "staff",
            self.admin_id
        )

        updated = get_user(self.staff_id, self.admin_id)

        self.assertEqual(updated["username"], "staff_updated")
        self.assertEqual(updated["full_name"], "Updated Staff")
        self.assertEqual(updated["created_at"], original["created_at"])

        # The existing password must remain valid.
        authenticated = authenticate_user(
            "staff_updated",
            "StaffPass123"
        )
        self.assertIsNotNone(authenticated)

    def test_non_admin_cannot_update_user(self):
        with self.assertRaises(PermissionError):
            update_user(
                self.staff_id,
                "changed_staff",
                "Changed Staff",
                "staff",
                self.staff_id
            )

    def test_admin_cannot_change_own_role(self):
        with self.assertRaises(ValueError):
            update_user(
                self.admin_id,
                "admin1",
                "Test Administrator",
                "staff",
                self.admin_id
            )

    def test_last_active_admin_cannot_be_demoted(self):
        with self.assertRaises(ValueError):
            update_user(
                self.admin_id,
                "admin1",
                "Test Administrator",
                "staff",
                self.admin_id
            )

    def test_last_active_admin_cannot_be_deactivated(self):
        with self.assertRaises(ValueError):
            update_user_status(
                self.admin_id,
                False,
                self.admin_id
            )

    def test_admin_cannot_deactivate_own_account(self):
        with self.assertRaises(ValueError):
            update_user_status(
                self.admin_id,
                False,
                self.admin_id
            )

    def test_deactivate_and_reactivate_staff(self):
        update_user_status(
            self.staff_id,
            False,
            self.admin_id
        )

        self.assertEqual(get_user(self.staff_id, self.admin_id)["is_active"], 0)
        self.assertIsNone(
            authenticate_user("staff1", "StaffPass123")
        )

        update_user_status(
            self.staff_id,
            True,
            self.admin_id
        )

        self.assertEqual(get_user(self.staff_id, self.admin_id)["is_active"], 1)
        self.assertIsNotNone(
            authenticate_user("staff1", "StaffPass123")
        )

    def test_invalid_status_type_rejected(self):
        with self.assertRaises(ValueError):
            update_user_status(
                self.staff_id,
                1,
                self.admin_id
            )

    def test_non_admin_cannot_change_user_status(self):
        with self.assertRaises(PermissionError):
            update_user_status(
                self.staff_id,
                False,
                self.staff_id
            )


if __name__ == "__main__":
    unittest.main()
