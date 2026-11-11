import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.academic_years.academic_year_form import AcademicYearForm
from ui.academic_years.academic_year_list import AcademicYearListFrame


SAMPLE_ACADEMIC_YEAR = {
    "id": 101,
    "name": "2026-2027",
    "start_date": "2026-09-01",
    "end_date": "2027-06-30",
    "is_current": 1,
}


def find_widgets(parent, widget_type):
    found = []

    for child in parent.winfo_children():
        if isinstance(child, widget_type):
            found.append(child)

        found.extend(find_widgets(child, widget_type))

    return found


def find_button(parent, button_text):
    for button in find_widgets(parent, ttk.Button):
        if button.cget("text") == button_text:
            return button

    raise AssertionError(f"Button not found: {button_text}")


class AcademicYearUITests(unittest.TestCase):

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
        for child in self.frame.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

        self.frame.destroy()
        self.root.update_idletasks()

    # --------------------------------------------------
    # FORM TESTS
    # --------------------------------------------------

    @patch("ui.academic_years.academic_year_form.messagebox.showinfo")
    @patch(
        "ui.academic_years.academic_year_form.create_academic_year",
        return_value=101
    )
    def test_01_create_academic_year(
        self,
        mock_create,
        mock_message
    ):
        on_saved = Mock()

        form = AcademicYearForm(
            self.frame,
            user=self.user,
            on_saved=on_saved
        )
        form.pack(fill="both", expand=True)

        form.name_var.set("2026-2027")
        form.start_date_var.set("2026-09-01")
        form.end_date_var.set("2027-06-30")
        form.is_current_var.set(True)

        form.save_academic_year()

        mock_create.assert_called_once_with({
            "name": "2026-2027",
            "start_date": "2026-09-01",
            "end_date": "2027-06-30",
            "is_current": True,
        }, actor_user_id=self.user["id"])

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.academic_years.academic_year_form.messagebox.showinfo")
    @patch(
        "ui.academic_years.academic_year_form.update_academic_year"
    )
    def test_02_edit_academic_year(
        self,
        mock_update,
        mock_message
    ):
        on_saved = Mock()

        form = AcademicYearForm(
            self.frame,
            user=self.user,
            on_saved=on_saved,
            academic_year=SAMPLE_ACADEMIC_YEAR
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.name_var.get(),
            "2026-2027"
        )
        self.assertTrue(form.is_current_var.get())

        form.name_var.set("Updated Academic Year")
        form.save_academic_year()

        mock_update.assert_called_once_with(
            101,
            {
                "name": "Updated Academic Year",
                "start_date": "2026-09-01",
                "end_date": "2027-06-30",
                "is_current": True,
            },
            actor_user_id=self.user["id"]
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.academic_years.academic_year_form.messagebox.showwarning")
    @patch(
        "ui.academic_years.academic_year_form.create_academic_year",
        side_effect=ValueError("Academic year name is required.")
    )
    def test_03_display_validation_error(
        self,
        mock_create,
        mock_warning
    ):
        form = AcademicYearForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.save_academic_year()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    def test_04_clear_form(self):
        form = AcademicYearForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.name_var.set("2026-2027")
        form.start_date_var.set("2026-09-01")
        form.end_date_var.set("2027-06-30")
        form.is_current_var.set(True)

        form.clear_form()

        self.assertEqual(form.name_var.get(), "")
        self.assertEqual(form.start_date_var.get(), "")
        self.assertEqual(form.end_date_var.get(), "")
        self.assertFalse(form.is_current_var.get())

    def test_05_form_back_callback(self):
        on_back = Mock()

        form = AcademicYearForm(
            self.frame,
            user=self.user,
            on_back=on_back
        )
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()

    # --------------------------------------------------
    # LIST TESTS
    # --------------------------------------------------

    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[SAMPLE_ACADEMIC_YEAR]
    )
    def test_06_list_displays_academic_year(self, mock_get):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        rows = list_frame.tree.get_children()

        self.assertEqual(len(rows), 1)

        values = list_frame.tree.item(rows[0], "values")

        self.assertEqual(values[0], "101")
        self.assertEqual(values[1], "2026-2027")
        self.assertEqual(values[2], "2026-09-01")
        self.assertEqual(values[3], "2027-06-30")
        self.assertEqual(values[4], "Yes")

        mock_get.assert_called_once_with("", actor_user_id=self.user["id"])

    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[SAMPLE_ACADEMIC_YEAR]
    )
    def test_07_search_and_clear(self, mock_get):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("2026")
        list_frame.load_academic_years()

        mock_get.assert_called_with("2026", actor_user_id=self.user["id"])

        list_frame.clear_search()

        self.assertEqual(list_frame.search_var.get(), "")
        mock_get.assert_called_with("", actor_user_id=self.user["id"])

    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[SAMPLE_ACADEMIC_YEAR]
    )
    def test_08_edit_selected_academic_year(self, mock_get):
        on_edit = Mock()

        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=on_edit
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.edit_academic_year()

        on_edit.assert_called_once_with(101)

    @patch("ui.academic_years.academic_year_list.messagebox.showinfo")
    @patch(
        "ui.academic_years.academic_year_list.messagebox.askyesno",
        return_value=False
    )
    @patch(
        "ui.academic_years.academic_year_list.set_current_academic_year"
    )
    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[
            {
                **SAMPLE_ACADEMIC_YEAR,
                "is_current": 0,
            }
        ]
    )
    def test_09_cancel_setting_current_academic_year(
        self,
        mock_get,
        mock_set_current,
        mock_confirm,
        mock_message
    ):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.set_current()

        mock_confirm.assert_called_once()
        mock_set_current.assert_not_called()
        mock_message.assert_not_called()

    @patch("ui.academic_years.academic_year_list.messagebox.showinfo")
    @patch(
        "ui.academic_years.academic_year_list.messagebox.askyesno",
        return_value=True
    )
    @patch(
        "ui.academic_years.academic_year_list.set_current_academic_year"
    )
    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        side_effect=[
            [
                {
                    **SAMPLE_ACADEMIC_YEAR,
                    "is_current": 0,
                }
            ],
            [SAMPLE_ACADEMIC_YEAR],
        ]
    )
    def test_10_set_current_for_non_current_year(
        self,
        mock_get,
        mock_set_current,
        mock_confirm,
        mock_message
    ):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.set_current()

        mock_confirm.assert_called_once()
        mock_set_current.assert_called_once_with(101, actor_user_id=self.user["id"])
        mock_message.assert_called_once()
        self.assertEqual(mock_get.call_count, 2)

    @patch(
        "ui.academic_years.academic_year_list.messagebox.showinfo"
    )
    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[SAMPLE_ACADEMIC_YEAR]
    )
    def test_11_current_year_is_not_set_again(
        self,
        mock_get,
        mock_message
    ):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        with patch(
            "ui.academic_years.academic_year_list.set_current_academic_year"
        ) as mock_set:
            list_frame.set_current()

        mock_set.assert_not_called()
        mock_message.assert_called_once()

    @patch(
        "ui.academic_years.academic_year_list.messagebox.showwarning"
    )
    def test_12_reject_action_without_selection(self, mock_warning):
        list_frame = AcademicYearListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        self.assertIsNone(
            list_frame.get_selected_academic_year()
        )

        mock_warning.assert_called_once()



    @patch(
        "ui.academic_years.academic_year_list.get_academic_years",
        return_value=[SAMPLE_ACADEMIC_YEAR]
    )
    def test_13_staff_can_view_but_cannot_manage_academic_years(self, mock_get):
        staff_user = {
            "id": 2,
            "full_name": "Test Staff",
            "role": "staff",
        }
        on_create = Mock()
        on_edit = Mock()

        list_frame = AcademicYearListFrame(
            self.frame,
            on_create=on_create,
            on_edit=on_edit,
            user=staff_user
        )
        list_frame.pack(fill="both", expand=True)

        self.assertEqual(len(list_frame.tree.get_children()), 1)

        button_labels = {
            button.cget("text")
            for button in find_widgets(list_frame, ttk.Button)
        }
        self.assertNotIn("Create Academic Year", button_labels)
        self.assertNotIn("Edit Academic Year", button_labels)
        self.assertNotIn("Set as Current", button_labels)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)
        list_frame.edit_academic_year()
        list_frame.set_current()

        on_create.assert_not_called()
        on_edit.assert_not_called()
        mock_get.assert_called_once_with(
            "",
            actor_user_id=staff_user["id"]
        )

    def test_14_staff_cannot_open_academic_year_form(self):
        staff_user = {
            "id": 2,
            "full_name": "Test Staff",
            "role": "staff",
        }

        with self.assertRaises(PermissionError):
            AcademicYearForm(self.frame, user=staff_user)

if __name__ == "__main__":
    unittest.main(verbosity=2)
