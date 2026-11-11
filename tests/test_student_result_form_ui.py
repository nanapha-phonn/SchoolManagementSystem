import tkinter as tk
import unittest
from tkinter import TclError, ttk
from unittest.mock import Mock, patch

from ui.student_results.student_result_form import StudentResultForm


class StudentResultFormUITests(unittest.TestCase):
    TEST_USER = {"id": 1, "role": "admin"}


    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except TclError as error:
            raise unittest.SkipTest(str(error))

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.period = {
            "id": 1,
            "academic_year_id": 1,
            "name": "Semester 1",
            "academic_year_name": "2026-2027",
            "start_date": "2026-10-01",
            "end_date": "2026-10-15",
            "status": "active",
        }

        self.saved_callback = Mock()

        self.period_patcher = patch(
            "ui.student_results.student_result_form.get_assessment_periods",
            return_value=[self.period],
        )
        self.period_patcher.start()
        self.addCleanup(self.period_patcher.stop)

        self.form = StudentResultForm(
            self.frame,
            user=self.TEST_USER,
            on_back=Mock(),
            on_saved=self.saved_callback,
        )
        self.form.pack(fill="both", expand=True)

        self.root.update_idletasks()

    def tearDown(self):
        self.frame.destroy()
        self.root.update_idletasks()

    def sample_assignment(self, **overrides):
        data = {
            "id": 10,
            "subject_id": 20,
            "section_id": 30,
            "academic_year_id": 1,
            "subject_code": "MATH",
            "subject_name": "Mathematics",
            "teacher_name": "Test Teacher",
            "section_name": "Section A",
            "assigned_on": "2026-09-20",
            "ended_on": None,
        }
        data.update(overrides)
        return data

    def sample_enrollment(self):
        return {
            "id": 40,
            "student_id": 50,
            "admission_no": "ST001",
            "student_name": "Test Student",
            "class_id": 60,
            "section_id": 30,
            "academic_year_id": 1,
        }

    def sample_scheme(self):
        return {
            "id": 70,
            "class_id": 60,
            "academic_year_id": 1,
            "name": "Standard Scheme",
            "version_no": 1,
            "status": "active",
        }

    def prepare_selection(self):
        period_label = next(iter(self.form.periods))
        assignment = self.sample_assignment()
        assignment_label = (
            f"{assignment['subject_code']} - "
            f"{assignment['subject_name']} | "
            f"{assignment['teacher_name']} | "
            f"{assignment['section_name']} "
            f"[ID:{assignment['id']}]"
        )
        enrollment = self.sample_enrollment()
        enrollment_label = (
            f"{enrollment['admission_no']} - "
            f"{enrollment['student_name']} "
            f"[ID:{enrollment['id']}]"
        )

        self.form.period_var.set(period_label)
        self.form.periods[period_label] = self.period

        self.form.assignment_var.set(assignment_label)
        self.form.assignments[assignment_label] = assignment

        self.form.enrollment_var.set(enrollment_label)
        self.form.enrollments[enrollment_label] = enrollment

        self.form.grading_scheme = self.sample_scheme()

    def test_01_load_active_assessment_periods(self):
        self.assertEqual(len(self.form.periods), 1)
        self.assertEqual(len(self.form.period_combo["values"]), 1)

    def test_02_load_and_filter_teacher_assignments(self):
        assignments = [
            self.sample_assignment(),
            self.sample_assignment(
                id=11,
                assigned_on="2026-10-20",
            ),
            self.sample_assignment(
                id=12,
                assigned_on="2026-08-01",
                ended_on="2026-09-20",
            ),
        ]

        with patch(
            "ui.student_results.student_result_form.get_teacher_subject_assignments",
            return_value=assignments,
        ) as mock_get_assignments:
            self.form.period_var.set(next(iter(self.form.periods)))
            self.form.on_period_selected()

        mock_get_assignments.assert_called_once_with(
            academic_year_id=1,
            actor_user_id=self.TEST_USER["id"],
        )
        self.assertEqual(len(self.form.assignments), 1)
        self.assertIn("MATH", next(iter(self.form.assignments)))

    def test_03_load_students_and_active_grading_scheme(self):
        assignment = self.sample_assignment()

        with patch(
            "ui.student_results.student_result_form.get_enrollments",
            return_value=[self.sample_enrollment()],
        ), patch(
            "ui.student_results.student_result_form.get_grading_schemes",
            return_value=[self.sample_scheme()],
        ):
            self.form.period_var.set(next(iter(self.form.periods)))

            assignment_label = (
                "MATH - Mathematics | Test Teacher | Section A [ID:10]"
            )
            self.form.assignment_var.set(assignment_label)
            self.form.assignments[assignment_label] = assignment

            self.form.on_assignment_selected()

        self.assertEqual(len(self.form.enrollments), 1)
        self.assertEqual(self.form.grading_scheme["id"], 70)
        self.assertIn("Standard Scheme", self.form.reference_label.cget("text"))

    def test_04_disable_save_without_active_periods(self):
        with patch(
            "ui.student_results.student_result_form.get_assessment_periods",
            return_value=[],
        ):
            empty_form = StudentResultForm(self.frame, user=self.TEST_USER)
            empty_form.pack(fill="both", expand=True)
            self.root.update_idletasks()

            self.assertEqual(len(empty_form.periods), 0)
            self.assertEqual(
                str(empty_form.save_button["state"]),
                "disabled",
            )

            empty_form.destroy()

    def test_05_create_student_result(self):
        self.prepare_selection()

        with patch(
            "ui.student_results.student_result_form.create_student_subject_result",
            return_value=100,
        ) as mock_create, patch(
            "ui.student_results.student_result_form.messagebox.showinfo",
        ):
            self.form.marks_var.set("85")
            self.form.maximum_var.set("100")
            self.form.save()

        mock_create.assert_called_once_with({
            "enrollment_id": 40,
            "assessment_period_id": 1,
            "teacher_subject_assignment_id": 10,
            "subject_id": 20,
            "grading_scheme_id": 70,
            "marks_obtained": 85.0,
            "maximum_marks": 100.0,
        })
        self.saved_callback.assert_called_once()

    def test_06_reject_missing_selection(self):
        with patch(
            "ui.student_results.student_result_form.messagebox.showwarning",
        ) as warning:
            self.form.marks_var.set("85")
            self.form.save()

        warning.assert_called_once()
        self.saved_callback.assert_not_called()

    def test_07_edit_existing_result(self):
        result = {
            "id": 100,
            "admission_no": "ST001",
            "student_first_name": "Test",
            "student_last_name": "Student",
            "subject_name": "Mathematics",
            "assessment_period_name": "Semester 1",
            "teacher_name": "Test Teacher",
            "grading_scheme_name": "Standard Scheme",
            "grading_scheme_version": 1,
            "assessment_period_status": "active",
            "marks_obtained": 75,
            "maximum_marks": 100,
        }

        edit_form = StudentResultForm(
            self.frame,
            user=self.TEST_USER,
            result=result,
            on_saved=self.saved_callback,
        )
        edit_form.pack(fill="both", expand=True)

        with patch(
            "ui.student_results.student_result_form.update_student_subject_result",
            return_value=result,
        ) as mock_update, patch(
            "ui.student_results.student_result_form.messagebox.showinfo",
        ):
            edit_form.marks_var.set("90")
            edit_form.save()

        mock_update.assert_called_once_with(
            100,
            {
                "marks_obtained": 90.0,
                "maximum_marks": 100.0,
            },
        )
        self.saved_callback.assert_called_once()
        edit_form.destroy()

    def test_08_completed_assessment_disables_save(self):
        result = {
            "id": 100,
            "admission_no": "ST001",
            "student_first_name": "Test",
            "student_last_name": "Student",
            "subject_name": "Mathematics",
            "assessment_period_name": "Semester 1",
            "teacher_name": "Test Teacher",
            "grading_scheme_name": "Standard Scheme",
            "grading_scheme_version": 1,
            "assessment_period_status": "completed",
            "marks_obtained": 75,
            "maximum_marks": 100,
        }

        locked_form = StudentResultForm(
            self.frame,
            user=self.TEST_USER,
            result=result,
        )
        locked_form.pack(fill="both", expand=True)

        self.assertEqual(
            str(locked_form.save_button["state"]),
            "disabled",
        )
        locked_form.destroy()


if __name__ == "__main__":
    unittest.main()
