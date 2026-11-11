import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.grading_schemes.grade_band_form import GradeBandForm


SAMPLE_SCHEME = {
    "id": 101,
    "class_id": 1,
    "academic_year_id": 1,
    "name": "Standard Grading",
    "version_no": 1,
    "status": "draft",
}

SAMPLE_BAND = {
    "id": 201,
    "grading_scheme_id": 101,
    "grade_label": "A",
    "min_percentage": 80.0,
    "grade_point": 4.0,
    "remark": "Excellent",
}


class GradeBandFormUITests(unittest.TestCase):

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
        self.user = {
            "id": 1,
            "full_name": "Test Administrator",
            "role": "admin",
        }
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        self.frame.destroy()
        self.root.update_idletasks()

    def create_form(self, **kwargs):
        kwargs.setdefault("user", self.user)
        return GradeBandForm(
            self.frame,
            grading_scheme=kwargs.pop(
                "grading_scheme",
                SAMPLE_SCHEME,
            ),
            **kwargs,
        )

    def fill_form(
        self,
        form,
        label="A",
        percentage="80",
        grade_point="4.0",
        remark="Excellent",
    ):
        form.grade_label_var.set(label)
        form.min_percentage_var.set(percentage)
        form.grade_point_var.set(grade_point)

        form.remark_text.delete("1.0", "end")
        form.remark_text.insert("1.0", remark)

    # --------------------------------------------------
    # CREATION
    # --------------------------------------------------

    @patch("ui.grading_schemes.grade_band_form.messagebox.showinfo")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band",
        return_value=201,
    )
    def test_01_create_grade_band(
        self,
        mock_create,
        mock_message,
    ):
        on_saved = Mock()

        form = self.create_form(on_saved=on_saved)
        form.pack(fill="both", expand=True)

        self.fill_form(form)
        form.save_grade_band()

        mock_create.assert_called_once_with(
            101,
            {
                "grade_label": "A",
                "min_percentage": 80.0,
                "grade_point": 4.0,
                "remark": "Excellent",
            },
                    actor_user_id=self.user["id"],
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.grading_schemes.grade_band_form.messagebox.showinfo")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band",
        return_value=202,
    )
    def test_02_create_without_optional_grade_point(
        self,
        mock_create,
        mock_message,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(
            form,
            grade_point="",
            remark="Pass",
        )

        form.save_grade_band()

        mock_create.assert_called_once_with(
            101,
            {
                "grade_label": "A",
                "min_percentage": 80.0,
                "grade_point": None,
                "remark": "Pass",
            },
                    actor_user_id=self.user["id"],
        )

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------

    @patch("ui.grading_schemes.grade_band_form.messagebox.showinfo")
    @patch(
        "ui.grading_schemes.grade_band_form.update_grade_band"
    )
    def test_03_update_existing_grade_band(
        self,
        mock_update,
        mock_message,
    ):
        on_saved = Mock()

        form = self.create_form(
            grade_band=SAMPLE_BAND,
            on_saved=on_saved,
        )
        form.pack(fill="both", expand=True)

        self.fill_form(
            form,
            label="A+",
            percentage="90",
            grade_point="4.5",
            remark="Outstanding",
        )

        form.save_grade_band()

        mock_update.assert_called_once_with(
            201,
            {
                "grade_label": "A+",
                "min_percentage": 90.0,
                "grade_point": 4.5,
                "remark": "Outstanding",
            },
                    actor_user_id=self.user["id"],
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    def test_04_load_existing_grade_band(self):
        form = self.create_form(
            grade_band=SAMPLE_BAND,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(form.grade_label_var.get(), "A")
        self.assertEqual(form.min_percentage_var.get(), "80.0")
        self.assertEqual(form.grade_point_var.get(), "4.0")
        self.assertEqual(
            form.remark_text.get("1.0", "end-1c"),
            "Excellent",
        )

    def test_05_load_existing_band_without_grade_point(self):
        band = dict(SAMPLE_BAND)
        band["grade_point"] = None

        form = self.create_form(grade_band=band)
        form.pack(fill="both", expand=True)

        self.assertEqual(form.grade_point_var.get(), "")

    # --------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------

    @patch("ui.grading_schemes.grade_band_form.messagebox.showwarning")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band"
    )
    def test_06_require_minimum_percentage(
        self,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(form, percentage="")

        form.save_grade_band()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

        self.assertIn(
            "required",
            mock_warning.call_args.args[1].lower(),
        )

    @patch("ui.grading_schemes.grade_band_form.messagebox.showwarning")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band"
    )
    def test_07_reject_non_numeric_percentage(
        self,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(form, percentage="eighty")

        form.save_grade_band()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    @patch("ui.grading_schemes.grade_band_form.messagebox.showwarning")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band"
    )
    def test_08_reject_non_numeric_grade_point(
        self,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(form, grade_point="four")

        form.save_grade_band()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

        self.assertIn(
            "grade point",
            mock_warning.call_args.args[1].lower(),
        )

    # --------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------

    @patch("ui.grading_schemes.grade_band_form.messagebox.showerror")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band",
        side_effect=RuntimeError("Database failure"),
    )
    def test_09_handle_service_error(
        self,
        mock_create,
        mock_error,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(form)
        form.save_grade_band()

        mock_create.assert_called_once()
        mock_error.assert_called_once()

        self.assertIn(
            "Database failure",
            mock_error.call_args.args[1],
        )

    # --------------------------------------------------
    # FORM RESET
    # --------------------------------------------------

    def test_10_clear_new_grade_band_form(self):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.fill_form(form)
        form.clear_form()

        self.assertEqual(form.grade_label_var.get(), "")
        self.assertEqual(form.min_percentage_var.get(), "")
        self.assertEqual(form.grade_point_var.get(), "")
        self.assertEqual(
            form.remark_text.get("1.0", "end-1c"),
            "",
        )

    def test_11_clear_edit_form_restores_original_values(self):
        form = self.create_form(
            grade_band=SAMPLE_BAND,
        )
        form.pack(fill="both", expand=True)

        self.fill_form(
            form,
            label="Changed",
            percentage="50",
            grade_point="2.0",
            remark="Temporary remark",
        )

        form.clear_form()

        self.assertEqual(form.grade_label_var.get(), "A")
        self.assertEqual(form.min_percentage_var.get(), "80.0")
        self.assertEqual(form.grade_point_var.get(), "4.0")
        self.assertEqual(
            form.remark_text.get("1.0", "end-1c"),
            "Excellent",
        )

    # --------------------------------------------------
    # LOCKED SCHEMES
    # --------------------------------------------------

    def test_12_active_scheme_is_read_only(self):
        active_scheme = dict(SAMPLE_SCHEME)
        active_scheme["status"] = "active"

        form = self.create_form(
            grading_scheme=active_scheme,
            grade_band=SAMPLE_BAND,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(str(form.save_button["state"]), "disabled")
        self.assertEqual(str(form.clear_button["state"]), "disabled")
        self.assertEqual(str(form.remark_text["state"]), "disabled")

        for entry in form.entries.values():
            self.assertEqual(str(entry["state"]), "disabled")

    def test_13_archived_scheme_is_read_only(self):
        archived_scheme = dict(SAMPLE_SCHEME)
        archived_scheme["status"] = "archived"

        form = self.create_form(
            grading_scheme=archived_scheme,
            grade_band=SAMPLE_BAND,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(str(form.save_button["state"]), "disabled")
        self.assertEqual(str(form.clear_button["state"]), "disabled")

    @patch("ui.grading_schemes.grade_band_form.messagebox.showwarning")
    @patch(
        "ui.grading_schemes.grade_band_form.create_grade_band"
    )
    def test_14_locked_scheme_rejects_save(
        self,
        mock_create,
        mock_warning,
    ):
        active_scheme = dict(SAMPLE_SCHEME)
        active_scheme["status"] = "active"

        form = self.create_form(
            grading_scheme=active_scheme,
        )
        form.pack(fill="both", expand=True)

        self.fill_form(form)
        form.save_grade_band()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def test_15_back_callback(self):
        on_back = Mock()

        form = self.create_form(on_back=on_back)
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
