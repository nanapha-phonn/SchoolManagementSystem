import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from models.academic_year import AcademicYear
from services.academic_year_service import (
    create_academic_year,
    get_academic_year,
    get_academic_years,
    set_current_academic_year,
    update_academic_year,
)
from services.auth_service import create_initial_admin, authenticate_user


def sample_year(**overrides):
    data = {
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": False,
    }

    data.update(overrides)
    return data


class AcademicYearServiceTests(unittest.TestCase):

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

    def _call_create_academic_year(self, data):
        return create_academic_year(data, actor_user_id=self.admin_id)

    def _call_get_academic_year(self, year_id):
        return get_academic_year(year_id, actor_user_id=self.admin_id)

    def _call_get_academic_years(self, search=""):
        return get_academic_years(search, actor_user_id=self.admin_id)

    def _call_update_academic_year(self, year_id, data):
        return update_academic_year(
            year_id,
            data,
            actor_user_id=self.admin_id,
        )

    def _call_set_current_academic_year(self, year_id):
        return set_current_academic_year(
            year_id,
            actor_user_id=self.admin_id,
        )

    def test_01_create_and_retrieve_academic_year(self):
        year_id = self._call_create_academic_year(sample_year())

        year = self._call_get_academic_year(year_id)

        self.assertIsNotNone(year)
        self.assertEqual(year["name"], "2026-2027")
        self.assertEqual(year["start_date"], "2026-09-01")
        self.assertEqual(year["end_date"], "2027-06-30")
        self.assertEqual(year["is_current"], 0)

    def test_02_normalize_academic_year_name(self):
        year_id = self._call_create_academic_year(
            sample_year(name="  2026-2027  ")
        )

        year = self._call_get_academic_year(year_id)

        self.assertEqual(year["name"], "2026-2027")

    def test_03_accept_future_academic_year_dates(self):
        year_id = self._call_create_academic_year(
            sample_year(
                name="2099-2100",
                start_date="2099-09-01",
                end_date="2100-06-30",
            )
        )

        self.assertIsNotNone(self._call_get_academic_year(year_id))

    def test_04_reject_invalid_academic_year_data(self):
        invalid_cases = [
            ("empty name", {"name": ""}),
            ("whitespace name", {"name": "   "}),
            ("long name", {"name": "A" * 101}),
            ("empty start date", {"start_date": ""}),
            ("invalid start date", {"start_date": "01-09-2026"}),
            ("non-padded date", {"start_date": "2026-9-01"}),
            ("invalid calendar date", {"start_date": "2026-02-30"}),
            ("empty end date", {"end_date": ""}),
            ("invalid end date", {"end_date": "not-a-date"}),
            (
                "end before start",
                {
                    "start_date": "2027-09-01",
                    "end_date": "2027-06-30",
                },
            ),
            ("invalid current flag", {"is_current": "yes"}),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                with self.assertRaises(ValueError):
                    AcademicYear(
                        **sample_year(**overrides)
                    ).validate()

        self.assertEqual(len(self._call_get_academic_years()), 0)

    def test_05_reject_duplicate_academic_year_name(self):
        self._call_create_academic_year(sample_year())

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            self._call_create_academic_year(sample_year())

        self.assertEqual(len(self._call_get_academic_years()), 1)

    def test_06_retrieve_missing_academic_year(self):
        self.assertIsNone(self._call_get_academic_year(999999))

    def test_07_search_academic_years(self):
        self._call_create_academic_year(sample_year())

        self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            )
        )

        self.assertEqual(len(self._call_get_academic_years("2026")), 1)
        self.assertEqual(len(self._call_get_academic_years("2027")), 2)
        self.assertEqual(len(self._call_get_academic_years("not-found")), 0)

    def test_08_update_academic_year(self):
        year_id = self._call_create_academic_year(sample_year())

        self._call_update_academic_year(
            year_id,
            sample_year(
                name="Updated Academic Year",
                start_date="2026-10-01",
                end_date="2027-07-31",
            )
        )

        year = self._call_get_academic_year(year_id)

        self.assertEqual(year["name"], "Updated Academic Year")
        self.assertEqual(year["start_date"], "2026-10-01")
        self.assertEqual(year["end_date"], "2027-07-31")

    def test_09_reject_duplicate_name_during_update(self):
        first_id = self._call_create_academic_year(sample_year())

        self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "already exists"
        ):
            self._call_update_academic_year(
                first_id,
                sample_year(name="2027-2028")
            )

        self.assertEqual(
            self._call_get_academic_year(first_id)["name"],
            "2026-2027"
        )

    def test_10_reject_update_for_missing_year(self):
        with self.assertRaisesRegex(
            ValueError,
            "record was not found"
        ):
            self._call_update_academic_year(
                999999,
                sample_year()
            )

    def test_11_create_current_year_unsets_previous_current_year(self):
        first_id = self._call_create_academic_year(
            sample_year(is_current=True)
        )

        second_id = self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
                is_current=True,
            )
        )

        self.assertEqual(
            self._call_get_academic_year(first_id)["is_current"],
            0
        )

        self.assertEqual(
            self._call_get_academic_year(second_id)["is_current"],
            1
        )

    def test_12_creating_non_current_year_preserves_current_year(self):
        first_id = self._call_create_academic_year(
            sample_year(is_current=True)
        )

        self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
                is_current=False,
            )
        )

        self.assertEqual(
            self._call_get_academic_year(first_id)["is_current"],
            1
        )

    def test_13_set_current_year_switches_current_year(self):
        first_id = self._call_create_academic_year(
            sample_year(is_current=True)
        )

        second_id = self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            )
        )

        self._call_set_current_academic_year(second_id)

        self.assertEqual(
            self._call_get_academic_year(first_id)["is_current"],
            0
        )

        self.assertEqual(
            self._call_get_academic_year(second_id)["is_current"],
            1
        )

    def test_14_update_can_set_and_clear_current_year(self):
        first_id = self._call_create_academic_year(
            sample_year(is_current=True)
        )

        second_id = self._call_create_academic_year(
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
            )
        )

        self._call_update_academic_year(
            second_id,
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
                is_current=True,
            )
        )

        self.assertEqual(
            self._call_get_academic_year(first_id)["is_current"],
            0
        )

        self.assertEqual(
            self._call_get_academic_year(second_id)["is_current"],
            1
        )

        self._call_update_academic_year(
            second_id,
            sample_year(
                name="2027-2028",
                start_date="2027-09-01",
                end_date="2028-06-30",
                is_current=False,
            )
        )

        self.assertEqual(
            self._call_get_academic_year(second_id)["is_current"],
            0
        )

    def test_15_missing_year_cannot_change_current_year(self):
        year_id = self._call_create_academic_year(
            sample_year(is_current=True)
        )

        with self.assertRaisesRegex(
            ValueError,
            "record was not found"
        ):
            self._call_set_current_academic_year(999999)

        self.assertEqual(
            self._call_get_academic_year(year_id)["is_current"],
            1
        )

    def test_16_reject_invalid_academic_year_ids(self):
        for invalid_id in (0, -1, "invalid", None, True):
            with self.subTest(academic_year_id=invalid_id):
                with self.assertRaises(ValueError):
                    self._call_get_academic_year(invalid_id)

    def test_17_database_enforces_single_current_year(self):
        self._call_create_academic_year(sample_year(is_current=True))

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        INSERT INTO academic_years (
                            name,
                            start_date,
                            end_date,
                            is_current
                        )
                        VALUES (?, ?, ?, 1)
                        """,
                        (
                            "Direct Insert",
                            "2028-09-01",
                            "2029-06-30",
                        )
                    )

    def test_18_sqlite_database_integrity(self):
        self._call_create_academic_year(sample_year())

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])

    def test_19_unique_index_exists(self):
        with closing(database_module.get_connection()) as connection:
            indexes = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND name = 'idx_one_current_academic_year'
                """
            ).fetchall()

        self.assertEqual(len(indexes), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
