import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.dashboard import DashboardWindow


SAMPLE_RESULT = {
    "id": 101,
    "enrollment_id": 10,
    "assessment_period_id": 20,
}


class StudentResultDashboardTests(unittest.TestCase):

    def setUp(self):
        self.dashboard = SimpleNamespace(
            content=object(),
            clear_content=Mock(),
            show_student_results=Mock(),
            show_student_result_form=Mock(),
            show_student_report_card=Mock(),
            user={
                "id": 1,
                "full_name": "Test User",
                "role": "admin",
            },
        )

    @patch("ui.dashboard.StudentResultListFrame")
    def test_01_show_student_result_list(self, mock_list_class):
        page = mock_list_class.return_value

        DashboardWindow.show_student_results(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_list_class.assert_called_once_with(
            self.dashboard.content,
            on_create=self.dashboard.show_student_result_form,
            on_edit=self.dashboard.show_student_result_form,
            on_view_report_card=self.dashboard.show_student_report_card,
            user=self.dashboard.user,
        )

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.StudentResultForm")
    def test_02_show_create_result_form(self, mock_form_class):
        form = mock_form_class.return_value

        DashboardWindow.show_student_result_form(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_student_results,
            on_saved=self.dashboard.show_student_results,
            result=None,
            user=self.dashboard.user,
        )

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.StudentResultForm")
    @patch(
        "ui.dashboard.get_student_subject_result",
        return_value=SAMPLE_RESULT,
    )
    def test_03_show_edit_result_form(
        self,
        mock_get_result,
        mock_form_class,
    ):
        form = mock_form_class.return_value

        DashboardWindow.show_student_result_form(
            self.dashboard,
            SAMPLE_RESULT,
        )

        mock_get_result.assert_called_once_with(101)

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_student_results,
            on_saved=self.dashboard.show_student_results,
            result=SAMPLE_RESULT,
            user=self.dashboard.user,
        )

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.StudentResultForm")
    @patch(
        "ui.dashboard.get_student_subject_result",
        return_value=None,
    )
    def test_04_handle_missing_result(
        self,
        mock_get_result,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_student_result_form(
            self.dashboard,
            SAMPLE_RESULT,
        )

        mock_get_result.assert_called_once_with(101)
        mock_error.assert_called_once()
        self.dashboard.show_student_results.assert_called_once_with()
        mock_form_class.assert_not_called()

    @patch("ui.dashboard.StudentReportCardFrame")
    def test_05_show_student_report_card(self, mock_report_class):
        page = mock_report_class.return_value

        DashboardWindow.show_student_report_card(
            self.dashboard,
            10,
            20,
        )

        self.dashboard.clear_content.assert_called_once_with()

        mock_report_class.assert_called_once_with(
            self.dashboard.content,
            enrollment_id=10,
            assessment_period_id=20,
            on_back=self.dashboard.show_student_results,
        )

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch(
        "ui.dashboard.StudentReportCardFrame",
        side_effect=ValueError("Enrollment was not found."),
    )
    def test_06_handle_report_card_error(
        self,
        mock_report_class,
        mock_error,
    ):
        DashboardWindow.show_student_report_card(
            self.dashboard,
            999,
            20,
        )

        mock_error.assert_called_once()
        self.dashboard.show_student_results.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
