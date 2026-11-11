import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

from ui.grading_schemes.grading_scheme_list import GradingSchemeListFrame


SAMPLE_CLASSES = [
    {"id": 1, "name": "Grade 10"},
    {"id": 2, "name": "Grade 11"},
]

SAMPLE_YEARS = [
    {
        "id": 10,
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-08-31",
    },
]

SAMPLE_SCHEMES = [
    {
        "id": 101,
        "name": "Standard Grading",
        "class_name": "Grade 10",
        "academic_year_name": "2026-2027",
        "version_no": 1,
        "band_count": 5,
        "status": "draft",
        "created_at": "2026-11-05 10:00:00",
    },
    {
        "id": 102,
        "name": "Previous Grading",
        "class_name": "Grade 11",
        "academic_year_name": "2026-2027",
        "version_no": 2,
        "band_count": 4,
        "status": "active",
        "created_at": "2026-11-05 11:00:00",
    },
    {
        "id": 103,
        "name": "Archived Grading",
        "class_name": "Grade 10",
        "academic_year_name": "2026-2027",
        "version_no": 1,
        "band_count": 3,
        "status": "archived",
        "created_at": "2026-11-05 12:00:00",
    },
]


class GradingSchemeListUITests(unittest.TestCase):

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

        self.classes_patcher = patch(
            "ui.grading_schemes.grading_scheme_list.get_classes",
            return_value=SAMPLE_CLASSES,
        )
        self.years_patcher = patch(
            "ui.grading_schemes.grading_scheme_list.get_academic_years",
            return_value=SAMPLE_YEARS,
        )
        self.schemes_patcher = patch(
            "ui.grading_schemes.grading_scheme_list.get_grading_schemes",
            return_value=SAMPLE_SCHEMES,
        )
        self.activate_patcher = patch(
            "ui.grading_schemes.grading_scheme_list.activate_grading_scheme"
        )
        self.archive_patcher = patch(
            "ui.grading_schemes.grading_scheme_list.archive_grading_scheme"
        )

        self.get_classes = self.classes_patcher.start()
        self.get_years = self.years_patcher.start()
        self.get_schemes = self.schemes_patcher.start()
        self.activate_scheme = self.activate_patcher.start()
        self.archive_scheme = self.archive_patcher.start()

        self.dialog_patchers = [
            patch(
                "ui.grading_schemes.grading_scheme_list.messagebox.showinfo"
            ),
            patch(
                "ui.grading_schemes.grading_scheme_list.messagebox.showwarning"
            ),
            patch(
                "ui.grading_schemes.grading_scheme_list.messagebox.showerror"
            ),
            patch(
                "ui.grading_schemes.grading_scheme_list.messagebox.askyesno",
                return_value=False,
            ),
        ]

        self.showinfo = self.dialog_patchers[0].start()
        self.showwarning = self.dialog_patchers[1].start()
        self.showerror = self.dialog_patchers[2].start()
        self.askyesno = self.dialog_patchers[3].start()

        self.root.update_idletasks()

    def tearDown(self):
        for patcher in self.dialog_patchers:
            patcher.stop()

        for patcher in (
            self.classes_patcher,
            self.years_patcher,
            self.schemes_patcher,
            self.activate_patcher,
            self.archive_patcher,
        ):
            patcher.stop()

        self.frame.destroy()
        self.root.update_idletasks()

    def create_list(self, **kwargs):
        kwargs.setdefault("user", self.user)
        return GradingSchemeListFrame(
            self.frame,
            **kwargs,
        )

    def select_scheme(self, scheme_list, scheme_id):
        scheme_list.tree.selection_set(str(scheme_id))
        scheme_list.tree.focus(str(scheme_id))
        scheme_list.apply_selection_controls()

    # --------------------------------------------------
    # INITIAL LOADING
    # --------------------------------------------------

    def test_01_load_grading_schemes(self):
        page = self.create_list()

        rows = page.tree.get_children()

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows, ("101", "102", "103"))

        values = page.tree.item("101", "values")

        self.assertEqual(
            values,
            (
                "101",
                "Standard Grading",
                "Grade 10",
                "2026-2027",
                "1",
                "5",
                "Draft",
                "2026-11-05 10:00:00",
            ),
        )

        self.get_schemes.assert_called_once_with(
            class_id=None,
            academic_year_id=None,
            status=None,
            search="",
            actor_user_id=self.user["id"],
        )

    def test_02_load_empty_list(self):
        self.get_schemes.return_value = []

        page = self.create_list()

        self.assertEqual(page.tree.get_children(), ())

    def test_03_display_scheme_loading_error(self):
        self.get_schemes.side_effect = RuntimeError(
            "Database unavailable"
        )

        page = self.create_list()

        self.assertEqual(page.tree.get_children(), ())
        self.showerror.assert_called_once()

        self.assertIn(
            "Database unavailable",
            self.showerror.call_args.args[1],
        )

    def test_04_load_class_filter_options(self):
        page = self.create_list()

        self.assertEqual(
            page.class_id_by_label["Grade 10 (ID: 1)"],
            1,
        )
        self.assertEqual(
            page.class_id_by_label["Grade 11 (ID: 2)"],
            2,
        )
        self.assertIn("All", page.class_combo["values"])

    def test_05_load_academic_year_filter_options(self):
        page = self.create_list()

        label = (
            "2026-2027 (2026-09-01 to 2027-08-31) (ID: 10)"
        )

        self.assertEqual(
            page.academic_year_id_by_label[label],
            10,
        )

    def test_06_handle_class_filter_loading_error(self):
        self.get_classes.side_effect = RuntimeError(
            "Class query failed"
        )

        page = self.create_list()

        self.assertEqual(page.class_var.get(), "All")
        self.assertEqual(
            list(page.class_combo["values"]),
            ["All"],
        )
        self.showerror.assert_called()

    def test_07_handle_academic_year_filter_loading_error(self):
        self.get_years.side_effect = RuntimeError(
            "Academic year query failed"
        )

        page = self.create_list()

        self.assertEqual(page.academic_year_var.get(), "All")
        self.assertEqual(
            list(page.academic_year_combo["values"]),
            ["All"],
        )
        self.showerror.assert_called()

    # --------------------------------------------------
    # FILTERING
    # --------------------------------------------------

    def test_08_apply_all_filters(self):
        page = self.create_list()

        class_label = "Grade 10 (ID: 1)"
        year_label = (
            "2026-2027 (2026-09-01 to 2027-08-31) (ID: 10)"
        )

        page.class_var.set(class_label)
        page.academic_year_var.set(year_label)
        page.status_var.set("Active")
        page.search_var.set("  standard  ")

        page.load_grading_schemes()

        self.get_schemes.assert_called_with(
            class_id=1,
            academic_year_id=10,
            status="active",
            search="standard",
            actor_user_id=self.user["id"],
        )

    def test_09_reset_filters(self):
        page = self.create_list()

        page.class_var.set("Grade 10 (ID: 1)")
        page.academic_year_var.set(
            "2026-2027 (2026-09-01 to 2027-08-31) (ID: 10)"
        )
        page.status_var.set("Archived")
        page.search_var.set("old scheme")

        page.reset_filters()

        self.assertEqual(page.class_var.get(), "All")
        self.assertEqual(page.academic_year_var.get(), "All")
        self.assertEqual(page.status_var.get(), "All")
        self.assertEqual(page.search_var.get(), "")

        self.get_schemes.assert_called_with(
            class_id=None,
            academic_year_id=None,
            status=None,
            search="",
            actor_user_id=self.user["id"],
        )

    def test_10_refresh_reloads_reference_data_and_schemes(self):
        page = self.create_list()

        self.get_classes.reset_mock()
        self.get_years.reset_mock()
        self.get_schemes.reset_mock()

        page.refresh()

        self.get_classes.assert_called_once_with(actor_user_id=self.user['id'])
        self.get_years.assert_called_once_with(actor_user_id=self.user['id'])
        self.get_schemes.assert_called_once()

    # --------------------------------------------------
    # SELECTION AND BUTTON STATES
    # --------------------------------------------------

    def test_11_no_selection_disables_actions(self):
        page = self.create_list()

        self.assertEqual(
            str(page.edit_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(page.manage_bands_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(page.activate_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(page.archive_button["state"]),
            "disabled",
        )

    def test_12_draft_selection_enables_all_actions(self):
        page = self.create_list()
        self.select_scheme(page, 101)

        for button in (
            page.edit_button,
            page.manage_bands_button,
            page.activate_button,
            page.archive_button,
        ):
            self.assertEqual(str(button["state"]), "normal")

    def test_13_active_selection_locks_edit_and_activation(self):
        page = self.create_list()
        self.select_scheme(page, 102)

        self.assertEqual(str(page.edit_button["state"]), "disabled")
        self.assertEqual(
            str(page.manage_bands_button["state"]),
            "normal",
        )
        self.assertEqual(
            str(page.activate_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(page.archive_button["state"]),
            "normal",
        )

    def test_14_archived_selection_allows_only_band_management(self):
        page = self.create_list()
        self.select_scheme(page, 103)

        self.assertEqual(str(page.edit_button["state"]), "disabled")
        self.assertEqual(
            str(page.manage_bands_button["state"]),
            "normal",
        )
        self.assertEqual(
            str(page.activate_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(page.archive_button["state"]),
            "disabled",
        )

    def test_15_warn_when_no_scheme_is_selected(self):
        page = self.create_list()

        self.assertIsNone(page.get_selected_scheme())
        self.showwarning.assert_called_once()

    def test_16_return_selected_scheme(self):
        page = self.create_list()
        self.select_scheme(page, 101)

        scheme = page.get_selected_scheme()

        self.assertEqual(scheme["id"], 101)
        self.assertEqual(scheme["name"], "Standard Grading")
        self.assertEqual(scheme["status"], "draft")
        self.assertEqual(scheme["version_no"], 1)

    # --------------------------------------------------
    # CREATE, EDIT AND BAND MANAGEMENT
    # --------------------------------------------------

    def test_17_create_calls_callback(self):
        callback = patch(
            "ui.grading_schemes.grading_scheme_list.get_grading_schemes",
            return_value=SAMPLE_SCHEMES,
        )

        on_create = patch.object(
            GradingSchemeListFrame,
            "create_grading_scheme",
        )

        callback.start()
        on_create.stop()

        create_callback = unittest.mock.Mock()
        page = self.create_list(on_create=create_callback)

        page.create_grading_scheme()

        create_callback.assert_called_once_with()

        callback.stop()

    def test_18_edit_draft_calls_callback(self):
        from unittest.mock import Mock

        edit_callback = Mock()
        page = self.create_list(on_edit=edit_callback)
        self.select_scheme(page, 101)

        page.edit_selected()

        edit_callback.assert_called_once_with(101)

    def test_19_edit_active_scheme_is_rejected(self):
        from unittest.mock import Mock

        edit_callback = Mock()
        page = self.create_list(on_edit=edit_callback)
        self.select_scheme(page, 102)

        page.edit_selected()

        edit_callback.assert_not_called()
        self.showwarning.assert_called_once()

    def test_20_manage_bands_calls_callback(self):
        from unittest.mock import Mock

        callback = Mock()
        page = self.create_list(on_manage_bands=callback)
        self.select_scheme(page, 103)

        page.manage_selected_bands()

        callback.assert_called_once_with(103)

    # --------------------------------------------------
    # ACTIVATION
    # --------------------------------------------------

    def test_21_cancel_activation(self):
        page = self.create_list()
        self.select_scheme(page, 101)

        self.askyesno.return_value = False
        page.activate_selected()

        self.activate_scheme.assert_not_called()
        self.showinfo.assert_not_called()

    def test_22_confirm_activation(self):
        page = self.create_list()
        self.select_scheme(page, 101)

        self.askyesno.return_value = True
        page.activate_selected()

        self.activate_scheme.assert_called_once_with(
            101, actor_user_id=self.user["id"]
        )
        self.showinfo.assert_called_once()

    def test_23_display_activation_validation_error(self):
        self.activate_scheme.side_effect = ValueError(
            "At least two grade bands are required."
        )

        page = self.create_list()
        self.select_scheme(page, 101)
        self.askyesno.return_value = True

        page.activate_selected()

        self.showwarning.assert_called_once()
        self.assertIn(
            "At least two grade bands",
            self.showwarning.call_args.args[1],
        )

    def test_24_display_activation_unexpected_error(self):
        self.activate_scheme.side_effect = RuntimeError(
            "Database unavailable"
        )

        page = self.create_list()
        self.select_scheme(page, 101)
        self.askyesno.return_value = True

        page.activate_selected()

        self.showerror.assert_called_once()

    # --------------------------------------------------
    # ARCHIVING
    # --------------------------------------------------

    def test_25_cancel_archiving(self):
        page = self.create_list()
        self.select_scheme(page, 102)

        self.askyesno.return_value = False
        page.archive_selected()

        self.archive_scheme.assert_not_called()

    def test_26_confirm_archiving(self):
        page = self.create_list()
        self.select_scheme(page, 102)

        self.askyesno.return_value = True
        page.archive_selected()

        self.archive_scheme.assert_called_once_with(
            102, actor_user_id=self.user["id"]
        )
        self.showinfo.assert_called_once()

    def test_27_display_archiving_validation_error(self):
        self.archive_scheme.side_effect = ValueError(
            "Cannot archive this scheme."
        )

        page = self.create_list()
        self.select_scheme(page, 101)
        self.askyesno.return_value = True

        page.archive_selected()

        self.showwarning.assert_called_once()

    def test_28_display_archiving_unexpected_error(self):
        self.archive_scheme.side_effect = RuntimeError(
            "Database unavailable"
        )

        page = self.create_list()
        self.select_scheme(page, 101)
        self.askyesno.return_value = True

        page.archive_selected()

        self.showerror.assert_called_once()

    def test_29_archived_scheme_cannot_be_archived_again(self):
        page = self.create_list()
        self.select_scheme(page, 103)

        page.archive_selected()

        self.archive_scheme.assert_not_called()
        self.askyesno.assert_not_called()
        self.showwarning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
