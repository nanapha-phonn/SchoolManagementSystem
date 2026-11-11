import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.assessment_periods.assessment_period_list import (
    AssessmentPeriodListFrame,
)


SAMPLE_ACADEMIC_YEARS = [
    {
        "id": 101,
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": 1,
    },
    {
        "id": 102,
        "name": "2027-2028",
        "start_date": "2027-09-01",
        "end_date": "2028-06-30",
        "is_current": 0,
    },
]

SAMPLE_PERIOD = {
    "id": 501,
    "academic_year_id": 101,
    "academic_year_name": "2026-2027",
    "name": "Semester 1 Midterm",
    "period_type": "midterm",
    "start_date": "2026-10-01",
    "end_date": "2026-10-15",
    "status": "planned",
}


class AssessmentPeriodListUITests(unittest.TestCase):

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
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[SAMPLE_PERIOD],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_01_display_assessment_period(
        self,
        mock_years,
        mock_periods,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        rows = list_frame.tree.get_children()
        self.assertEqual(len(rows), 1)

        values = list_frame.tree.item(rows[0], "values")

        self.assertEqual(values[0], "501")
        self.assertEqual(values[1], "Semester 1 Midterm")
        self.assertEqual(values[2], "Midterm")
        self.assertEqual(values[3], "2026-2027")
        self.assertEqual(values[4], "2026-10-01")
        self.assertEqual(values[5], "2026-10-15")
        self.assertEqual(values[6], "Planned")

        mock_years.assert_called_once_with(actor_user_id=self.user["id"])
        mock_periods.assert_called_once_with(
            academic_year_id=None,
            status=None,
            search="",
            actor_user_id=self.user["id"],
        )

    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_02_filter_by_year_status_and_search(
        self,
        mock_years,
        mock_periods,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        year_label = next(
            label
            for label, year_id
            in list_frame.academic_year_id_by_label.items()
            if year_id == 101
        )

        list_frame.academic_year_var.set(year_label)
        list_frame.status_var.set("Active")
        list_frame.search_var.set("Midterm")

        list_frame.load_assessment_periods()

        mock_periods.assert_called_with(
            academic_year_id=101,
            status="active",
            search="Midterm",
            actor_user_id=self.user["id"],
        )

    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_03_reset_filters(
        self,
        mock_years,
        mock_periods,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        year_label = next(
            label
            for label, year_id
            in list_frame.academic_year_id_by_label.items()
            if year_id == 101
        )

        list_frame.academic_year_var.set(year_label)
        list_frame.status_var.set("Completed")
        list_frame.search_var.set("Final")

        list_frame.reset_filters()

        self.assertEqual(list_frame.academic_year_var.get(), "All")
        self.assertEqual(list_frame.status_var.get(), "All")
        self.assertEqual(list_frame.search_var.get(), "")

        mock_periods.assert_called_with(
            academic_year_id=None,
            status=None,
            search="",
            actor_user_id=self.user["id"],
        )

    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[SAMPLE_PERIOD],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_04_edit_selected_period(
        self,
        mock_years,
        mock_periods,
    ):
        on_edit = Mock()

        list_frame = AssessmentPeriodListFrame(
            self.frame,
            on_edit=on_edit,
         user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.edit_selected()

        on_edit.assert_called_once_with(501)

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_05_reject_action_without_selection(
        self,
        mock_years,
        mock_periods,
        mock_warning,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        result = list_frame.get_selected_assessment_period()

        self.assertIsNone(result)
        mock_warning.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.showinfo"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.update_assessment_period_status"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[SAMPLE_PERIOD],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_06_activate_planned_period(
        self,
        mock_years,
        mock_periods,
        mock_update,
        mock_confirm,
        mock_message,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("active")

        mock_confirm.assert_called_once()
        mock_update.assert_called_once_with(501, "active", actor_user_id=self.user["id"])
        mock_message.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.showinfo"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.update_assessment_period_status"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[
            {**SAMPLE_PERIOD, "status": "active"}
        ],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_07_complete_active_period(
        self,
        mock_years,
        mock_periods,
        mock_update,
        mock_confirm,
        mock_message,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("completed")

        mock_confirm.assert_called_once()
        mock_update.assert_called_once_with(501, "completed", actor_user_id=self.user["id"])
        mock_message.assert_called_once()

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.askyesno"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.update_assessment_period_status"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[SAMPLE_PERIOD],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_08_reject_planned_to_completed(
        self,
        mock_years,
        mock_periods,
        mock_update,
        mock_confirm,
        mock_warning,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("completed")

        mock_warning.assert_called_once()
        mock_confirm.assert_not_called()
        mock_update.assert_not_called()

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.askyesno",
        return_value=False,
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.update_assessment_period_status"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[SAMPLE_PERIOD],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_09_cancel_status_transition(
        self,
        mock_years,
        mock_periods,
        mock_update,
        mock_confirm,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("active")

        mock_confirm.assert_called_once()
        mock_update.assert_not_called()

    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_10_refresh_reloads_reference_and_period_data(
        self,
        mock_years,
        mock_periods,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        list_frame.refresh()

        self.assertEqual(mock_years.call_count, 2)
        self.assertEqual(mock_periods.call_count, 2)

    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.showwarning"
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.update_assessment_period_status",
        side_effect=ValueError(
            "Invalid status transition: completed to active."
        ),
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_assessment_periods",
        return_value=[
            {**SAMPLE_PERIOD, "status": "active"}
        ],
    )
    @patch(
        "ui.assessment_periods.assessment_period_list.get_academic_years",
        return_value=SAMPLE_ACADEMIC_YEARS,
    )
    def test_11_display_status_validation_error(
        self,
        mock_years,
        mock_periods,
        mock_confirm,
        mock_update,
        mock_warning,
    ):
        list_frame = AssessmentPeriodListFrame(self.frame, user=self.user)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("completed")

        mock_update.assert_called_once_with(501, "completed", actor_user_id=self.user["id"])
        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
