import tempfile
import unittest
from pathlib import Path

import database.database as database_module

from services.student_subject_result_service import (
    create_student_subject_result,
)
from services.student_report_card_service import (
    get_student_report_card,
)


class StudentReportCardServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = database_module.DB_PATH
        database_module.DB_PATH = str(
            Path(self.temp_dir.name) / "test.db"
        )

        database_module.initialize_database()
        self.connection = database_module.get_connection()

        self.year_id = self.connection.execute("""
            INSERT INTO academic_years (
                name, start_date, end_date
            )
            VALUES ('2026-2027', '2026-09-01', '2027-06-30')
        """).lastrowid

        self.class_id = self.connection.execute("""
            INSERT INTO classes (name)
            VALUES ('Class A')
        """).lastrowid

        self.section_id = self.connection.execute("""
            INSERT INTO sections (class_id, name)
            VALUES (?, 'Section 1')
        """, (self.class_id,)).lastrowid

        self.student_id = self.connection.execute("""
            INSERT INTO students (
                admission_no, first_name, last_name
            )
            VALUES ('ST001', 'Test', 'Student')
        """).lastrowid

        self.teacher_id = self.connection.execute("""
            INSERT INTO teachers (
                employee_no, first_name, last_name
            )
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
            self.student_id,
            self.section_id,
            self.year_id,
        )).lastrowid

        self.assignment_id = self.connection.execute("""
            INSERT INTO teacher_subject_assignments (
                teacher_id, subject_id, section_id,
                academic_year_id, assigned_on
            )
            VALUES (?, ?, ?, ?, '2026-09-20')
        """, (
            self.teacher_id,
            self.subject_id,
            self.section_id,
            self.year_id,
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

        self.connection.execute("""
            UPDATE assessment_periods
            SET status = 'active'
            WHERE id = ?
        """, (self.period_id,))

        self.scheme_id = self.connection.execute("""
            INSERT INTO grading_schemes (
                class_id, academic_year_id,
                name, version_no
            )
            VALUES (?, ?, 'Standard Scheme', 1)
        """, (self.class_id, self.year_id)).lastrowid

        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label,
                min_percentage, grade_point, remark
            )
            VALUES (?, 'F', 0, 0, 'Needs improvement')
        """, (self.scheme_id,))

        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label,
                min_percentage, grade_point, remark
            )
            VALUES (?, 'B', 60, 3.0, 'Good')
        """, (self.scheme_id,))

        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label,
                min_percentage, grade_point, remark
            )
            VALUES (?, 'A', 80, 4.0, 'Excellent')
        """, (self.scheme_id,))

        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'active'
            WHERE id = ?
        """, (self.scheme_id,))

        self.connection.commit()

    def tearDown(self):
        self.connection.close()
        database_module.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def add_result(
        self,
        marks,
        maximum=100,
        subject_id=None,
        assignment_id=None,
    ):
        return create_student_subject_result({
            "enrollment_id": self.enrollment_id,
            "assessment_period_id": self.period_id,
            "teacher_subject_assignment_id": (
                assignment_id or self.assignment_id
            ),
            "subject_id": subject_id or self.subject_id,
            "grading_scheme_id": self.scheme_id,
            "marks_obtained": marks,
            "maximum_marks": maximum,
        })

    def test_01_report_card_contains_student_and_academic_details(self):
        self.add_result(85)

        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        self.assertEqual(report["student"]["admission_no"], "ST001")
        self.assertEqual(report["student"]["full_name"], "Test Student")
        self.assertEqual(report["class"]["name"], "Class A")
        self.assertEqual(report["section"]["name"], "Section 1")
        self.assertEqual(report["academic_year"]["name"], "2026-2027")
        self.assertEqual(report["assessment_period"]["name"], "Semester 1")

    def test_02_calculate_subject_percentage_and_grade(self):
        self.add_result(85)

        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        subject = report["subjects"][0]

        self.assertEqual(subject["subject_name"], "Mathematics")
        self.assertEqual(subject["percentage"], 85)
        self.assertEqual(subject["grade_label"], "A")
        self.assertEqual(subject["grade_point"], 4.0)
        self.assertEqual(subject["grade_remark"], "Excellent")

    def test_03_calculate_overall_result(self):
        self.add_result(85)

        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        summary = report["summary"]

        self.assertEqual(summary["subject_count"], 1)
        self.assertEqual(summary["total_marks_obtained"], 85)
        self.assertEqual(summary["total_maximum_marks"], 100)
        self.assertEqual(summary["overall_percentage"], 85)
        self.assertEqual(summary["overall_grade_label"], "A")
        self.assertEqual(summary["overall_grade_point"], 4.0)

    def test_04_overall_percentage_uses_total_marks(self):
        self.add_result(80)

        second_subject = self.connection.execute("""
            INSERT INTO subjects (subject_code, name)
            VALUES ('SCI', 'Science')
        """).lastrowid

        second_assignment = self.connection.execute("""
            INSERT INTO teacher_subject_assignments (
                teacher_id, subject_id, section_id,
                academic_year_id, assigned_on
            )
            VALUES (?, ?, ?, ?, '2026-09-20')
        """, (
            self.teacher_id,
            second_subject,
            self.section_id,
            self.year_id,
        )).lastrowid
        self.connection.commit()

        self.add_result(
            45,
            maximum=100,
            subject_id=second_subject,
            assignment_id=second_assignment,
        )

        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        summary = report["summary"]

        self.assertEqual(summary["subject_count"], 2)
        self.assertEqual(summary["total_marks_obtained"], 125)
        self.assertEqual(summary["total_maximum_marks"], 200)
        self.assertEqual(summary["overall_percentage"], 62.5)
        self.assertEqual(summary["overall_grade_label"], "B")

    def test_05_empty_report_card(self):
        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        self.assertEqual(report["subjects"], [])
        self.assertEqual(report["summary"]["subject_count"], 0)
        self.assertIsNone(report["summary"]["overall_percentage"])
        self.assertIsNone(report["summary"]["overall_grade_label"])

    def test_06_reject_missing_enrollment(self):
        with self.assertRaisesRegex(ValueError, "enrollment"):
            get_student_report_card(9999, self.period_id)

    def test_07_reject_missing_assessment_period(self):
        with self.assertRaisesRegex(ValueError, "Assessment period"):
            get_student_report_card(self.enrollment_id, 9999)

    def test_08_reject_different_academic_years(self):
        second_year = self.connection.execute("""
            INSERT INTO academic_years (
                name, start_date, end_date
            )
            VALUES ('2027-2028', '2027-09-01', '2028-06-30')
        """).lastrowid

        second_period = self.connection.execute("""
            INSERT INTO assessment_periods (
                academic_year_id, name, period_type,
                start_date, end_date
            )
            VALUES (
                ?, 'Second Year', 'midterm',
                '2027-10-01', '2027-10-15'
            )
        """, (second_year,)).lastrowid
        self.connection.commit()

        with self.assertRaisesRegex(ValueError, "different academic years"):
            get_student_report_card(
                self.enrollment_id,
                second_period,
            )

    def test_09_archived_scheme_preserves_historical_grade(self):
        self.add_result(85)

        self.connection.execute("""
            UPDATE grading_schemes
            SET status = 'archived'
            WHERE id = ?
        """, (self.scheme_id,))
        self.connection.commit()

        report = get_student_report_card(
            self.enrollment_id,
            self.period_id,
        )

        self.assertEqual(
            report["subjects"][0]["grade_label"],
            "A",
        )
        self.assertEqual(
            report["grading_scheme"]["status"],
            "archived",
        )

    def test_10_integrity_and_foreign_keys(self):
        self.add_result(85)

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
