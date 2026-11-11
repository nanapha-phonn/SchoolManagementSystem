import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from models.enrollment import (
    Enrollment,
    VALID_ENROLLMENT_STATUSES,
)
from services.auth_service import (
    create_initial_admin,
    authenticate_user,
)
from services.student_service import (
    create_student as service_create_student,
    update_student_status as service_update_student_status,
)
from services.user_service import create_user, update_user_status
from services.academic_year_service import create_academic_year
from services.class_service import create_class
from services.section_service import create_section
from services.enrollment_service import (
    create_enrollment as service_create_enrollment,
    get_enrollment as service_get_enrollment,
    get_enrollments as service_get_enrollments,
    update_enrollment as service_update_enrollment,
)


def sample_student(**overrides):
    data = {
        "admission_no": "STU-ENR-001",
        "first_name": "Test",
        "last_name": "Student",
        "status": "active",
    }
    data.update(overrides)
    return data


def sample_year(**overrides):
    data = {
        "name": "2090-2091",
        "start_date": "2090-09-01",
        "end_date": "2091-06-30",
        "is_current": False,
    }
    data.update(overrides)
    return data


def sample_enrollment(**overrides):
    data = {
        "student_id": 1,
        "section_id": 1,
        "academic_year_id": 1,
        "enrolled_on": "2090-09-01",
        "status": "enrolled",
    }
    data.update(overrides)
    return data


class EnrollmentServiceTests(unittest.TestCase):

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
            "admin1",
            "AdminPass123",
            "Test Administrator",
        )
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]

        self.staff_user_id = create_user(
            "staff1",
            "StaffPass123",
            "Test Staff",
            "staff",
            self.admin_id,
        )

        self.student_one = service_create_student(
            sample_student(),
            actor_user_id=self.admin_id,
        )

        self.student_two = service_create_student(
            sample_student(
                admission_no="STU-ENR-002",
                first_name="Second",
                last_name="Student",
            ),
            actor_user_id=self.admin_id,
        )

        self.student_three = service_create_student(
            sample_student(
                admission_no="STU-ENR-003",
                first_name="Inactive",
                last_name="Student",
            ),
            actor_user_id=self.admin_id,
        )

        self.year_one = create_academic_year(sample_year(), actor_user_id=self.admin_id)

        self.year_two = create_academic_year(
            sample_year(
                name="2091-2092",
                start_date="2091-09-01",
                end_date="2092-06-30",
            ),
            actor_user_id=self.admin_id,
        )

        self.class_one = create_class(
            {
                "name": "Grade 1",
                "description": "First grade",
            },
            actor_user_id=self.admin_id,
        )

        self.class_two = create_class(
            {
                "name": "Grade 2",
                "description": "Second grade",
            },
            actor_user_id=self.admin_id,
        )

        self.section_one = create_section(
            {
                "class_id": self.class_one,
                "name": "A",
            },
            actor_user_id=self.admin_id,
        )

        self.section_two = create_section(
            {
                "class_id": self.class_one,
                "name": "B",
            },
            actor_user_id=self.admin_id,
        )

        self.section_three = create_section(
            {
                "class_id": self.class_two,
                "name": "A",
            },
            actor_user_id=self.admin_id,
        )

    def _create_student(self, data):
        return service_create_student(
            data,
            actor_user_id=self.admin_id,
        )

    def _update_student_status(self, student_id, status):
        return service_update_student_status(
            student_id,
            status,
            actor_user_id=self.admin_id,
        )

    def _create_enrollment(self, data):
        return service_create_enrollment(
            data,
            actor_user_id=self.admin_id,
        )

    def _get_enrollment(self, enrollment_id):
        return service_get_enrollment(
            enrollment_id,
            actor_user_id=self.admin_id,
        )

    def _get_enrollments(self, *args, **kwargs):
        return service_get_enrollments(
            *args,
            actor_user_id=self.admin_id,
            **kwargs,
        )

    def _update_enrollment(self, enrollment_id, data):
        return service_update_enrollment(
            enrollment_id,
            data,
            actor_user_id=self.admin_id,
        )

    def enrollment(self, **overrides):
        data = sample_enrollment(
            student_id=self.student_one,
            section_id=self.section_one,
            academic_year_id=self.year_one,
        )
        data.update(overrides)
        return self._create_enrollment(data)

    def test_01_create_and_retrieve_enrollment(self):
        enrollment_id = self.enrollment()

        enrollment = self._get_enrollment(enrollment_id)

        self.assertIsNotNone(enrollment)
        self.assertEqual(
            enrollment["student_id"],
            self.student_one
        )
        self.assertEqual(
            enrollment["admission_no"],
            "STU-ENR-001"
        )
        self.assertEqual(
            enrollment["student_name"],
            "Test Student"
        )
        self.assertEqual(
            enrollment["class_name"],
            "Grade 1"
        )
        self.assertEqual(enrollment["section_name"], "A")
        self.assertEqual(
            enrollment["academic_year_name"],
            "2090-2091"
        )
        self.assertEqual(enrollment["status"], "enrolled")

    def test_02_accept_all_valid_enrollment_statuses(self):
        for status in sorted(VALID_ENROLLMENT_STATUSES):
            with self.subTest(status=status):
                student_id = self._create_student(
                    sample_student(
                        admission_no=f"STU-STATUS-{status}",
                        first_name="Status",
                        last_name="Student",
                    )
                )

                enrollment_id = self.enrollment(
                    student_id=student_id,
                    status=status
                )

                self.assertEqual(
                    self._get_enrollment(enrollment_id)["status"],
                    status
                )

    def test_03_reject_invalid_enrollment_data(self):
        invalid_cases = [
            ("zero student ID", {"student_id": 0}),
            ("negative student ID", {"student_id": -1}),
            ("invalid student ID", {"student_id": "invalid"}),
            ("boolean student ID", {"student_id": True}),
            ("zero section ID", {"section_id": 0}),
            ("zero academic year ID", {"academic_year_id": 0}),
            ("empty enrollment date", {"enrolled_on": ""}),
            ("invalid enrollment date", {"enrolled_on": "01-09-2090"}),
            ("non-padded date", {"enrolled_on": "2090-9-01"}),
            ("invalid calendar date", {"enrolled_on": "2090-02-30"}),
            ("invalid status", {"status": "pending"}),
            ("empty status", {"status": ""}),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                data = sample_enrollment(
                    student_id=self.student_one,
                    section_id=self.section_one,
                    academic_year_id=self.year_one,
                )
                data.update(overrides)

                with self.assertRaises(ValueError):
                    Enrollment(**data).validate()

        self.assertEqual(len(self._get_enrollments()), 0)

    def test_04_reject_missing_student(self):
        with self.assertRaisesRegex(
            ValueError,
            "Selected student was not found"
        ):
            self.enrollment(student_id=999999)

        self.assertEqual(len(self._get_enrollments()), 0)

    def test_05_reject_inactive_student(self):
        self._update_student_status(
            self.student_three,
            "inactive"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Only active students"
        ):
            self.enrollment(student_id=self.student_three)

        self.assertEqual(len(self._get_enrollments()), 0)

    def test_06_reject_missing_section(self):
        with self.assertRaisesRegex(
            ValueError,
            "Selected section was not found"
        ):
            self.enrollment(section_id=999999)

        self.assertEqual(len(self._get_enrollments()), 0)

    def test_07_reject_missing_academic_year(self):
        with self.assertRaisesRegex(
            ValueError,
            "Selected academic year was not found"
        ):
            self.enrollment(academic_year_id=999999)

        self.assertEqual(len(self._get_enrollments()), 0)

    def test_08_prevent_duplicate_enrollment_in_same_year(self):
        self.enrollment()

        with self.assertRaisesRegex(
            ValueError,
            "already enrolled in this academic year"
        ):
            self.enrollment(
                section_id=self.section_two
            )

        self.assertEqual(len(self._get_enrollments()), 1)

    def test_09_promote_student_to_new_academic_year(self):
        first_id = self.enrollment()

        second_id = self.enrollment(
            section_id=self.section_three,
            academic_year_id=self.year_two,
            enrolled_on="2091-09-01",
        )

        first = self._get_enrollment(first_id)
        second = self._get_enrollment(second_id)

        self.assertNotEqual(first_id, second_id)

        self.assertEqual(first["academic_year_id"], self.year_one)
        self.assertEqual(first["class_name"], "Grade 1")
        self.assertEqual(first["section_name"], "A")

        self.assertEqual(second["academic_year_id"], self.year_two)
        self.assertEqual(second["class_name"], "Grade 2")
        self.assertEqual(second["section_name"], "A")

        self.assertEqual(len(self._get_enrollments()), 2)

    def test_10_different_students_can_share_same_year_and_section(self):
        first_id = self.enrollment()

        second_id = self.enrollment(
            student_id=self.student_two
        )

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(len(self._get_enrollments()), 2)

    def test_11_retrieve_missing_enrollment(self):
        self.assertIsNone(self._get_enrollment(999999))

    def test_12_search_by_admission_number(self):
        self.enrollment()

        results = self._get_enrollments("STU-ENR-001")

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["admission_no"],
            "STU-ENR-001"
        )

    def test_13_search_by_student_name(self):
        self.enrollment()

        results = self._get_enrollments("Test")

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["student_name"],
            "Test Student"
        )

    def test_14_search_by_academic_year_class_and_section(self):
        self.enrollment()

        self.assertEqual(len(self._get_enrollments("2090-2091")), 1)
        self.assertEqual(len(self._get_enrollments("Grade 1")), 1)
        self.assertEqual(len(self._get_enrollments("A")), 1)

    def test_15_filter_by_academic_year(self):
        self.enrollment()

        self.enrollment(
            academic_year_id=self.year_two,
            enrolled_on="2091-09-01"
        )

        results = self._get_enrollments(
            academic_year_id=self.year_two
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["academic_year_id"],
            self.year_two
        )

    def test_16_filter_by_class(self):
        self.enrollment()

        self.enrollment(
            student_id=self.student_two,
            section_id=self.section_three
        )

        results = self._get_enrollments(
            class_id=self.class_two
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["class_id"],
            self.class_two
        )

    def test_17_filter_by_section(self):
        self.enrollment()

        self.enrollment(
            section_id=self.section_two,
            academic_year_id=self.year_two,
            enrolled_on="2091-09-01"
        )

        results = self._get_enrollments(
            section_id=self.section_two
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["section_id"],
            self.section_two
        )

    def test_18_filter_by_status(self):
        self.enrollment(status="enrolled")

        self.enrollment(
            student_id=self.student_two,
            status="completed"
        )

        results = self._get_enrollments(status="completed")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "completed")

    def test_19_reject_invalid_status_filter(self):
        with self.assertRaisesRegex(
            ValueError,
            "Invalid enrollment status"
        ):
            self._get_enrollments(status="unknown")

    def test_20_update_section_date_and_status(self):
        enrollment_id = self.enrollment()

        self._update_enrollment(
            enrollment_id,
            {
                "section_id": self.section_two,
                "enrolled_on": "2090-09-15",
                "status": "completed",
            }
        )

        enrollment = self._get_enrollment(enrollment_id)

        self.assertEqual(
            enrollment["section_id"],
            self.section_two
        )
        self.assertEqual(
            enrollment["enrolled_on"],
            "2090-09-15"
        )
        self.assertEqual(enrollment["status"], "completed")

    def test_21_update_preserves_student_and_academic_year(self):
        enrollment_id = self.enrollment()

        original = self._get_enrollment(enrollment_id)

        self._update_enrollment(
            enrollment_id,
            {
                "section_id": self.section_two,
                "enrolled_on": "2090-09-15",
                "status": "enrolled",
            }
        )

        updated = self._get_enrollment(enrollment_id)

        self.assertEqual(
            updated["student_id"],
            original["student_id"]
        )

        self.assertEqual(
            updated["academic_year_id"],
            original["academic_year_id"]
        )

    def test_22_reject_student_or_year_changes_during_update(self):
        enrollment_id = self.enrollment()

        with self.assertRaisesRegex(
            ValueError,
            "cannot be changed"
        ):
            self._update_enrollment(
                enrollment_id,
                {
                    "student_id": self.student_two,
                    "section_id": self.section_two,
                    "academic_year_id": self.year_two,
                    "enrolled_on": "2090-09-15",
                    "status": "enrolled",
                }
            )

        self.assertEqual(
            self._get_enrollment(enrollment_id)["student_id"],
            self.student_one
        )

    def test_23_reject_update_for_missing_enrollment(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found"
        ):
            self._update_enrollment(
                999999,
                {
                    "section_id": self.section_one,
                    "enrolled_on": "2090-09-01",
                    "status": "enrolled",
                }
            )

    def test_24_invalid_update_preserves_original_record(self):
        enrollment_id = self.enrollment()

        with self.assertRaises(ValueError):
            self._update_enrollment(
                enrollment_id,
                {
                    "section_id": 999999,
                    "enrolled_on": "2090-09-15",
                    "status": "enrolled",
                }
            )

        enrollment = self._get_enrollment(enrollment_id)

        self.assertEqual(
            enrollment["section_id"],
            self.section_one
        )
        self.assertEqual(
            enrollment["enrolled_on"],
            "2090-09-01"
        )

    def test_25_reject_invalid_enrollment_ids_and_filters(self):
        for invalid_id in (0, -1, "invalid", None, True):
            if invalid_id is None:
                continue

            with self.subTest(enrollment_id=invalid_id):
                with self.assertRaises(ValueError):
                    self._get_enrollment(invalid_id)

        with self.assertRaises(ValueError):
            self._get_enrollments(class_id=0)

        with self.assertRaises(ValueError):
            self._get_enrollments(academic_year_id=-1)

        with self.assertRaises(ValueError):
            self._get_enrollments(section_id="invalid")

    def test_26_database_prevents_duplicate_enrollment(self):
        self.enrollment()

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO enrollments (
                            student_id,
                            section_id,
                            academic_year_id,
                            enrolled_on,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            self.student_one,
                            self.section_two,
                            self.year_one,
                            "2090-09-15",
                            "enrolled"
                        )
                    )

    def test_27_database_prevents_enrollment_history_deletion(self):
        enrollment_id = self.enrollment()

        self.assertIsNotNone(self._get_enrollment(enrollment_id))

        with closing(database_module.get_connection()) as connection:
            with self.assertRaisesRegex(
                sqlite3.IntegrityError,
                "Enrollment history cannot be deleted"
            ):
                with connection:
                    connection.execute(
                        "DELETE FROM enrollments WHERE id = ?",
                        (enrollment_id,)
                    )

        self.assertIsNotNone(self._get_enrollment(enrollment_id))

    def test_28_foreign_keys_protect_referenced_records(self):
        enrollment_id = self.enrollment()

        referenced_records = [
            ("students", self.student_one),
            ("sections", self.section_one),
            ("academic_years", self.year_one),
            ("classes", self.class_one),
        ]

        with closing(database_module.get_connection()) as connection:
            for table, record_id in referenced_records:
                with self.subTest(table=table):
                    with self.assertRaises(sqlite3.IntegrityError):
                        with connection:
                            connection.execute(
                                f'DELETE FROM "{table}" WHERE id = ?',
                                (record_id,)
                            )

        self.assertIsNotNone(self._get_enrollment(enrollment_id))

    def test_30_enrollment_role_authorization(self):
        enrollment_id = self.enrollment()

        # Staff can create, retrieve, list, and update enrollments.
        staff_enrollment_id = service_create_enrollment(
            sample_enrollment(
                student_id=self.student_two,
                section_id=self.section_two,
            ),
            actor_user_id=self.staff_user_id,
        )

        self.assertIsNotNone(
            service_get_enrollment(
                staff_enrollment_id,
                actor_user_id=self.staff_user_id,
            )
        )

        staff_results = service_get_enrollments(
            actor_user_id=self.staff_user_id,
        )
        self.assertEqual(len(staff_results), 2)

        service_update_enrollment(
            staff_enrollment_id,
            {
                "section_id": self.section_three,
                "enrolled_on": "2090-09-15",
                "status": "completed",
            },
            actor_user_id=self.staff_user_id,
        )

        updated = service_get_enrollment(
            staff_enrollment_id,
            actor_user_id=self.staff_user_id,
        )
        self.assertEqual(updated["status"], "completed")

        # All four operations reject a missing actor.
        with self.assertRaises(PermissionError):
            service_create_enrollment(sample_enrollment(), actor_user_id=None)

        with self.assertRaises(PermissionError):
            service_get_enrollment(enrollment_id, actor_user_id=None)

        with self.assertRaises(PermissionError):
            service_get_enrollments(actor_user_id=None)

        with self.assertRaises(PermissionError):
            service_update_enrollment(
                enrollment_id,
                {
                    "section_id": self.section_two,
                    "enrolled_on": "2090-09-15",
                    "status": "enrolled",
                },
                actor_user_id=None,
            )

        # All four operations reject an inactive actor.
        update_user_status(
            self.staff_user_id,
            False,
            self.admin_id,
        )

        with self.assertRaises(PermissionError):
            service_create_enrollment(
                sample_enrollment(),
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            service_get_enrollment(
                enrollment_id,
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            service_get_enrollments(
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            service_update_enrollment(
                enrollment_id,
                {
                    "section_id": self.section_two,
                    "enrolled_on": "2090-09-15",
                    "status": "enrolled",
                },
                actor_user_id=self.staff_user_id,
            )

    def test_29_sqlite_database_integrity(self):
        self.enrollment()

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
