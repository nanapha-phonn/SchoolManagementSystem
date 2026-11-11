import tkinter as tk
import unittest
from tkinter import TclError, ttk
from unittest.mock import Mock, patch

from ui.student_results.student_result_list import StudentResultListFrame


class StudentResultListUITests(unittest.TestCase):

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
        self.user = {
            "id": 1,
            "full_name": "Test Administrator",
            "role": "admin",
        }
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.active_period = {
            "id": 1,
            "name": "Semester 1",
            "academic_year_name": "2026-2027",
            "status": "active",
        }

        self.completed_period = {
            "id": 2,
            "name": "Semester 2",
            "academic_year_name": "2026-2027",
            "status": "completed",
        }

        self.result = {
            "id": 101,
            "enrollment_id": 10,
            "assessment_period_id": 1,
            "admission_no": "ST001",
            "student_first_name": "Test",
            "student_last_name": "Student",
            "class_name": "Class A",
            "section_name": "Section 1",
            "subject_code": "MATH",
            "subject_name": "Mathematics",
            "assessment_period_name": "Semester 1",
            "assessment_period_status": "active",
            "marks_obtained": 85.0,
            "maximum_marks": 100.0,
            "teacher_name": "Test Teacher",
        }

        self.on_create = Mock()
        self.on_edit = Mock()
        self.on_report = Mock()

        self.period_patcher = patch(
            "ui.student_results.student_result_list.get_assessment_periods",
            return_value=[
                self.active_period,
                self.completed_period,
            ],
        )
        self.results_patcher = patch(
            "ui.student_results.student_result_list.get_student_subject_results",
            return_value=[self.result],
        )

        self.get_periods = self.period_patcher.start()
        self.results_patcher.start()

        self.addCleanup(self.period_patcher.stop)
        self.addCleanup(self.results_patcher.stop)

        self.form = StudentResultListFrame(
            self.frame,
            on_create=self.on_create,
            on_edit=self.on_edit,
            on_view_report_card=self.on_report,
            user=self.user,
        )
        self.form.pack(fill="both", expand=True)

        self.root.update_idletasks()

    def tearDown(self):
        self.frame.destroy()
        self.root.update_idletasks()

    def select_result(self):
        self.form.tree.selection_set("101")
        self.form.apply_selection_controls()

    def test_01_display_student_results(self):
        self.assertEqual(len(self.form.tree.get_children()), 1)

        values = self.form.tree.item("101", "values")

        self.assertEqual(values[1], "ST001")
        self.assertEqual(values[2], "Test Student")
        self.assertEqual(values[4], "MATH - Mathematics")
        self.assertEqual(values[6], "85 / 100")
        self.assertEqual(values[7], "85.00%")
        self.assertEqual(values[9], "Active")

    def test_02_load_assessment_period_filters(self):
        self.get_periods.assert_called_once_with(
            actor_user_id=self.user["id"],
        )
        self.assertEqual(len(self.form.periods), 3)
        self.assertEqual(self.form.period_combo["values"][0], "All")

        labels = list(self.form.periods)
        self.assertEqual(self.form.periods[labels[1]], 1)
        self.assertEqual(self.form.periods[labels[2]], 2)

    def test_03_filter_results_by_period_and_search(self):
        labels = list(self.form.periods)

        self.form.period_var.set(labels[2])
        self.form.search_var.set("ST001")
        self.form.load_results()

        self.assertEqual(
            self.results_patcher.is_local if False else
            self.form.tree.get_children(),
            ("101",),
        )

        from ui.student_results import student_result_list

        student_result_list.get_student_subject_results.assert_called_with(
            assessment_period_id=2,
            search="ST001",
        )

    def test_04_reset_filters(self):
        self.form.search_var.set("MATH")
        self.form.period_var.set(list(self.form.periods)[2])

        self.form.reset_filters()

        self.assertEqual(self.form.search_var.get(), "")
        self.assertEqual(self.form.period_var.get(), "All")

    def test_05_create_button_calls_callback(self):
        self.form.create_result()
        self.on_create.assert_called_once()

    def test_06_edit_active_result_calls_callback(self):
        self.select_result()

        self.assertEqual(str(self.form.edit_button["state"]), "normal")

        self.form.edit_selected()

        self.on_edit.assert_called_once_with(self.result)

    def test_07_completed_result_disables_edit_and_delete(self):
        completed = dict(self.result)
        completed["assessment_period_status"] = "completed"

        with patch(
            "ui.student_results.student_result_list.get_student_subject_results",
            return_value=[completed],
        ):
            self.form.load_results()

        self.form.tree.selection_set("101")
        self.form.apply_selection_controls()

        self.assertEqual(str(self.form.edit_button["state"]), "disabled")
        self.assertEqual(str(self.form.delete_button["state"]), "disabled")
        self.assertEqual(str(self.form.report_button["state"]), "normal")

    def test_08_delete_confirmation_cancelled(self):
        self.select_result()

        with patch(
            "ui.student_results.student_result_list.messagebox.askyesno",
            return_value=False,
        ), patch(
            "ui.student_results.student_result_list.delete_student_subject_result",
        ) as mock_delete:
            self.form.delete_selected()

        mock_delete.assert_not_called()

    def test_09_delete_confirmed(self):
        self.select_result()

        with patch(
            "ui.student_results.student_result_list.messagebox.askyesno",
            return_value=True,
        ), patch(
            "ui.student_results.student_result_list.messagebox.showinfo",
        ), patch(
            "ui.student_results.student_result_list.delete_student_subject_result",
        ) as mock_delete:
            self.form.delete_selected()

        mock_delete.assert_called_once_with(101)

    def test_10_report_card_callback(self):
        self.select_result()

        self.form.view_report_card()

        self.on_report.assert_called_once_with(10, 1)

    def test_11_report_card_available_for_completed_result(self):
        completed = dict(self.result)
        completed["assessment_period_status"] = "completed"

        with patch(
            "ui.student_results.student_result_list.get_student_subject_results",
            return_value=[completed],
        ):
            self.form.load_results()

        self.form.tree.selection_set("101")
        self.form.apply_selection_controls()
        self.form.view_report_card()

        self.on_report.assert_called_once_with(10, 1)

    def test_12_warn_when_no_result_is_selected(self):
        with patch(
            "ui.student_results.student_result_list.messagebox.showwarning",
        ) as warning:
            result = self.form.get_selected_result()

        self.assertIsNone(result)
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
