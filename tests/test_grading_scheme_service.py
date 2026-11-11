import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database
from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
from services.grading_scheme_service import (
    create_grading_scheme,
    get_grading_scheme,
    get_grading_schemes,
    update_grading_scheme,
    create_grade_band,
    get_grade_band,
    get_grade_bands,
    update_grade_band,
    delete_grade_band,
    activate_grading_scheme,
    archive_grading_scheme,
    get_grade_for_percentage,
)


def sample_scheme(**overrides):
    data = {
        "class_id": 1,
        "academic_year_id": 1,
        "name": "Standard Grading",
    }
    data.update(overrides)
    return data


def sample_band(**overrides):
    data = {
        "grade_label": "A",
        "min_percentage": 80,
        "grade_point": 4.0,
        "remark": "Excellent",
    }
    data.update(overrides)
    return data


class GradingSchemeServiceTests(unittest.TestCase):

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

        with database_module.get_connection() as connection:
            connection.execute("""
                INSERT INTO classes (name, description)
                VALUES ('Grade 10', 'Test class')
            """)

            connection.execute("""
                INSERT INTO classes (name, description)
                VALUES ('Grade 11', 'Second test class')
            """)

            connection.execute("""
                INSERT INTO academic_years (
                    name, start_date, end_date, is_current
                )
                VALUES (
                    '2026-2027',
                    '2026-09-01',
                    '2027-06-30',
                    0
                )
            """)

            connection.execute("""
                INSERT INTO academic_years (
                    name, start_date, end_date, is_current
                )
                VALUES (
                    '2027-2028',
                    '2027-09-01',
                    '2028-06-30',
                    0
                )
            """)

    def create_scheme(self, **overrides):
        return create_grading_scheme(
            sample_scheme(**overrides),
            actor_user_id=self.admin_id,
        )

    def add_band(self, scheme_id, **overrides):
        return create_grade_band(
            scheme_id,
            sample_band(**overrides),
            actor_user_id=self.admin_id,
        )

    def add_valid_bands(self, scheme_id):
        self.add_band(
            scheme_id,
            grade_label="F",
            min_percentage=0,
            grade_point=0,
            remark="Needs improvement",
        )
        self.add_band(
            scheme_id,
            grade_label="C",
            min_percentage=50,
            grade_point=2,
            remark="Satisfactory",
        )
        self.add_band(
            scheme_id,
            grade_label="A",
            min_percentage=80,
            grade_point=4,
            remark="Excellent",
        )

    def create_active_scheme(self, **overrides):
        scheme_id = self.create_scheme(**overrides)
        self.add_valid_bands(scheme_id)
        activate_grading_scheme(scheme_id, actor_user_id=self.admin_id)
        return scheme_id

    # --------------------------------------------------
    # GRADING SCHEME
    # --------------------------------------------------

    def test_01_create_and_retrieve_scheme(self):
        scheme_id = self.create_scheme()
        scheme = get_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(scheme)
        self.assertEqual(scheme["class_id"], 1)
        self.assertEqual(scheme["academic_year_id"], 1)
        self.assertEqual(scheme["name"], "Standard Grading")
        self.assertEqual(scheme["version_no"], 1)
        self.assertEqual(scheme["status"], "draft")
        self.assertEqual(scheme["class_name"], "Grade 10")
        self.assertEqual(scheme["academic_year_name"], "2026-2027")
        self.assertEqual(scheme["band_count"], 0)

    def test_02_automatically_increment_scheme_version(self):
        first = self.create_scheme()
        second = self.create_scheme()

        self.assertEqual(
            get_grading_scheme(first, actor_user_id=self.admin_id)["version_no"],
            1,
        )
        self.assertEqual(
            get_grading_scheme(second, actor_user_id=self.admin_id)["version_no"],
            2,
        )

    def test_03_version_numbers_are_independent_per_class(self):
        first = self.create_scheme(class_id=1)
        second = self.create_scheme(class_id=2)

        self.assertEqual(
            get_grading_scheme(first, actor_user_id=self.admin_id)["version_no"],
            1,
        )
        self.assertEqual(
            get_grading_scheme(second, actor_user_id=self.admin_id)["version_no"],
            1,
        )

    def test_04_version_numbers_are_independent_per_year(self):
        first = self.create_scheme(academic_year_id=1)
        second = self.create_scheme(academic_year_id=2)

        self.assertEqual(
            get_grading_scheme(first, actor_user_id=self.admin_id)["version_no"],
            1,
        )
        self.assertEqual(
            get_grading_scheme(second, actor_user_id=self.admin_id)["version_no"],
            1,
        )

    def test_05_trim_scheme_name(self):
        scheme_id = self.create_scheme(
            name="  Standard Grading  "
        )

        self.assertEqual(
            get_grading_scheme(scheme_id, actor_user_id=self.admin_id)["name"],
            "Standard Grading",
        )

    def test_06_reject_missing_class(self):
        with self.assertRaisesRegex(ValueError, "class"):
            self.create_scheme(class_id=999)

    def test_07_reject_missing_academic_year(self):
        with self.assertRaisesRegex(ValueError, "academic year"):
            self.create_scheme(academic_year_id=999)

    def test_08_reject_invalid_scheme_data(self):
        invalid_cases = [
            ("missing name", {"name": ""}),
            ("invalid class ID", {"class_id": -1}),
            ("fractional class ID", {"class_id": 1.5}),
            ("boolean class ID", {"class_id": True}),
            ("unexpected field", {"status": "active"}),
        ]

        for label, overrides in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.create_scheme(**overrides)

    def test_09_retrieve_missing_scheme(self):
        self.assertIsNone(get_grading_scheme(999, actor_user_id=self.admin_id))

    def test_10_list_all_schemes(self):
        self.create_scheme()
        self.create_scheme(class_id=2)

        schemes = get_grading_schemes(actor_user_id=self.admin_id)

        self.assertEqual(len(schemes), 2)

    def test_11_filter_schemes_by_class(self):
        first = self.create_scheme(class_id=1)
        self.create_scheme(class_id=2)

        schemes = get_grading_schemes(class_id=1, actor_user_id=self.admin_id)

        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0]["id"], first)

    def test_12_filter_schemes_by_academic_year(self):
        self.create_scheme(academic_year_id=1)
        second = self.create_scheme(academic_year_id=2)

        schemes = get_grading_schemes(academic_year_id=2, actor_user_id=self.admin_id)

        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0]["id"], second)

    def test_13_filter_schemes_by_status(self):
        self.create_scheme()
        self.create_active_scheme()

        schemes = get_grading_schemes(status="active", actor_user_id=self.admin_id)

        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0]["status"], "active")

    def test_14_search_schemes(self):
        self.create_scheme(name="Standard Mathematics")
        self.create_scheme(name="Science Grading")

        schemes = get_grading_schemes(search="Mathematics", actor_user_id=self.admin_id)

        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0]["name"], "Standard Mathematics")

    def test_15_reject_invalid_status_filter(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            get_grading_schemes(status="published", actor_user_id=self.admin_id)

    def test_16_update_draft_scheme_name(self):
        scheme_id = self.create_scheme()

        update_grading_scheme(
            scheme_id,
            {"name": "Updated Grading"},
         actor_user_id=self.admin_id)

        self.assertEqual(
            get_grading_scheme(scheme_id, actor_user_id=self.admin_id)["name"],
            "Updated Grading",
        )

    def test_17_reject_updating_active_scheme(self):
        scheme_id = self.create_active_scheme()

        with self.assertRaisesRegex(ValueError, "Only draft"):
            update_grading_scheme(
                scheme_id,
                {"name": "Changed"},
             actor_user_id=self.admin_id)

    def test_18_reject_invalid_scheme_update_fields(self):
        scheme_id = self.create_scheme()

        with self.assertRaisesRegex(ValueError, "Only the grading scheme name"):
            update_grading_scheme(
                scheme_id,
                {
                    "name": "Changed",
                    "status": "active",
                },
             actor_user_id=self.admin_id)

    def test_19_reject_updating_missing_scheme(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            update_grading_scheme(
                999,
                {"name": "Missing"},
             actor_user_id=self.admin_id)

    # --------------------------------------------------
    # GRADE BANDS
    # --------------------------------------------------

    def test_20_create_and_retrieve_grade_band(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id)

        band = get_grade_band(band_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(band)
        self.assertEqual(band["grading_scheme_id"], scheme_id)
        self.assertEqual(band["grade_label"], "A")
        self.assertEqual(band["min_percentage"], 80)
        self.assertEqual(band["grade_point"], 4)
        self.assertEqual(band["remark"], "Excellent")

    def test_21_list_grade_bands_in_descending_order(self):
        scheme_id = self.create_scheme()
        self.add_band(
            scheme_id,
            grade_label="F",
            min_percentage=0,
        )
        self.add_band(
            scheme_id,
            grade_label="C",
            min_percentage=50,
        )
        self.add_band(
            scheme_id,
            grade_label="A",
            min_percentage=80,
        )

        bands = get_grade_bands(scheme_id, actor_user_id=self.admin_id)

        self.assertEqual(
            [band["grade_label"] for band in bands],
            ["A", "C", "F"],
        )

    def test_22_reject_listing_bands_for_missing_scheme(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            get_grade_bands(999, actor_user_id=self.admin_id)

    def test_23_reject_invalid_grade_band_data(self):
        scheme_id = self.create_scheme()

        invalid_cases = [
            ("missing label", {"grade_label": ""}),
            ("invalid label type", {"grade_label": 123}),
            ("percentage below zero", {"min_percentage": -1}),
            ("percentage above 100", {"min_percentage": 101}),
            ("fractional numeric string", {"min_percentage": "80"}),
            ("boolean percentage", {"min_percentage": True}),
            ("negative grade point", {"grade_point": -1}),
            ("invalid remark", {"remark": 123}),
        ]

        for label, overrides in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.add_band(scheme_id, **overrides)

    def test_24_reject_duplicate_grade_label(self):
        scheme_id = self.create_scheme()

        self.add_band(
            scheme_id,
            grade_label="A",
            min_percentage=80,
        )

        with self.assertRaisesRegex(ValueError, "grade label already exists"):
            self.add_band(
                scheme_id,
                grade_label="a",
                min_percentage=90,
            )

    def test_25_reject_duplicate_minimum_percentage(self):
        scheme_id = self.create_scheme()

        self.add_band(
            scheme_id,
            grade_label="A",
            min_percentage=80,
        )

        with self.assertRaisesRegex(ValueError, "minimum percentage already exists"):
            self.add_band(
                scheme_id,
                grade_label="B",
                min_percentage=80,
            )

    def test_26_update_draft_grade_band(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id)

        update_grade_band(
            band_id,
            {
                "grade_label": "B",
                "min_percentage": 70,
                "grade_point": 3,
                "remark": "Good",
            },
         actor_user_id=self.admin_id)

        band = get_grade_band(band_id, actor_user_id=self.admin_id)

        self.assertEqual(band["grade_label"], "B")
        self.assertEqual(band["min_percentage"], 70)
        self.assertEqual(band["grade_point"], 3)
        self.assertEqual(band["remark"], "Good")

    def test_27_delete_draft_grade_band(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id)

        delete_grade_band(band_id, actor_user_id=self.admin_id)

        self.assertIsNone(get_grade_band(band_id, actor_user_id=self.admin_id))

    def test_28_reject_updating_missing_grade_band(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            update_grade_band(
                999,
                {
                    "grade_label": "A",
                    "min_percentage": 80,
                },
             actor_user_id=self.admin_id)

    def test_29_reject_deleting_missing_grade_band(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            delete_grade_band(999, actor_user_id=self.admin_id)

    def test_30_reject_editing_active_grade_band(self):
        scheme_id = self.create_active_scheme()
        bands = get_grade_bands(scheme_id, actor_user_id=self.admin_id)
        band_id = bands[0]["id"]

        with self.assertRaisesRegex(ValueError, "Only draft"):
            update_grade_band(
                band_id,
                {
                    "grade_label": "Changed",
                    "min_percentage": 90,
                },
             actor_user_id=self.admin_id)

    def test_31_reject_deleting_active_grade_band(self):
        scheme_id = self.create_active_scheme()
        band_id = get_grade_bands(scheme_id, actor_user_id=self.admin_id)[0]["id"]

        with self.assertRaisesRegex(ValueError, "Only draft"):
            delete_grade_band(band_id, actor_user_id=self.admin_id)

    # --------------------------------------------------
    # ACTIVATION AND ARCHIVING
    # --------------------------------------------------

    def test_32_activation_requires_valid_bands(self):
        scheme_id = self.create_scheme()

        with self.assertRaisesRegex(ValueError, "at least two grade bands"):
            activate_grading_scheme(scheme_id, actor_user_id=self.admin_id)

    def test_33_activate_valid_scheme(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)

        activate_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        self.assertEqual(
            get_grading_scheme(scheme_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_34_reject_second_active_scheme(self):
        first = self.create_active_scheme()
        second = self.create_scheme()
        self.add_valid_bands(second)

        with self.assertRaisesRegex(ValueError, "already active"):
            activate_grading_scheme(second, actor_user_id=self.admin_id)

        self.assertEqual(
            get_grading_scheme(first, actor_user_id=self.admin_id)["status"],
            "active",
        )
        self.assertEqual(
            get_grading_scheme(second, actor_user_id=self.admin_id)["status"],
            "draft",
        )

    def test_35_archive_active_scheme(self):
        scheme_id = self.create_active_scheme()

        archive_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        self.assertEqual(
            get_grading_scheme(scheme_id, actor_user_id=self.admin_id)["status"],
            "archived",
        )

    def test_36_archive_draft_scheme(self):
        scheme_id = self.create_scheme()

        archive_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        self.assertEqual(
            get_grading_scheme(scheme_id, actor_user_id=self.admin_id)["status"],
            "archived",
        )

    def test_37_reject_archiving_missing_scheme(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            archive_grading_scheme(999, actor_user_id=self.admin_id)

    def test_38_reject_archiving_twice(self):
        scheme_id = self.create_scheme()

        archive_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "already archived"):
            archive_grading_scheme(scheme_id, actor_user_id=self.admin_id)

    def test_39_create_next_version_after_archiving(self):
        first = self.create_active_scheme()

        archive_grading_scheme(first, actor_user_id=self.admin_id)

        second = self.create_scheme()

        self.assertEqual(
            get_grading_scheme(second, actor_user_id=self.admin_id)["version_no"],
            2,
        )

    # --------------------------------------------------
    # GRADE CALCULATION
    # --------------------------------------------------

    def test_40_grade_lookup_at_exact_thresholds(self):
        scheme_id = self.create_active_scheme()

        expected = {
            0: "F",
            49.99: "F",
            50: "C",
            79.99: "C",
            80: "A",
            100: "A",
        }

        for percentage, grade_label in expected.items():
            with self.subTest(percentage=percentage):
                grade = get_grade_for_percentage(
                    scheme_id,
                    percentage,
                 actor_user_id=self.admin_id)
                self.assertEqual(
                    grade["grade_label"],
                    grade_label,
                )

    def test_41_grade_lookup_rejects_draft_scheme(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)

        with self.assertRaisesRegex(ValueError, "active or archived"):
            get_grade_for_percentage(scheme_id, 85, actor_user_id=self.admin_id)

    def test_42_grade_lookup_supports_archived_scheme(self):
        scheme_id = self.create_active_scheme()
        archive_grading_scheme(scheme_id, actor_user_id=self.admin_id)

        grade = get_grade_for_percentage(scheme_id, 85, actor_user_id=self.admin_id)

        self.assertEqual(grade["grade_label"], "A")

    def test_43_reject_invalid_grade_lookup_percentages(self):
        scheme_id = self.create_active_scheme()

        invalid_values = (
            -0.01,
            100.01,
            True,
            "85",
            None,
            float("nan"),
            float("inf"),
        )

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    get_grade_for_percentage(
                        scheme_id,
                        value,
                     actor_user_id=self.admin_id)

    def test_44_reject_grade_lookup_for_missing_scheme(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            get_grade_for_percentage(999, 85, actor_user_id=self.admin_id)


    # --------------------------------------------------
    # ROLE AUTHORIZATION
    # --------------------------------------------------

    def test_45_staff_can_read_schemes_and_calculate_grades(self):
        scheme_id = self.create_active_scheme()

        scheme = get_grading_scheme(
            scheme_id,
            actor_user_id=self.staff_id,
        )
        schemes = get_grading_schemes(
            class_id=1,
            academic_year_id=1,
            status="active",
            actor_user_id=self.staff_id,
        )
        bands = get_grade_bands(
            scheme_id,
            actor_user_id=self.staff_id,
        )
        band = get_grade_band(
            bands[0]["id"],
            actor_user_id=self.staff_id,
        )
        grade = get_grade_for_percentage(
            scheme_id,
            85,
            actor_user_id=self.staff_id,
        )

        self.assertEqual(scheme["id"], scheme_id)
        self.assertEqual(len(schemes), 1)
        self.assertEqual(len(bands), 3)
        self.assertIsNotNone(band)
        self.assertEqual(grade["grade_label"], "A")

    def test_46_staff_cannot_change_grading_configuration(self):
        draft_scheme_id = self.create_scheme()
        band_id = self.add_band(draft_scheme_id)
        active_scheme_id = self.create_active_scheme()

        denied_operations = {
            "create scheme": lambda: create_grading_scheme(
                sample_scheme(name="Staff Attempt"),
                actor_user_id=self.staff_id,
            ),
            "update scheme": lambda: update_grading_scheme(
                draft_scheme_id,
                {"name": "Staff Attempt"},
                actor_user_id=self.staff_id,
            ),
            "create grade band": lambda: create_grade_band(
                draft_scheme_id,
                sample_band(
                    grade_label="B",
                    min_percentage=50,
                    grade_point=3,
                ),
                actor_user_id=self.staff_id,
            ),
            "update grade band": lambda: update_grade_band(
                band_id,
                sample_band(
                    grade_label="B",
                    min_percentage=50,
                    grade_point=3,
                ),
                actor_user_id=self.staff_id,
            ),
            "delete grade band": lambda: delete_grade_band(
                band_id,
                actor_user_id=self.staff_id,
            ),
            "activate scheme": lambda: activate_grading_scheme(
                draft_scheme_id,
                actor_user_id=self.staff_id,
            ),
            "archive scheme": lambda: archive_grading_scheme(
                active_scheme_id,
                actor_user_id=self.staff_id,
            ),
        }

        for operation, call in denied_operations.items():
            with self.subTest(operation=operation):
                with self.assertRaises(PermissionError):
                    call()

        # Confirm denied operations did not change the stored records.
        unchanged_scheme = get_grading_scheme(
            draft_scheme_id,
            actor_user_id=self.admin_id,
        )
        unchanged_band = get_grade_band(
            band_id,
            actor_user_id=self.admin_id,
        )
        unchanged_active_scheme = get_grading_scheme(
            active_scheme_id,
            actor_user_id=self.admin_id,
        )

        self.assertEqual(unchanged_scheme["name"], "Standard Grading")
        self.assertIsNotNone(unchanged_band)
        self.assertEqual(unchanged_active_scheme["status"], "active")


if __name__ == "__main__":
    unittest.main()
