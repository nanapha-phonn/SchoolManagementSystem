import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.grading_schemes.grade_band_list import GradeBandListFrame


SAMPLE_SCHEME = {
    "id": 101,
    "class_id": 1,
    "academic_year_id": 1,
    "name": "Standard Grading",
    "version_no": 1,
    "status": "draft",
}

SAMPLE_BANDS = [
    {
        "id": 201,
        "grading_scheme_id": 101,
        "grade_label": "A",
        "min_percentage": 80.0,
        "grade_point": 4.0,
        "remark": "Excellent",
    },
    {
        "id": 202,
        "grading_scheme_id": 101,
        "grade_label": "F",
        "min_percentage": 0.0,
        "grade_point": None,
        "remark": "Needs improvement",
    },
]


class GradeBandListUITests(unittest.TestCase):

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

        self.get_bands_patcher = patch(
            "ui.grading_schemes.grade_band_list.get_grade_bands",
            return_value=SAMPLE_BANDS,
        )
        self.delete_patcher = patch(
            "ui.grading_schemes.grade_band_list.delete_grade_band"
        )
        self.activate_patcher = patch(
            "ui.grading_schemes.grade_band_list.activate_grading_scheme"
        )
        self.archive_patcher = patch(
            "ui.grading_schemes.grade_band_list.archive_grading_scheme"
        )

        self.get_bands = self.get_bands_patcher.start()
        self.delete_band = self.delete_patcher.start()
        self.activate_scheme_service = self.activate_patcher.start()
        self.archive_scheme_service = self.archive_patcher.start()

        self.dialog_patches = [
            patch(
                "ui.grading_schemes.grade_band_list.messagebox.showinfo"
            ),
            patch(
                "ui.grading_schemes.grade_band_list.messagebox.showwarning"
            ),
            patch(
                "ui.grading_schemes.grade_band_list.messagebox.showerror"
            ),
            patch(
                "ui.grading_schemes.grade_band_list.messagebox.askyesno",
                return_value=False,
            ),
        ]

        self.showinfo = self.dialog_patches[0].start()
        self.showwarning = self.dialog_patches[1].start()
        self.showerror = self.dialog_patches[2].start()
        self.askyesno = self.dialog_patches[3].start()

        self.root.update_idletasks()

    def tearDown(self):
        for patcher in self.dialog_patches:
            patcher.stop()

        self.get_bands_patcher.stop()
        self.delete_patcher.stop()
        self.activate_patcher.stop()
        self.archive_patcher.stop()

        self.frame.destroy()
        self.root.update_idletasks()

    def create_list(self, status="draft", **kwargs):
        scheme = dict(SAMPLE_SCHEME)
        scheme["status"] = status

        kwargs.setdefault("user", self.user)

        return GradeBandListFrame(
            self.frame,
            grading_scheme=scheme,
            **kwargs,
        )

    def select_first_band(self, grade_list):
        items = grade_list.tree.get_children()

        if items:
            grade_list.tree.selection_set(items[0])

    # --------------------------------------------------
    # INITIAL LOADING
    # --------------------------------------------------

    def test_01_load_grade_bands_into_table(self):
        grade_list = self.create_list()

        rows = grade_list.tree.get_children()

        self.assertEqual(len(rows), 2)

        first = grade_list.tree.item(rows[0], "values")
        second = grade_list.tree.item(rows[1], "values")

        self.assertEqual(
            first,
            ("201", "A", "80%", "4", "Excellent"),
        )

        self.assertEqual(
            second,
            ("202", "F", "0%", "", "Needs improvement"),
        )

        self.get_bands.assert_called_once_with(101, actor_user_id=self.user["id"])

    def test_02_load_empty_grade_band_list(self):
        self.get_bands.return_value = []

        grade_list = self.create_list()

        self.assertEqual(
            grade_list.tree.get_children(),
            (),
        )

    def test_03_display_loading_error(self):
        self.get_bands.side_effect = RuntimeError(
            "Database unavailable"
        )

        grade_list = self.create_list()

        self.assertEqual(
            grade_list.tree.get_children(),
            (),
        )

        self.showerror.assert_called_once()

        self.assertIn(
            "Database unavailable",
            self.showerror.call_args.args[1],
        )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def test_04_warn_when_no_grade_band_is_selected(self):
        grade_list = self.create_list()

        result = grade_list.get_selected_grade_band()

        self.assertIsNone(result)
        self.showwarning.assert_called_once()

    def test_05_return_selected_grade_band(self):
        grade_list = self.create_list()
        self.select_first_band(grade_list)

        result = grade_list.get_selected_grade_band()

        self.assertEqual(
            result,
            {
                "id": 201,
                "grade_label": "A",
                "min_percentage": "80%",
                "grade_point": "4",
                "remark": "Excellent",
            },
        )

    # --------------------------------------------------
    # CREATE / EDIT
    # --------------------------------------------------

    def test_06_add_button_calls_callback(self):
        on_add = Mock()
        grade_list = self.create_list(on_add=on_add)

        grade_list.add_grade_band()

        on_add.assert_called_once()

    def test_07_edit_selected_calls_callback(self):
        on_edit = Mock()
        grade_list = self.create_list(on_edit=on_edit)
        self.select_first_band(grade_list)

        grade_list.edit_selected()

        on_edit.assert_called_once_with(201)

    def test_08_edit_without_selection_does_not_call_callback(self):
        on_edit = Mock()
        grade_list = self.create_list(on_edit=on_edit)

        grade_list.edit_selected()

        on_edit.assert_not_called()
        self.showwarning.assert_called_once()

    def test_09_draft_scheme_allows_editing_controls(self):
        grade_list = self.create_list()

        self.assertEqual(
            str(grade_list.add_button.cget("state")),
            "normal",
        )
        self.assertEqual(
            str(grade_list.edit_button.cget("state")),
            "normal",
        )
        self.assertEqual(
            str(grade_list.delete_button.cget("state")),
            "normal",
        )
        self.assertEqual(
            str(grade_list.activate_button.cget("state")),
            "normal",
        )
        self.assertEqual(
            str(grade_list.archive_button.cget("state")),
            "normal",
        )

    def test_10_active_scheme_locks_grade_band_controls(self):
        grade_list = self.create_list(status="active")

        for button in (
            grade_list.add_button,
            grade_list.edit_button,
            grade_list.delete_button,
            grade_list.activate_button,
        ):
            self.assertEqual(
                str(button.cget("state")),
                "disabled",
            )

        self.assertEqual(
            str(grade_list.archive_button.cget("state")),
            "normal",
        )

    def test_11_archived_scheme_disables_all_lifecycle_controls(self):
        grade_list = self.create_list(status="archived")

        for button in (
            grade_list.add_button,
            grade_list.edit_button,
            grade_list.delete_button,
            grade_list.activate_button,
            grade_list.archive_button,
        ):
            self.assertEqual(
                str(button.cget("state")),
                "disabled",
            )

    def test_12_direct_add_on_active_scheme_is_rejected(self):
        on_add = Mock()
        grade_list = self.create_list(
            status="active",
            on_add=on_add,
        )

        grade_list.add_grade_band()

        on_add.assert_not_called()
        self.showwarning.assert_called_once()

    def test_13_direct_edit_on_archived_scheme_is_rejected(self):
        on_edit = Mock()
        grade_list = self.create_list(
            status="archived",
            on_edit=on_edit,
        )
        self.select_first_band(grade_list)

        grade_list.edit_selected()

        on_edit.assert_not_called()
        self.showwarning.assert_called_once()

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    def test_14_cancel_grade_band_deletion(self):
        grade_list = self.create_list()
        self.select_first_band(grade_list)
        self.askyesno.return_value = False

        grade_list.delete_selected()

        self.askyesno.assert_called_once()
        self.delete_band.assert_not_called()
        self.showinfo.assert_not_called()

    def test_15_confirm_grade_band_deletion(self):
        grade_list = self.create_list()
        self.select_first_band(grade_list)
        self.askyesno.return_value = True

        grade_list.delete_selected()

        self.delete_band.assert_called_once_with(201, actor_user_id=self.user["id"])
        self.showinfo.assert_called_once()
        self.assertEqual(self.get_bands.call_count, 2)

    def test_16_display_grade_band_deletion_validation_error(self):
        grade_list = self.create_list()
        self.select_first_band(grade_list)
        self.askyesno.return_value = True

        self.delete_band.side_effect = ValueError(
            "Grade band cannot be deleted."
        )

        grade_list.delete_selected()

        self.delete_band.assert_called_once_with(201, actor_user_id=self.user["id"])
        self.showwarning.assert_called_once()

        self.assertIn(
            "Grade band cannot be deleted.",
            self.showwarning.call_args.args[1],
        )

    def test_17_display_unexpected_grade_band_deletion_error(self):
        grade_list = self.create_list()
        self.select_first_band(grade_list)
        self.askyesno.return_value = True

        self.delete_band.side_effect = RuntimeError(
            "Unexpected database error"
        )

        grade_list.delete_selected()

        self.delete_band.assert_called_once_with(201, actor_user_id=self.user["id"])
        self.showerror.assert_called_once()

        self.assertIn(
            "Unexpected database error",
            self.showerror.call_args.args[1],
        )

    def test_18_active_scheme_cannot_delete_grade_band(self):
        grade_list = self.create_list(status="active")
        self.select_first_band(grade_list)

        grade_list.delete_selected()

        self.delete_band.assert_not_called()
        self.askyesno.assert_not_called()
        self.showwarning.assert_called_once()

    # --------------------------------------------------
    # ACTIVATION
    # --------------------------------------------------

    def test_19_cancel_scheme_activation(self):
        grade_list = self.create_list()
        self.askyesno.return_value = False

        grade_list.activate_scheme()

        self.askyesno.assert_called_once()
        self.activate_scheme_service.assert_not_called()

    def test_20_activate_draft_scheme(self):
        on_scheme_changed = Mock()
        grade_list = self.create_list(
            on_scheme_changed=on_scheme_changed,
        )
        self.askyesno.return_value = True

        grade_list.activate_scheme()

        self.activate_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showinfo.assert_called_once()
        on_scheme_changed.assert_called_once()

    def test_21_display_scheme_activation_validation_error(self):
        grade_list = self.create_list()
        self.askyesno.return_value = True

        self.activate_scheme_service.side_effect = ValueError(
            "At least two grade bands are required."
        )

        grade_list.activate_scheme()

        self.activate_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showwarning.assert_called_once()

        self.assertIn(
            "At least two grade bands are required.",
            self.showwarning.call_args.args[1],
        )

    def test_22_display_unexpected_scheme_activation_error(self):
        grade_list = self.create_list()
        self.askyesno.return_value = True

        self.activate_scheme_service.side_effect = RuntimeError(
            "Activation database error"
        )

        grade_list.activate_scheme()

        self.activate_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showerror.assert_called_once()

        self.assertIn(
            "Activation database error",
            self.showerror.call_args.args[1],
        )

    def test_23_active_scheme_cannot_be_activated_again(self):
        grade_list = self.create_list(status="active")

        grade_list.activate_scheme()

        self.activate_scheme_service.assert_not_called()
        self.askyesno.assert_not_called()
        self.showwarning.assert_called_once()

    # --------------------------------------------------
    # ARCHIVING
    # --------------------------------------------------

    def test_24_cancel_scheme_archiving(self):
        grade_list = self.create_list(status="draft")
        self.askyesno.return_value = False

        grade_list.archive_scheme()

        self.askyesno.assert_called_once()
        self.archive_scheme_service.assert_not_called()

    def test_25_archive_active_scheme(self):
        on_scheme_changed = Mock()
        grade_list = self.create_list(
            status="active",
            on_scheme_changed=on_scheme_changed,
        )
        self.askyesno.return_value = True

        grade_list.archive_scheme()

        self.archive_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showinfo.assert_called_once()
        on_scheme_changed.assert_called_once()

    def test_26_archive_draft_scheme(self):
        grade_list = self.create_list()
        self.askyesno.return_value = True

        grade_list.archive_scheme()

        self.archive_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showinfo.assert_called_once()

    def test_27_display_scheme_archiving_validation_error(self):
        grade_list = self.create_list()
        self.askyesno.return_value = True

        self.archive_scheme_service.side_effect = ValueError(
            "Scheme cannot be archived."
        )

        grade_list.archive_scheme()

        self.archive_scheme_service.assert_called_once_with(101, actor_user_id=self.user["id"])
        self.showwarning.assert_called_once()

        self.assertIn(
            "Scheme cannot be archived.",
            self.showwarning.call_args.args[1],
        )

    def test_28_archived_scheme_cannot_be_archived_again(self):
        grade_list = self.create_list(status="archived")

        grade_list.archive_scheme()

        self.archive_scheme_service.assert_not_called()
        self.askyesno.assert_not_called()
        self.showwarning.assert_called_once()

    # --------------------------------------------------
    # NAVIGATION / REFRESH
    # --------------------------------------------------

    def test_29_back_button_calls_callback(self):
        on_back = Mock()
        grade_list = self.create_list(on_back=on_back)

        grade_list.go_back()

        on_back.assert_called_once()

    def test_30_refresh_reloads_grade_bands(self):
        grade_list = self.create_list()

        self.get_bands.reset_mock()

        grade_list.refresh()

        self.get_bands.assert_called_once_with(101, actor_user_id=self.user["id"])


if __name__ == "__main__":
    unittest.main()
