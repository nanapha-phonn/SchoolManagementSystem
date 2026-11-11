import sqlite3
import tempfile
import unittest
from pathlib import Path

import database.database as database_module


class StudentSubjectResultSchemaTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database_module.DB_PATH
        database_module.DB_PATH = str(
            Path(self.temp_dir.name) / "test.db"
        )

        database_module.initialize_database()
        self.connection = database_module.get_connection()

        self.year_id = self.connection.execute("""
            INSERT INTO academic_years
                (name, start_date, end_date)
            VALUES ('2026-2027', '2026-09-01', '2027-06-30')
        """).lastrowid

        self.class_id = self.connection.execute("""
            INSERT INTO classes (name) VALUES ('Class A')
        """).lastrowid

        self.section_id = self.connection.execute("""
            INSERT INTO sections (class_id, name)
            VALUES (?, 'Section 1')
        """, (self.class_id,)).lastrowid

        self.student_id = self.connection.execute("""
            INSERT INTO students
                (admission_no, first_name, last_name)
            VALUES ('ST001', 'Test', 'Student')
        """).lastrowid

        self.teacher_id = self.connection.execute("""
            INSERT INTO teachers
                (employee_no, first_name, last_name)
            VALUES ('TE001', 'Test', 'Teacher')
        """).lastrowid

        self.subject_id = self.connection.execute("""
            INSERT INTO subjects (subject_code, name)
            VALUES ('MATH', 'Mathematics')
        """).lastrowid

        self.enrollment_id = self.connection.execute("""
            INSERT INTO enrollments (
                student_id, section_id, academic_year_id,
                enrolled_on
            )
            VALUES (?, ?, ?, '2026-09-15')
        """, (
            self.student_id, self.section_id, self.year_id
        )).lastrowid

        self.assignment_id = self.connection.execute("""
            INSERT INTO teacher_subject_assignments (
                teacher_id, subject_id, section_id,
                academic_year_id, assigned_on
            )
            VALUES (?, ?, ?, ?, '2026-09-20')
        """, (
            self.teacher_id, self.subject_id,
            self.section_id, self.year_id
        )).lastrowid

        self.period_id = self.connection.execute("""
            INSERT INTO assessment_periods (
                academic_year_id, name, period_type,
                start_date, end_date
            )
            VALUES (
                ?, 'Semester 1', 'midterm',
                '2026-10-01', '2026-10-15'
            )
        """, (self.year_id,)).lastrowid

        self.scheme_id = self.connection.execute("""
            INSERT INTO grading_schemes (
                class_id, academic_year_id, name, version_no
            )
            VALUES (?, ?, 'Standard Scheme', 1)
        """, (self.class_id, self.year_id)).lastrowid

        self.add_band("F", 0)
        self.add_band("A", 80, 4.0)
        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        database_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def add_band(self, label, minimum, grade_point=None):
        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label,
                min_percentage, grade_point
            )
            VALUES (?, ?, ?, ?)
        """, (self.scheme_id, label, minimum, grade_point))

    def activate_period(self):
        self.connection.execute("""
            UPDATE assessment_periods
            SET status = 'active'
            WHERE id = ?
        """, (self.period_id,))
        self.connection.commit()

    def activate_scheme(self):
        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
        """, (self.scheme_id,))
        self.connection.commit()

    def activate_references(self):
        self.activate_period()
        self.activate_scheme()

    def insert_result(self, **overrides):
        values = {
            "enrollment_id": self.enrollment_id,
            "assessment_period_id": self.period_id,
            "teacher_subject_assignment_id": self.assignment_id,
            "subject_id": self.subject_id,
            "grading_scheme_id": self.scheme_id,
            "marks_obtained": 85,
            "maximum_marks": 100,
        }
        values.update(overrides)

        return self.connection.execute("""
            INSERT INTO student_subject_results (
                enrollment_id, assessment_period_id,
                teacher_subject_assignment_id, subject_id,
                grading_scheme_id, marks_obtained, maximum_marks
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tuple(values.values())).lastrowid

    def test_01_schema_objects_exist(self):
        tables = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name FROM sqlite_master WHERE type = 'table'
            """)
        }
        self.assertIn("student_subject_results", tables)

        indexes = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'index'
                  AND tbl_name = 'student_subject_results'
                  AND name NOT LIKE 'sqlite_%'
            """)
        }
        expected_indexes = {
            "idx_student_subject_results_period_enrollment",
            "idx_student_subject_results_assignment",
            "idx_student_subject_results_grading_scheme",
        }
        self.assertEqual(indexes, expected_indexes)

        triggers = {
            row["name"]
            for row in self.connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'trigger'
                  AND tbl_name = 'student_subject_results'
            """)
        }
        self.assertEqual(len(triggers), 6)

    def test_02_valid_result_can_be_created(self):
        self.activate_references()
        result_id = self.insert_result()
        self.connection.commit()

        row = self.connection.execute("""
            SELECT * FROM student_subject_results WHERE id = ?
        """, (result_id,)).fetchone()

        self.assertEqual(row["marks_obtained"], 85)
        self.assertEqual(row["maximum_marks"], 100)

    def test_03_planned_assessment_period_rejects_result(self):
        self.activate_scheme()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "references do not match"
        ):
            self.insert_result()

    def test_04_draft_scheme_rejects_result(self):
        self.activate_period()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "references do not match"
        ):
            self.insert_result()

    def test_05_duplicate_result_is_rejected(self):
        self.activate_references()
        self.insert_result()
        self.connection.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_result()

    def test_06_invalid_marks_are_rejected(self):
        self.activate_references()

        for marks, maximum in (
            (-1, 100),
            (101, 100),
            (50, 0),
            (50, -10),
        ):
            with self.subTest(marks=marks, maximum=maximum):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.insert_result(
                        marks_obtained=marks,
                        maximum_marks=maximum,
                    )
                self.connection.rollback()

    def test_07_completed_period_locks_result(self):
        self.activate_references()
        result_id = self.insert_result()
        self.connection.commit()

        self.connection.execute("""
            UPDATE assessment_periods
            SET status = 'completed'
            WHERE id = ?
        """, (self.period_id,))
        self.connection.commit()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "only be changed"
        ):
            self.connection.execute("""
                UPDATE student_subject_results
                SET marks_obtained = 90
                WHERE id = ?
            """, (result_id,))

        self.connection.rollback()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "cannot be deleted"
        ):
            self.connection.execute("""
                DELETE FROM student_subject_results
                WHERE id = ?
            """, (result_id,))

    def test_08_result_academic_identity_is_immutable(self):
        self.activate_references()
        result_id = self.insert_result()
        self.connection.commit()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "references cannot be changed"
        ):
            self.connection.execute("""
                UPDATE student_subject_results
                SET subject_id = 999
                WHERE id = ?
            """, (result_id,))

    def test_09_assignment_cannot_end_before_assessment(self):
        self.activate_references()
        self.insert_result()
        self.connection.commit()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError, "cannot invalidate existing"
        ):
            self.connection.execute("""
                UPDATE teacher_subject_assignments
                SET ended_on = '2026-09-30', status = 'inactive'
                WHERE id = ?
            """, (self.assignment_id,))

    def test_10_database_integrity(self):
        self.activate_references()
        self.insert_result()
        self.connection.commit()

        integrity = self.connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_keys = self.connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


if __name__ == "__main__":
    unittest.main()
