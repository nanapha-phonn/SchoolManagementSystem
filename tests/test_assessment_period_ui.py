import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.assessment_periods.assessment_period_form import (
    AssessmentPeriodForm,
)


SAMPLE_ACADEMIC_YEARS = [
    {
        "id": 101,
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": 1,
    }
]

SAMPLE_PERIOD = {
    "id": 501,
    "academic_year_id": 101,
    "academic_year_name": "2026-2027",
    "name": "Semester 1 Midterm",
    "period_type": "midterm",
    "start_date": "2026-10-01",
    "end_date": "2026-10-15",
    "status": "active",
}


class AssessmentPeriodFormUITests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError as error:
            raise unittest.SkipTest(
                f"Tkinter display unavailable: {error}"
            )

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.user = {"id": 1, "full_name": "Test Administrator", "role": "admin"}

    def tearDown(self):
        self.frame.destroy()
        self.root.update_idletasks()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showinfo"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.create_assessment_period",
        return_value=501,
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_01_create_assessment_period(
        self,
        mock_years,
        mock_create,
        mock_message,
    ):
        on_saved = Mock()

        form = AssessmentPeriodForm(
            self.frame,
            on_saved=on_saved,
         user=self.user)
        form.pack(fill="both", expand=True)

        form.academic_year_var.set(
            form.academic_year_label_by_id[101]
        )
        form.name_var.set("Semester 1 Midterm")
        form.period_type_var.set("Midterm")
        form.start_date_var.set("2026-10-01")
        form.end_date_var.set("2026-10-15")

        form.save_assessment_period()

        mock_create.assert_called_once_with({
            "academic_year_id": 101,
            "name": "Semester 1 Midterm",
            "period_type": "midterm",
            "start_date": "2026-10-01",
            "end_date": "2026-10-15",
            "status": "planned",
        }, actor_user_id=self.user["id"])

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showinfo"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.update_assessment_period"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_02_edit_active_assessment_period(
        self,
        mock_years,
        mock_update,
        mock_message,
    ):
        on_saved = Mock()

        form = AssessmentPeriodForm(
            self.frame,
            on_saved=on_saved,
            assessment_period=SAMPLE_PERIOD,
         user=self.user)
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.name_var.get(),
            "Semester 1 Midterm",
        )
        self.assertEqual(
            form.period_type_var.get(),
            "Midterm",
        )
        self.assertEqual(
            form.start_date_var.get(),
            "2026-10-01",
        )
        self.assertEqual(
            form.end_date_var.get(),
            "2026-10-15",
        )

        self.assertTrue(
            form.academic_year_combo.instate(["disabled"])
        )

        form.name_var.set("Updated Semester 1 Midterm")
        form.save_assessment_period()

        mock_update.assert_called_once_with(
            501,
            {
                "academic_year_id": 101,
                "name": "Updated Semester 1 Midterm",
                "period_type": "midterm",
                "start_date": "2026-10-01",
                "end_date": "2026-10-15",
                "status": "active",
            },
            actor_user_id=self.user["id"],
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.create_assessment_period"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_03_reject_missing_academic_year(
        self,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.name_var.set("Semester 1 Midterm")
        form.start_date_var.set("2026-10-01")
        form.end_date_var.set("2026-10-15")

        form.save_assessment_period()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.create_assessment_period"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_04_reject_invalid_period_type(
        self,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.academic_year_var.set(
            form.academic_year_label_by_id[101]
        )
        form.period_type_var.set("Invalid Type")

        form.save_assessment_period()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.create_assessment_period",
        side_effect=ValueError(
            "Assessment periods cannot overlap within an academic year."
        ),
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_05_display_service_validation_error(
        self,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.academic_year_var.set(
            form.academic_year_label_by_id[101]
        )
        form.name_var.set("Semester 1 Midterm")
        form.start_date_var.set("2026-10-01")
        form.end_date_var.set("2026-10-15")

        form.save_assessment_period()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_06_clear_form(self, mock_years):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.academic_year_var.set(
            form.academic_year_label_by_id[101]
        )
        form.name_var.set("Semester 1 Midterm")
        form.period_type_var.set("Final")
        form.start_date_var.set("2026-10-01")
        form.end_date_var.set("2026-10-15")

        form.clear_form()

        self.assertEqual(form.academic_year_var.get(), "")
        self.assertEqual(form.name_var.get(), "")
        self.assertEqual(form.period_type_var.get(), "Midterm")
        self.assertEqual(form.start_date_var.get(), "")
        self.assertEqual(form.end_date_var.get(), "")

    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_07_form_back_callback(self, mock_years):
        on_back = Mock()

        form = AssessmentPeriodForm(
            self.frame,
            on_back=on_back,
         user=self.user)
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.update_assessment_period"
    )
    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_08_completed_period_is_locked(
        self,
        mock_years,
        mock_update,
        mock_warning,
    ):
        completed_period = {
            **SAMPLE_PERIOD,
            "status": "completed",
        }

        form = AssessmentPeriodForm(
            self.frame,
            assessment_period=completed_period,
         user=self.user)
        form.pack(fill="both", expand=True)

        self.assertTrue(
            form.name_entry.instate(["disabled"])
        )
        self.assertTrue(
            form.period_type_combo.instate(["disabled"])
        )
        self.assertTrue(
            form.start_date_entry.instate(["disabled"])
        )
        self.assertTrue(
            form.end_date_entry.instate(["disabled"])
        )
        self.assertTrue(
            form.save_button.instate(["disabled"])
        )
        self.assertTrue(
            form.clear_button.instate(["disabled"])
        )

        form.save_assessment_period()

        mock_update.assert_not_called()
        mock_warning.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        return_value=[],
    )
    def test_09_disable_save_without_academic_years(self, mock_years):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        self.assertTrue(
            form.save_button.instate(["disabled"])
        )
        self.assertIn(
            "No academic years",
            form.year_warning_label.cget("text"),
        )

    @patch(
        "ui.assessment_periods.assessment_period_form.get_academic_years",
        side_effect=RuntimeError("Database unavailable"),
    )
    def test_10_handle_academic_year_loading_error(self, mock_years):
        form = AssessmentPeriodForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        self.assertTrue(
            form.save_button.instate(["disabled"])
        )
        self.assertIn(
            "Database unavailable",
            form.year_warning_label.cget("text"),
        )


if __name__ == "__main__":
    unittest.main()
