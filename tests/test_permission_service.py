import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user, update_user_status
from services.permission_service import (
    PERMISSIONS,
    has_permission,
    require_permission,
)


class TestPermissionService(unittest.TestCase):

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
        self.admin_id = authenticate_user(
            "admin1", "AdminPass123"
        )["id"]

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

    def test_permission_definitions_are_explicit(self):
        self.assertIn("dashboard.view", PERMISSIONS)
        self.assertIn("documents.view", PERMISSIONS)
        self.assertIn("documents.manage", PERMISSIONS)
        self.assertIn("documents.archive", PERMISSIONS)
        self.assertIn("users.manage", PERMISSIONS)
        self.assertIn("payroll.manage", PERMISSIONS)
        self.assertIn("system.manage", PERMISSIONS)

    def test_admin_has_dashboard_permission(self):
        self.assertTrue(
            has_permission(self.admin_id, "dashboard.view")
        )

    def test_staff_has_dashboard_permission(self):
        self.assertTrue(
            has_permission(self.staff_id, "dashboard.view")
        )

    def test_staff_can_manage_academic_operations(self):
        permissions = [
            "students.manage",
            "academics.manage",
            "teachers.manage",
            "transportation.manage",
            "fees.manage",
            "documents.view",
            "documents.manage",
        ]

        for permission in permissions:
            with self.subTest(permission=permission):
                self.assertTrue(
                    has_permission(self.staff_id, permission)
                )

    def test_admin_only_permissions_are_denied_to_staff(self):
        permissions = [
            "fees.reports.view",
            "student_accounts.view",
            "payroll.manage",
            "payroll.reports.view",
            "users.manage",
            "system.manage",
            "documents.archive",
        ]

        for permission in permissions:
            with self.subTest(permission=permission):
                self.assertFalse(
                    has_permission(self.staff_id, permission)
                )

    def test_admin_has_user_management_permission(self):
        self.assertTrue(
            has_permission(self.admin_id, "users.manage")
        )

    def test_admin_has_payroll_permission(self):
        self.assertTrue(
            has_permission(self.admin_id, "payroll.manage")
        )

    def test_require_permission_allows_authorized_user(self):
        self.assertTrue(
            require_permission(self.staff_id, "students.manage")
        )

    def test_require_permission_rejects_unauthorized_user(self):
        with self.assertRaises(PermissionError):
            require_permission(self.staff_id, "users.manage")

    def test_unknown_permission_is_rejected(self):
        with self.assertRaises(ValueError):
            has_permission(self.admin_id, "unknown.permission")

    def test_missing_user_is_rejected(self):
        with self.assertRaises(PermissionError):
            has_permission(99999, "dashboard.view")

    def test_inactive_user_is_rejected(self):
        update_user_status(
            self.staff_id, False, self.admin_id
        )

        with self.assertRaises(PermissionError):
            has_permission(self.staff_id, "dashboard.view")

    def test_role_is_read_from_database(self):
        # Verify that permissions do not rely on a stale UI role.
        with database_module.get_connection() as connection:
            connection.execute(
                "UPDATE users SET role = 'staff' WHERE id = ?",
                (self.admin_id,)
            )

        self.assertFalse(
            has_permission(self.admin_id, "users.manage")
        )


if __name__ == "__main__":
    unittest.main()
