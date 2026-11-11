import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.dashboard import DashboardWindow


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


class AssessmentPeriodDashboardTests(unittest.TestCase):

    def setUp(self):
        self.dashboard = SimpleNamespace(
            content=object(),
            user={"id": 1, "full_name": "Test Administrator", "role": "admin"},
            clear_content=Mock(),
            show_assessment_period_form=Mock(),
            show_assessment_periods=Mock(),
        )

    @patch("ui.dashboard.AssessmentPeriodListFrame")
    def test_01_show_assessment_period_list(self, mock_list_class):
        page = mock_list_class.return_value

        DashboardWindow.show_assessment_periods(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_list_class.assert_called_once_with(
            self.dashboard.content,
            on_create=self.dashboard.show_assessment_period_form,
            on_edit=self.dashboard.show_assessment_period_form,
         user=self.dashboard.user)

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.AssessmentPeriodForm")
    def test_02_show_create_form(self, mock_form_class):
        form = mock_form_class.return_value

        DashboardWindow.show_assessment_period_form(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_assessment_periods,
            on_saved=self.dashboard.show_assessment_periods,
            assessment_period=None,
         user=self.dashboard.user)

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.AssessmentPeriodForm")
    @patch(
        "ui.dashboard.get_assessment_period",
        return_value=SAMPLE_PERIOD,
    )
    def test_03_show_edit_form(
        self,
        mock_get_period,
        mock_form_class,
    ):
        form = mock_form_class.return_value

        DashboardWindow.show_assessment_period_form(
            self.dashboard,
            501,
        )

        mock_get_period.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_assessment_periods,
            on_saved=self.dashboard.show_assessment_periods,
            assessment_period=SAMPLE_PERIOD,
         user=self.dashboard.user)

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.AssessmentPeriodForm")
    @patch(
        "ui.dashboard.get_assessment_period",
        return_value=None,
    )
    def test_04_handle_missing_assessment_period(
        self,
        mock_get_period,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_assessment_period_form(
            self.dashboard,
            999,
        )

        mock_get_period.assert_called_once_with(999, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_assessment_periods.assert_called_once_with()
        mock_form_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
