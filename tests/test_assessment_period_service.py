import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from services.academic_year_service import create_academic_year
from services.assessment_period_service import (
    create_assessment_period,
    get_assessment_period,
    get_assessment_periods,
    update_assessment_period,
    update_assessment_period_status,
)
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user


def sample_year(**overrides):
    data = {
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": False,
    }
    data.update(overrides)
    return data


def sample_period(**overrides):
    data = {
        "academic_year_id": 1,
        "name": "Semester 1 Midterm",
        "period_type": "midterm",
        "start_date": "2026-10-01",
        "end_date": "2026-10-15",
        "status": "planned",
    }
    data.update(overrides)
    return data


class AssessmentPeriodServiceTests(unittest.TestCase):

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

        self.year_id = create_academic_year(sample_year(), actor_user_id=self.admin_id)

    def create_period(self, **overrides):
        return create_assessment_period(
            sample_period(
                academic_year_id=self.year_id,
                **overrides,
            ),
            actor_user_id=self.admin_id
        )

    def test_01_create_and_retrieve_assessment_period(self):
        period_id = self.create_period()

        period = get_assessment_period(period_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(period)
        self.assertEqual(period["academic_year_id"], self.year_id)
        self.assertEqual(period["academic_year_name"], "2026-2027")
        self.assertEqual(period["name"], "Semester 1 Midterm")
        self.assertEqual(period["period_type"], "midterm")
        self.assertEqual(period["status"], "planned")

    def test_02_create_normalizes_period_data(self):
        period_id = self.create_period(
            name="  Semester 1 Final  ",
            period_type=" FINAL ",
        )

        period = get_assessment_period(period_id, actor_user_id=self.admin_id)

        self.assertEqual(period["name"], "Semester 1 Final")
        self.assertEqual(period["period_type"], "final")
        self.assertEqual(period["status"], "planned")

    def test_03_new_period_must_start_as_planned(self):
        with self.assertRaisesRegex(ValueError, "start as planned"):
            self.create_period(status="active")

        with self.assertRaisesRegex(ValueError, "start as planned"):
            self.create_period(status="completed")

        self.assertEqual(len(get_assessment_periods(actor_user_id=self.admin_id)), 0)

    def test_04_reject_duplicate_name_case_insensitively(self):
        self.create_period(name="Semester 1 Midterm")

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.create_period(
                name="semester 1 midterm",
                start_date="2026-11-01",
                end_date="2026-11-15",
            )

    def test_05_same_period_name_allowed_in_different_years(self):
        self.create_period()

        second_year_id = create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            ),
            actor_user_id=self.admin_id,
        )

        second_period_id = create_assessment_period(
            sample_period(
                academic_year_id=second_year_id,
                start_date="2027-10-01",
                end_date="2027-10-15",
            ),
            actor_user_id=self.admin_id
        )

        self.assertIsNotNone(get_assessment_period(second_period_id, actor_user_id=self.admin_id))

    def test_06_reject_missing_academic_year(self):
        with self.assertRaisesRegex(ValueError, "Academic year"):
            create_assessment_period(
                sample_period(academic_year_id=999),
                actor_user_id=self.admin_id
            )

    def test_07_reject_dates_outside_academic_year(self):
        with self.assertRaisesRegex(ValueError, "within the academic year"):
            self.create_period(
                start_date="2026-08-31",
                end_date="2026-09-10",
            )

        with self.assertRaisesRegex(ValueError, "within the academic year"):
            self.create_period(
                start_date="2027-06-20",
                end_date="2027-07-01",
            )

        self.assertEqual(len(get_assessment_periods(actor_user_id=self.admin_id)), 0)

    def test_08_reject_overlapping_periods(self):
        self.create_period()

        with self.assertRaisesRegex(ValueError, "cannot overlap"):
            self.create_period(
                name="Semester 1 Final",
                period_type="final",
                start_date="2026-10-15",
                end_date="2026-10-25",
            )

    def test_09_allow_adjacent_non_overlapping_periods(self):
        self.create_period()

        second_id = self.create_period(
            name="Semester 1 Final",
            period_type="final",
            start_date="2026-10-16",
            end_date="2026-10-30",
        )

        self.assertIsNotNone(get_assessment_period(second_id, actor_user_id=self.admin_id))

    def test_10_reject_update_that_causes_overlap(self):
        first_id = self.create_period()

        second_id = self.create_period(
            name="Semester 1 Final",
            period_type="final",
            start_date="2026-11-01",
            end_date="2026-11-15",
        )

        with self.assertRaisesRegex(ValueError, "cannot overlap"):
            update_assessment_period(
                second_id,
                sample_period(
                    academic_year_id=self.year_id,
                    name="Semester 1 Final",
                    period_type="final",
                    start_date="2026-10-10",
                    end_date="2026-10-20",
                ),
                actor_user_id=self.admin_id,
            )

        unchanged = get_assessment_period(second_id, actor_user_id=self.admin_id)
        self.assertEqual(unchanged["start_date"], "2026-11-01")
        self.assertEqual(unchanged["end_date"], "2026-11-15")
        self.assertIsNotNone(get_assessment_period(first_id, actor_user_id=self.admin_id))

    def test_11_edit_planned_period(self):
        period_id = self.create_period()

        update_assessment_period(
            period_id,
            sample_period(
                academic_year_id=self.year_id,
                name="Updated Midterm",
                period_type="term",
                start_date="2026-10-02",
                end_date="2026-10-20",
            ),
            actor_user_id=self.admin_id,
        )

        period = get_assessment_period(period_id, actor_user_id=self.admin_id)
        self.assertEqual(period["name"], "Updated Midterm")
        self.assertEqual(period["period_type"], "term")
        self.assertEqual(period["start_date"], "2026-10-02")
        self.assertEqual(period["status"], "planned")

    def test_12_edit_active_period_without_changing_status(self):
        period_id = self.create_period()
        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)

        update_assessment_period(
            period_id,
            sample_period(
                academic_year_id=self.year_id,
                name="Updated Active Period",
                period_type="midterm",
                start_date="2026-10-02",
                end_date="2026-10-20",
                status="active",
            ),
            actor_user_id=self.admin_id,
        )

        period = get_assessment_period(period_id, actor_user_id=self.admin_id)
        self.assertEqual(period["name"], "Updated Active Period")
        self.assertEqual(period["status"], "active")

    def test_13_cannot_move_period_to_another_academic_year(self):
        period_id = self.create_period()

        second_year_id = create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            ),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "cannot be moved"):
            update_assessment_period(
                period_id,
                sample_period(
                    academic_year_id=second_year_id,
                    start_date="2027-10-01",
                    end_date="2027-10-15",
                ),
                actor_user_id=self.admin_id,
            )

        period = get_assessment_period(period_id, actor_user_id=self.admin_id)
        self.assertEqual(period["academic_year_id"], self.year_id)

    def test_14_allow_planned_to_active_transition(self):
        period_id = self.create_period()

        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)

        self.assertEqual(
            get_assessment_period(period_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_15_allow_active_to_completed_transition(self):
        period_id = self.create_period()

        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)
        update_assessment_period_status(period_id, "completed", actor_user_id=self.admin_id)

        self.assertEqual(
            get_assessment_period(period_id, actor_user_id=self.admin_id)["status"],
            "completed",
        )

    def test_16_same_status_transition_is_safe_noop(self):
        period_id = self.create_period()

        update_assessment_period_status(period_id, "planned", actor_user_id=self.admin_id)

        self.assertEqual(
            get_assessment_period(period_id, actor_user_id=self.admin_id)["status"],
            "planned",
        )

    def test_17_reject_backward_and_skipped_transitions(self):
        period_id = self.create_period()

        with self.assertRaisesRegex(ValueError, "Invalid status transition"):
            update_assessment_period_status(period_id, "completed", actor_user_id=self.admin_id)

        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "Invalid status transition"):
            update_assessment_period_status(period_id, "planned", actor_user_id=self.admin_id)

    def test_18_completed_period_cannot_be_edited(self):
        period_id = self.create_period()

        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)
        update_assessment_period_status(period_id, "completed", actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "Completed"):
            update_assessment_period(
                period_id,
                sample_period(
                    academic_year_id=self.year_id,
                    name="Changed Completed Period",
                    start_date="2026-10-02",
                    end_date="2026-10-20",
                    status="completed",
                ),
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_assessment_period(period_id, actor_user_id=self.admin_id)["name"],
            "Semester 1 Midterm",
        )

    def test_19_completed_period_cannot_be_deleted(self):
        period_id = self.create_period()

        update_assessment_period_status(period_id, "active", actor_user_id=self.admin_id)
        update_assessment_period_status(period_id, "completed", actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM assessment_periods WHERE id = ?",
                    (period_id,),
                )

        self.assertIsNotNone(get_assessment_period(period_id, actor_user_id=self.admin_id))

    def test_20_search_and_filters(self):
        first_id = self.create_period()

        second_id = self.create_period(
            name="Semester 2 Final",
            period_type="final",
            start_date="2027-01-10",
            end_date="2027-01-25",
        )

        update_assessment_period_status(second_id, "active", actor_user_id=self.admin_id)

        self.assertEqual(
            len(get_assessment_periods(academic_year_id=self.year_id, actor_user_id=self.admin_id)),
            2,
        )
        self.assertEqual(
            len(get_assessment_periods(status="planned", actor_user_id=self.admin_id)),
            1,
        )
        self.assertEqual(
            len(get_assessment_periods(status="active", actor_user_id=self.admin_id)),
            1,
        )
        self.assertEqual(
            get_assessment_periods(search="Semester 2", actor_user_id=self.admin_id)[0]["id"],
            second_id,
        )
        self.assertEqual(
            get_assessment_periods(search="final", actor_user_id=self.admin_id)[0]["id"],
            second_id,
        )
        self.assertEqual(
            get_assessment_periods(search="2027-01-10", actor_user_id=self.admin_id)[0]["id"],
            second_id,
        )
        self.assertEqual(
            get_assessment_periods(search="not-found", actor_user_id=self.admin_id),
            [],
        )
        self.assertIsNotNone(get_assessment_period(first_id, actor_user_id=self.admin_id))

    def test_21_get_missing_period(self):
        self.assertIsNone(get_assessment_period(999, actor_user_id=self.admin_id))

    def test_22_reject_invalid_status_filter(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            get_assessment_periods(status="archived", actor_user_id=self.admin_id)

    def test_23_reject_invalid_assessment_period_ids(self):
        for value in (0, -1, True, False, None, "abc", 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    get_assessment_period(value, actor_user_id=self.admin_id)

    def test_24_database_integrity_and_foreign_keys(self):
        self.create_period()

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    def test_staff_can_read_assessment_periods(self):
        period_id = self.create_period()

        period = get_assessment_period(
            period_id,
            actor_user_id=self.staff_id,
        )
        periods = get_assessment_periods(
            academic_year_id=self.year_id,
            actor_user_id=self.staff_id,
        )

        self.assertEqual(period["id"], period_id)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["id"], period_id)

    def test_staff_cannot_change_assessment_periods(self):
        period_id = self.create_period()

        with self.assertRaises(PermissionError):
            create_assessment_period(
                sample_period(
                    academic_year_id=self.year_id,
                    name="Staff Created Period",
                    start_date="2026-11-01",
                    end_date="2026-11-15",
                ),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_assessment_period(
                period_id,
                sample_period(
                    academic_year_id=self.year_id,
                    name="Unauthorized Update",
                ),
                actor_user_id=self.staff_id,
            )

        with self.assertRaises(PermissionError):
            update_assessment_period_status(
                period_id,
                "active",
                actor_user_id=self.staff_id,
            )

        unchanged = get_assessment_period(
            period_id,
            actor_user_id=self.admin_id,
        )
        self.assertEqual(unchanged["name"], "Semester 1 Midterm")
        self.assertEqual(unchanged["status"], "planned")


if __name__ == "__main__":
    unittest.main()
