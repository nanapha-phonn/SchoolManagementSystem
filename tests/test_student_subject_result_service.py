import tempfile
import unittest
from pathlib import Path

import database.database as database_module

from services.student_subject_result_service import (
    create_student_subject_result,
    get_student_subject_result,
    get_student_subject_results,
    update_student_subject_result,
    delete_student_subject_result,
)


class StudentSubjectResultServiceTests(unittest.TestCase):

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
                student_id, section_id, academic_year_id, enrolled_on
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

        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label, min_percentage
            )
            VALUES (?, 'F', 0)
        """, (self.scheme_id,))

        self.connection.execute("""
            INSERT INTO grade_bands (
                grading_scheme_id, grade_label,
                min_percentage, grade_point
            )
            VALUES (?, 'A', 80, 4.0)
        """, (self.scheme_id,))

        self.connection.execute("""
            UPDATE assessment_periods
            SET status = 'active'
            WHERE id = ?
        """, (self.period_id,))

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

    def sample_result(self, **overrides):
        data = {
            "enrollment_id": self.enrollment_id,
            "assessment_period_id": self.period_id,
            "teacher_subject_assignment_id": self.assignment_id,
            "subject_id": self.subject_id,
            "grading_scheme_id": self.scheme_id,
            "marks_obtained": 85,
            "maximum_marks": 100,
        }
        data.update(overrides)
        return data

    def create_result(self, **overrides):
        return create_student_subject_result(
            self.sample_result(**overrides)
        )

    def test_01_create_and_retrieve_result(self):
        result_id = self.create_result()

        result = get_student_subject_result(result_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["enrollment_id"], self.enrollment_id)
        self.assertEqual(result["assessment_period_id"], self.period_id)
        self.assertEqual(result["student_id"], self.student_id)
        self.assertEqual(result["admission_no"], "ST001")
        self.assertEqual(result["student_first_name"], "Test")
        self.assertEqual(result["subject_code"], "MATH")
        self.assertEqual(result["subject_name"], "Mathematics")
        self.assertEqual(result["teacher_name"], "Test Teacher")
        self.assertEqual(result["class_name"], "Class A")
        self.assertEqual(result["section_name"], "Section 1")
        self.assertEqual(result["academic_year_name"], "2026-2027")
        self.assertEqual(result["grading_scheme_version"], 1)
        self.assertEqual(result["marks_obtained"], 85)
        self.assertEqual(result["maximum_marks"], 100)

    def test_02_retrieve_missing_result(self):
        self.assertIsNone(get_student_subject_result(9999))

    def test_03_list_and_filter_results(self):
        self.create_result()

        second_student = self.connection.execute("""
            INSERT INTO students
                (admission_no, first_name, last_name)
            VALUES ('ST002', 'Second', 'Student')
        """).lastrowid

        second_enrollment = self.connection.execute("""
            INSERT INTO enrollments (
                student_id, section_id, academic_year_id, enrolled_on
            )
            VALUES (?, ?, ?, '2026-09-15')
        """, (
            second_student, self.section_id, self.year_id
        )).lastrowid
        self.connection.commit()

        create_student_subject_result(self.sample_result(
            enrollment_id=second_enrollment,
            marks_obtained=70,
        ))

        self.assertEqual(len(get_student_subject_results()), 2)
        self.assertEqual(
            len(get_student_subject_results(
                enrollment_id=self.enrollment_id
            )),
            1,
        )
        self.assertEqual(
            len(get_student_subject_results(
                assessment_period_id=self.period_id
            )),
            2,
        )
        self.assertEqual(
            len(get_student_subject_results(
                section_id=self.section_id
            )),
            2,
        )
        self.assertEqual(
            len(get_student_subject_results(
                academic_year_id=self.year_id
            )),
            2,
        )
        self.assertEqual(
            len(get_student_subject_results(
                subject_id=self.subject_id
            )),
            2,
        )
        self.assertEqual(
            len(get_student_subject_results(
                teacher_subject_assignment_id=self.assignment_id
            )),
            2,
        )
        self.assertEqual(
            len(get_student_subject_results(
                grading_scheme_id=self.scheme_id
            )),
            2,
        )

    def test_04_search_results(self):
        self.create_result()

        self.assertEqual(
            len(get_student_subject_results(search="ST001")),
            1,
        )
        self.assertEqual(
            len(get_student_subject_results(search="Mathematics")),
            1,
        )
        self.assertEqual(
            len(get_student_subject_results(search="Test")),
            1,
        )
        self.assertEqual(
            get_student_subject_results(search="no match"),
            [],
        )

    def test_05_update_marks(self):
        result_id = self.create_result()

        updated = update_student_subject_result(
            result_id,
            {
                "marks_obtained": 90,
                "maximum_marks": 120,
            },
        )

        self.assertEqual(updated["marks_obtained"], 90)
        self.assertEqual(updated["maximum_marks"], 120)

    def test_06_reject_invalid_update_without_changing_result(self):
        result_id = self.create_result()

        with self.assertRaises(ValueError):
            update_student_subject_result(
                result_id,
                {"marks_obtained": 110},
            )

        result = get_student_subject_result(result_id)
        self.assertEqual(result["marks_obtained"], 85)

    def test_07_reject_unsupported_update_fields(self):
        result_id = self.create_result()

        with self.assertRaisesRegex(ValueError, "Unsupported"):
            update_student_subject_result(
                result_id,
                {"subject_id": 999},
            )

    def test_08_reject_empty_update(self):
        result_id = self.create_result()

        with self.assertRaisesRegex(ValueError, "required"):
            update_student_subject_result(result_id, {})

    def test_09_reject_update_for_missing_result(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            update_student_subject_result(
                9999,
                {"marks_obtained": 90},
            )

    def test_10_delete_result_during_active_period(self):
        result_id = self.create_result()

        self.assertTrue(delete_student_subject_result(result_id))
        self.assertIsNone(get_student_subject_result(result_id))
        self.assertEqual(len(get_student_subject_results()), 0)

    def test_11_reject_delete_for_missing_result(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            delete_student_subject_result(9999)

    def test_12_duplicate_result_is_rejected(self):
        self.create_result()

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.create_result()

    def test_13_reject_invalid_reference(self):
        with self.assertRaisesRegex(ValueError, "do not match"):
            self.create_result(subject_id=9999)

    def test_14_completed_period_locks_update_and_delete(self):
        result_id = self.create_result()

        self.connection.execute("""
            UPDATE assessment_periods
            SET status = 'completed'
            WHERE id = ?
        """, (self.period_id,))
        self.connection.commit()

        with self.assertRaisesRegex(ValueError, "only be changed"):
            update_student_subject_result(
                result_id,
                {"marks_obtained": 90},
            )

        with self.assertRaisesRegex(ValueError, "cannot be deleted"):
            delete_student_subject_result(result_id)

        self.assertIsNotNone(get_student_subject_result(result_id))

    def test_15_reject_invalid_search_and_filters(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            get_student_subject_results(enrollment_id=0)

        with self.assertRaisesRegex(ValueError, "Search text"):
            get_student_subject_results(search=123)

        with self.assertRaisesRegex(ValueError, "150 characters"):
            get_student_subject_results(search="x" * 151)


if __name__ == "__main__":
    unittest.main()
