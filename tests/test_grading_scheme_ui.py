import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.grading_schemes.grading_scheme_form import GradingSchemeForm


SAMPLE_CLASSES = [
    {"id": 1, "name": "Grade 10", "description": "Test class"},
    {"id": 2, "name": "Grade 11", "description": "Second class"},
]

SAMPLE_YEARS = [
    {
        "id": 1,
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": 1,
    }
]

SAMPLE_SCHEME = {
    "id": 101,
    "class_id": 1,
    "class_name": "Grade 10",
    "academic_year_id": 1,
    "academic_year_name": "2026-2027",
    "name": "Standard Grading",
    "version_no": 1,
    "status": "draft",
    "band_count": 3,
}


class GradingSchemeFormUITests(unittest.TestCase):

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
        return GradingSchemeForm(
            self.frame,
            **kwargs,
        )

    # --------------------------------------------------
    # CREATION
    # --------------------------------------------------

    @patch("ui.grading_schemes.grading_scheme_form.messagebox.showinfo")
    @patch(
        "ui.grading_schemes.grading_scheme_form.create_grading_scheme",
        return_value=101,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_01_create_grading_scheme(
        self,
        mock_classes,
        mock_years,
        mock_create,
        mock_message,
    ):
        on_saved = Mock()

        form = self.create_form(on_saved=on_saved)
        form.pack(fill="both", expand=True)

        form.class_var.set(form.class_label_by_id[1])
        form.academic_year_var.set(form.year_label_by_id[1])
        form.name_var.set("Standard Grading")

        form.save_grading_scheme()

        mock_create.assert_called_once_with(
            {
                "class_id": 1,
                "academic_year_id": 1,
                "name": "Standard Grading",
            },
            actor_user_id=self.user["id"],
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch(
        "ui.grading_schemes.grading_scheme_form.update_grading_scheme"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_02_edit_draft_scheme(
        self,
        mock_classes,
        mock_years,
        mock_update,
    ):
        on_saved = Mock()

        with patch(
            "ui.grading_schemes.grading_scheme_form.messagebox.showinfo"
        ) as mock_message:
            form = self.create_form(
                on_saved=on_saved,
                grading_scheme=SAMPLE_SCHEME,
            )
            form.pack(fill="both", expand=True)

            self.assertEqual(
                form.name_var.get(),
                "Standard Grading",
            )

            form.name_var.set("Updated Grading")
            form.save_grading_scheme()

        mock_update.assert_called_once_with(
            101,
            {"name": "Updated Grading"},
            actor_user_id=self.user["id"],
        )
        mock_message.assert_called_once()
        on_saved.assert_called_once()

    # --------------------------------------------------
    # REFERENCE DATA
    # --------------------------------------------------

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_03_load_class_and_year_options(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.class_id_by_label[
                form.class_label_by_id[1]
            ],
            1,
        )

        self.assertEqual(
            form.year_id_by_label[
                form.year_label_by_id[1]
            ],
            1,
        )

        self.assertEqual(
            len(form.class_combo["values"]),
            2,
        )

        self.assertEqual(
            len(form.academic_year_combo["values"]),
            1,
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.messagebox.showwarning"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.create_grading_scheme"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_04_require_class_selection(
        self,
        mock_classes,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        form.academic_year_var.set(form.year_label_by_id[1])
        form.name_var.set("Standard Grading")

        form.save_grading_scheme()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    @patch(
        "ui.grading_schemes.grading_scheme_form.messagebox.showwarning"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.create_grading_scheme"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_05_require_academic_year_selection(
        self,
        mock_classes,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        form.class_var.set(form.class_label_by_id[1])
        form.name_var.set("Standard Grading")

        form.save_grading_scheme()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    # --------------------------------------------------
    # VALIDATION AND ERRORS
    # --------------------------------------------------

    @patch(
        "ui.grading_schemes.grading_scheme_form.messagebox.showwarning"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.create_grading_scheme",
        side_effect=ValueError("Grading scheme name is required."),
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_06_display_validation_error(
        self,
        mock_classes,
        mock_years,
        mock_create,
        mock_warning,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        form.class_var.set(form.class_label_by_id[1])
        form.academic_year_var.set(form.year_label_by_id[1])
        form.save_grading_scheme()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    @patch(
        "ui.grading_schemes.grading_scheme_form.messagebox.showerror"
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.create_grading_scheme",
        side_effect=RuntimeError("Database unavailable."),
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_07_display_unexpected_error(
        self,
        mock_classes,
        mock_years,
        mock_create,
        mock_error,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        form.class_var.set(form.class_label_by_id[1])
        form.academic_year_var.set(form.year_label_by_id[1])
        form.name_var.set("Standard Grading")

        form.save_grading_scheme()

        mock_create.assert_called_once()
        mock_error.assert_called_once()

    # --------------------------------------------------
    # FORM STATE
    # --------------------------------------------------

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_08_existing_scheme_locks_class_and_year(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form(
            grading_scheme=SAMPLE_SCHEME,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.class_combo["state"]),
            "disabled",
        )

        self.assertEqual(
            str(form.academic_year_combo["state"]),
            "disabled",
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_09_active_scheme_is_read_only(
        self,
        mock_classes,
        mock_years,
    ):
        active_scheme = {
            **SAMPLE_SCHEME,
            "status": "active",
        }

        form = self.create_form(
            grading_scheme=active_scheme,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.class_combo["state"]),
            "disabled",
        )
        self.assertEqual(
            str(form.academic_year_combo["state"]),
            "disabled",
        )
        self.assertEqual(
            str(form.name_entry["state"]),
            "disabled",
        )
        self.assertEqual(
            str(form.save_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(form.clear_button["state"]),
            "disabled",
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_10_archived_scheme_is_read_only(
        self,
        mock_classes,
        mock_years,
    ):
        archived_scheme = {
            **SAMPLE_SCHEME,
            "status": "archived",
        }

        form = self.create_form(
            grading_scheme=archived_scheme,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.name_entry["state"]),
            "disabled",
        )
        self.assertEqual(
            str(form.save_button["state"]),
            "disabled",
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=[],
    )
    def test_11_disable_save_without_classes(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.save_button["state"]),
            "disabled",
        )
        self.assertIn(
            "classes",
            form.warning_label.cget("text"),
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=[],
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_12_disable_save_without_academic_years(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.save_button["state"]),
            "disabled",
        )
        self.assertIn(
            "academic years",
            form.warning_label.cget("text"),
        )

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        side_effect=RuntimeError("Database unavailable."),
    )
    def test_13_handle_reference_loading_error(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.save_button["state"]),
            "disabled",
        )
        self.assertIn(
            "Database unavailable",
            form.warning_label.cget("text"),
        )

    # --------------------------------------------------
    # CLEAR AND NAVIGATION
    # --------------------------------------------------

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_14_clear_create_form(
        self,
        mock_classes,
        mock_years,
    ):
        form = self.create_form()
        form.pack(fill="both", expand=True)

        form.class_var.set(form.class_label_by_id[1])
        form.academic_year_var.set(form.year_label_by_id[1])
        form.name_var.set("Standard Grading")

        form.clear_form()

        self.assertEqual(form.class_var.get(), "")
        self.assertEqual(form.academic_year_var.get(), "")
        self.assertEqual(form.name_var.get(), "")

    @patch(
        "ui.grading_schemes.grading_scheme_form.get_academic_years",
        return_value=SAMPLE_YEARS,
    )
    @patch(
        "ui.grading_schemes.grading_scheme_form.get_classes",
        return_value=SAMPLE_CLASSES,
    )
    def test_15_back_callback(
        self,
        mock_classes,
        mock_years,
    ):
        on_back = Mock()

        form = self.create_form(on_back=on_back)
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()


if __name__ == "__main__":
    unittest.main()
