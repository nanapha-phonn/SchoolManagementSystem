import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.dashboard import DashboardWindow


SAMPLE_SCHEME = {
    "id": 501,
    "class_id": 101,
    "class_name": "Grade 10",
    "academic_year_id": 201,
    "academic_year_name": "2026-2027",
    "name": "Standard Grading",
    "version_no": 1,
    "status": "draft",
}

SAMPLE_BAND = {
    "id": 701,
    "grading_scheme_id": 501,
    "grade_label": "A",
    "min_percentage": 90.0,
    "grade_point": 4.0,
    "remark": "Excellent",
}


class GradingSchemeDashboardTests(unittest.TestCase):

    def setUp(self):
        self.dashboard = SimpleNamespace(
            content=object(),
            user={
                "id": 1,
                "full_name": "Test Administrator",
                "role": "admin",
            },
            clear_content=Mock(),
            show_grading_schemes=Mock(),
            show_grading_scheme_form=Mock(),
            show_grade_bands=Mock(),
            show_grade_band_form=Mock(),
        )

    @patch("ui.dashboard.GradingSchemeListFrame")
    def test_01_show_grading_scheme_list(self, mock_list_class):
        page = mock_list_class.return_value

        DashboardWindow.show_grading_schemes(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_list_class.assert_called_once_with(
            self.dashboard.content,
            on_create=self.dashboard.show_grading_scheme_form,
            on_edit=self.dashboard.show_grading_scheme_form,
            on_manage_bands=self.dashboard.show_grade_bands,
            user=self.dashboard.user,
        )

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.GradingSchemeForm")
    def test_02_show_create_grading_scheme_form(self, mock_form_class):
        form = mock_form_class.return_value

        DashboardWindow.show_grading_scheme_form(self.dashboard)

        self.dashboard.clear_content.assert_called_once_with()

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_grading_schemes,
            on_saved=self.dashboard.show_grading_schemes,
            grading_scheme=None,
            user=self.dashboard.user,
        )

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.GradingSchemeForm")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_03_show_edit_grading_scheme_form(
        self,
        mock_get_scheme,
        mock_form_class,
    ):
        form = mock_form_class.return_value

        DashboardWindow.show_grading_scheme_form(
            self.dashboard,
            501,
        )

        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            on_back=self.dashboard.show_grading_schemes,
            on_saved=self.dashboard.show_grading_schemes,
            grading_scheme=SAMPLE_SCHEME,
            user=self.dashboard.user,
        )

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.GradingSchemeForm")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=None,
    )
    def test_04_handle_missing_grading_scheme(
        self,
        mock_get_scheme,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_grading_scheme_form(
            self.dashboard,
            999,
        )

        mock_get_scheme.assert_called_once_with(999, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_grading_schemes.assert_called_once_with()
        mock_form_class.assert_not_called()

    @patch("ui.dashboard.GradeBandListFrame")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_05_show_grade_band_list(
        self,
        mock_get_scheme,
        mock_list_class,
    ):
        page = mock_list_class.return_value

        DashboardWindow.show_grade_bands(
            self.dashboard,
            501,
        )

        self.dashboard.clear_content.assert_called_once_with()
        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])

        mock_list_class.assert_called_once()

        args, kwargs = mock_list_class.call_args

        self.assertIs(args[0], self.dashboard.content)
        self.assertEqual(kwargs["grading_scheme"], SAMPLE_SCHEME)
        self.assertEqual(kwargs["on_back"], self.dashboard.show_grading_schemes)
        self.assertEqual(
            kwargs["on_scheme_changed"],
            self.dashboard.show_grading_schemes,
        )
        self.assertEqual(kwargs["user"], self.dashboard.user)

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

        # Verify the Add and Edit callbacks preserve the scheme ID.
        kwargs["on_add"]()
        self.dashboard.show_grade_band_form.assert_called_once_with(501)

        self.dashboard.show_grade_band_form.reset_mock()

        kwargs["on_edit"](701)
        self.dashboard.show_grade_band_form.assert_called_once_with(
            501,
            701,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.GradeBandListFrame")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=None,
    )
    def test_06_handle_missing_scheme_when_opening_bands(
        self,
        mock_get_scheme,
        mock_list_class,
        mock_error,
    ):
        DashboardWindow.show_grade_bands(
            self.dashboard,
            999,
        )

        mock_get_scheme.assert_called_once_with(999, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_grading_schemes.assert_called_once_with()
        mock_list_class.assert_not_called()

    @patch("ui.dashboard.GradeBandForm")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_07_show_create_grade_band_form(
        self,
        mock_get_scheme,
        mock_form_class,
    ):
        form = mock_form_class.return_value

        DashboardWindow.show_grade_band_form(
            self.dashboard,
            501,
        )

        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            grading_scheme=SAMPLE_SCHEME,
            on_back=unittest.mock.ANY,
            on_saved=unittest.mock.ANY,
            grade_band=None,
            user=self.dashboard.user,
        )

        kwargs = mock_form_class.call_args.kwargs

        kwargs["on_back"]()
        self.dashboard.show_grade_bands.assert_called_once_with(501)

        self.dashboard.show_grade_bands.reset_mock()

        kwargs["on_saved"]()
        self.dashboard.show_grade_bands.assert_called_once_with(501)

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.GradeBandForm")
    @patch(
        "ui.dashboard.get_grade_band",
        return_value=SAMPLE_BAND,
    )
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_08_show_edit_grade_band_form(
        self,
        mock_get_scheme,
        mock_get_band,
        mock_form_class,
    ):
        form = mock_form_class.return_value

        DashboardWindow.show_grade_band_form(
            self.dashboard,
            501,
            701,
        )

        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])
        mock_get_band.assert_called_once_with(701, actor_user_id=self.dashboard.user["id"])

        mock_form_class.assert_called_once_with(
            self.dashboard.content,
            grading_scheme=SAMPLE_SCHEME,
            on_back=unittest.mock.ANY,
            on_saved=unittest.mock.ANY,
            grade_band=SAMPLE_BAND,
            user=self.dashboard.user,
        )

        form.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.GradeBandForm")
    @patch(
        "ui.dashboard.get_grade_band",
        return_value=None,
    )
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_09_handle_missing_grade_band(
        self,
        mock_get_scheme,
        mock_get_band,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_grade_band_form(
            self.dashboard,
            501,
            999,
        )

        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])
        mock_get_band.assert_called_once_with(999, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_grade_bands.assert_called_once_with(501)
        mock_form_class.assert_not_called()

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.GradeBandForm")
    @patch(
        "ui.dashboard.get_grade_band",
        return_value={
            **SAMPLE_BAND,
            "grading_scheme_id": 999,
        },
    )
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=SAMPLE_SCHEME,
    )
    def test_10_reject_grade_band_from_another_scheme(
        self,
        mock_get_scheme,
        mock_get_band,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_grade_band_form(
            self.dashboard,
            501,
            701,
        )

        mock_get_scheme.assert_called_once_with(501, actor_user_id=self.dashboard.user["id"])
        mock_get_band.assert_called_once_with(701, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_grade_bands.assert_called_once_with(501)
        mock_form_class.assert_not_called()

    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.GradeBandForm")
    @patch(
        "ui.dashboard.get_grading_scheme",
        return_value=None,
    )
    def test_11_handle_missing_scheme_when_opening_band_form(
        self,
        mock_get_scheme,
        mock_form_class,
        mock_error,
    ):
        DashboardWindow.show_grade_band_form(
            self.dashboard,
            999,
        )

        mock_get_scheme.assert_called_once_with(999, actor_user_id=self.dashboard.user["id"])
        mock_error.assert_called_once()
        self.dashboard.show_grading_schemes.assert_called_once_with()
        mock_form_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
