import sqlite3
import tempfile
import unittest
from pathlib import Path

import database.database as database_module


class GradingSchemeSchemaTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="grading_schema_test_"
        )
        self.original_db_path = database_module.DB_PATH

        database_module.DB_PATH = str(
            Path(self.temp_dir.name) / "grading_test.db"
        )

        database_module.initialize_database()
        self.connection = database_module.get_connection()

        self.connection.execute("""
            INSERT INTO classes (name, description)
            VALUES ('Test Class', 'Temporary test class')
        """)

        self.connection.execute("""
            INSERT INTO academic_years (
                name, start_date, end_date, is_current
            )
            VALUES (
                'Test Year', '2026-09-01', '2027-06-30', 0
            )
        """)

        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        database_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def create_scheme(self, version=1, name="Standard Grading"):
        cursor = self.connection.execute("""
            INSERT INTO grading_schemes (
                class_id,
                academic_year_id,
                name,
                version_no
            )
            VALUES (1, 1, ?, ?)
        """, (name, version))

        return cursor.lastrowid

    def add_band(
        self,
        scheme_id,
        label,
        minimum,
        grade_point=None,
        remark="",
    ):
        cursor = self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id,
                grade_label,
                min_percentage,
                grade_point,
                remark
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            scheme_id,
            label,
            minimum,
            grade_point,
            remark,
        ))

        return cursor.lastrowid

    def add_valid_bands(self, scheme_id):
        self.add_band(scheme_id, "F", 0)
        self.add_band(scheme_id, "A", 80, 4.0, "Excellent")

    def activate_scheme(self, scheme_id):
        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
        """, (scheme_id,))

    def expect_rejection(
        self,
        sql,
        parameters=(),
        expected_text=None,
    ):
        with self.assertRaises(sqlite3.IntegrityError) as context:
            self.connection.execute(sql, parameters)

        if expected_text:
            self.assertIn(
                expected_text,
                str(context.exception),
            )

    # --------------------------------------------------
    # SCHEMA
    # --------------------------------------------------

    def test_01_required_tables_indexes_and_triggers_exist(self):
        tables = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)
        }

        self.assertIn("grading_schemes", tables)
        self.assertIn("grade_bands", tables)

        indexes = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                  AND (
                      name LIKE '%grading%'
                      OR name LIKE '%grade_bands%'
                  )
            """)
        }

        self.assertIn(
            "idx_grading_schemes_class_year",
            indexes,
        )
        self.assertIn(
            "idx_one_active_grading_scheme_per_class_year",
            indexes,
        )
        self.assertIn(
            "idx_grade_bands_scheme_threshold",
            indexes,
        )

        triggers = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND (
                      name LIKE 'trg_grading_scheme_%'
                      OR name LIKE 'trg_grade_band_%'
                      OR name = 'trg_prevent_grading_scheme_delete'
                  )
            """)
        }

        self.assertEqual(len(triggers), 10)

    # --------------------------------------------------
    # SCHEME CREATION
    # --------------------------------------------------

    def test_02_new_scheme_starts_as_draft(self):
        scheme_id = self.create_scheme()

        row = self.connection.execute("""
            SELECT status
            FROM grading_schemes
            WHERE id = ?
        """, (scheme_id,)).fetchone()

        self.assertEqual(row["status"], "draft")

    def test_03_direct_active_creation_is_rejected(self):
        self.expect_rejection(
            """
            INSERT INTO grading_schemes (
                class_id,
                academic_year_id,
                name,
                version_no,
                status
            )
            VALUES (1, 1, 'Invalid Scheme', 1, 'active')
            """,
            expected_text="New grading schemes must start as draft",
        )

    def test_04_duplicate_version_is_rejected(self):
        self.create_scheme(version=1)

        with self.assertRaises(sqlite3.IntegrityError):
            self.create_scheme(version=1)

    def test_05_invalid_class_reference_is_rejected(self):
        self.expect_rejection("""
            INSERT INTO grading_schemes (
                class_id,
                academic_year_id,
                name,
                version_no
            )
            VALUES (999, 1, 'Invalid Class', 1)
        """)

    # --------------------------------------------------
    # GRADE BAND VALIDATION
    # --------------------------------------------------

    def test_06_grade_labels_are_case_insensitively_unique(self):
        scheme_id = self.create_scheme()

        self.add_band(scheme_id, "A", 80)

        self.expect_rejection(
            """
            INSERT INTO grade_bands (
                grading_scheme_id,
                grade_label,
                min_percentage
            )
            VALUES (?, 'a', 90)
            """,
            (scheme_id,),
        )

    def test_07_minimum_percentages_are_unique(self):
        scheme_id = self.create_scheme()

        self.add_band(scheme_id, "A", 80)

        self.expect_rejection(
            """
            INSERT INTO grade_bands (
                grading_scheme_id,
                grade_label,
                min_percentage
            )
            VALUES (?, 'B', 80)
            """,
            (scheme_id,),
        )

    def test_08_invalid_percentage_is_rejected(self):
        scheme_id = self.create_scheme()

        for percentage in (-1, 100.01):
            with self.subTest(percentage=percentage):
                self.expect_rejection(
                    """
                    INSERT INTO grade_bands (
                        grading_scheme_id,
                        grade_label,
                        min_percentage
                    )
                    VALUES (?, 'Invalid', ?)
                    """,
                    (scheme_id, percentage),
                )

    # --------------------------------------------------
    # ACTIVATION REQUIREMENTS
    # --------------------------------------------------

    def test_09_activation_without_bands_is_rejected(self):
        scheme_id = self.create_scheme()

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
            """,
            (scheme_id,),
            "at least two grade bands",
        )

    def test_10_activation_with_one_band_is_rejected(self):
        scheme_id = self.create_scheme()
        self.add_band(scheme_id, "F", 0)

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
            """,
            (scheme_id,),
            "at least two grade bands",
        )

    def test_11_activation_without_zero_threshold_is_rejected(self):
        scheme_id = self.create_scheme()

        self.add_band(scheme_id, "C", 50)
        self.add_band(scheme_id, "A", 80)

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
            """,
            (scheme_id,),
            "exactly one 0 percent threshold",
        )

    def test_12_valid_scheme_can_be_activated(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)

        self.activate_scheme(scheme_id)

        row = self.connection.execute("""
            SELECT status
            FROM grading_schemes
            WHERE id = ?
        """, (scheme_id,)).fetchone()

        self.assertEqual(row["status"], "active")

    def test_13_only_one_active_scheme_per_class_and_year(self):
        first = self.create_scheme(version=1)
        second = self.create_scheme(version=2)

        self.add_valid_bands(first)
        self.add_valid_bands(second)

        self.activate_scheme(first)

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
            """,
            (second,),
            "UNIQUE constraint failed",
        )

        row = self.connection.execute("""
            SELECT status
            FROM grading_schemes
            WHERE id = ?
        """, (second,)).fetchone()

        self.assertEqual(row["status"], "draft")

    # --------------------------------------------------
    # DRAFT AND HISTORICAL PROTECTION
    # --------------------------------------------------

    def test_14_draft_bands_can_be_updated_and_deleted(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id, "F", 0)

        self.connection.execute("""
            UPDATE grade_bands
            SET remark = 'Needs improvement'
            WHERE id = ?
        """, (band_id,))

        self.connection.execute("""
            DELETE FROM grade_bands
            WHERE id = ?
        """, (band_id,))

        count = self.connection.execute("""
            SELECT COUNT(*)
            FROM grade_bands
            WHERE grading_scheme_id = ?
        """, (scheme_id,)).fetchone()[0]

        self.assertEqual(count, 0)

    def test_15_active_scheme_cannot_receive_new_bands(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)
        self.activate_scheme(scheme_id)

        self.expect_rejection(
            """
            INSERT INTO grade_bands (
                grading_scheme_id,
                grade_label,
                min_percentage
            )
            VALUES (?, 'B', 70)
            """,
            (scheme_id,),
            "draft grading scheme",
        )

    def test_16_active_scheme_bands_cannot_be_updated(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id, "F", 0)
        self.add_band(scheme_id, "A", 80)
        self.activate_scheme(scheme_id)

        self.expect_rejection(
            """
            UPDATE grade_bands
            SET remark = 'Changed'
            WHERE id = ?
            """,
            (band_id,),
            "Only draft grading schemes",
        )

    def test_17_active_scheme_bands_cannot_be_deleted(self):
        scheme_id = self.create_scheme()
        band_id = self.add_band(scheme_id, "F", 0)
        self.add_band(scheme_id, "A", 80)
        self.activate_scheme(scheme_id)

        self.expect_rejection(
            """
            DELETE FROM grade_bands
            WHERE id = ?
            """,
            (band_id,),
            "cannot be deleted",
        )

    def test_18_grade_band_cannot_move_to_another_scheme(self):
        first = self.create_scheme(version=1)
        second = self.create_scheme(version=2)

        band_id = self.add_band(first, "F", 0)

        self.expect_rejection(
            """
            UPDATE grade_bands
            SET grading_scheme_id = ?
            WHERE id = ?
            """,
            (second, band_id),
            "cannot be moved",
        )

    def test_19_active_scheme_cannot_be_renamed(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)
        self.activate_scheme(scheme_id)

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET name = 'Changed Name'
            WHERE id = ?
            """,
            (scheme_id,),
            "Only draft grading schemes can be renamed",
        )

    def test_20_scheme_identity_and_version_are_immutable(self):
        scheme_id = self.create_scheme()

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET version_no = 99
            WHERE id = ?
            """,
            (scheme_id,),
            "identity and version cannot be changed",
        )

    def test_21_scheme_history_cannot_be_deleted(self):
        scheme_id = self.create_scheme()

        self.expect_rejection(
            """
            DELETE FROM grading_schemes
            WHERE id = ?
            """,
            (scheme_id,),
            "history cannot be deleted",
        )

    # --------------------------------------------------
    # VERSIONING AND ARCHIVING
    # --------------------------------------------------

    def test_22_active_scheme_can_be_archived(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)
        self.activate_scheme(scheme_id)

        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'archived'
            WHERE id = ?
        """, (scheme_id,))

        row = self.connection.execute("""
            SELECT status
            FROM grading_schemes
            WHERE id = ?
        """, (scheme_id,)).fetchone()

        self.assertEqual(row["status"], "archived")

    def test_23_archived_scheme_cannot_be_reactivated(self):
        scheme_id = self.create_scheme()
        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'archived'
            WHERE id = ?
        """, (scheme_id,))

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
            """,
            (scheme_id,),
            "Invalid grading scheme status transition",
        )

    def test_24_active_scheme_cannot_return_to_draft(self):
        scheme_id = self.create_scheme()
        self.add_valid_bands(scheme_id)
        self.activate_scheme(scheme_id)

        self.expect_rejection(
            """
            UPDATE grading_schemes
            SET status = 'draft'
            WHERE id = ?
            """,
            (scheme_id,),
            "Invalid grading scheme status transition",
        )

    def test_25_new_version_can_be_created_after_archiving(self):
        first = self.create_scheme(version=1)

        self.add_valid_bands(first)
        self.activate_scheme(first)

        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'archived'
            WHERE id = ?
        """, (first,))

        second = self.create_scheme(version=2)
        self.add_valid_bands(second)
        self.activate_scheme(second)

        active_count = self.connection.execute("""
            SELECT COUNT(*)
            FROM grading_schemes
            WHERE class_id = 1
              AND academic_year_id = 1
              AND status = 'active'
        """).fetchone()[0]

        self.assertEqual(active_count, 1)

    # --------------------------------------------------
    # DATABASE VERIFICATION
    # --------------------------------------------------

    def test_26_integrity_and_foreign_keys(self):
        integrity = self.connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_errors = self.connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_key_errors, [])


if __name__ == "__main__":
    unittest.main()
