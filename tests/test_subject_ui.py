import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.subjects.subject_form import SubjectForm
from ui.subjects.subject_list import SubjectListFrame


SAMPLE_SUBJECTS = [
    {
        "id": 1,
        "subject_code": "MATH",
        "name": "Mathematics",
        "description": "Mathematics subject",
        "status": "active",
    },
    {
        "id": 2,
        "subject_code": "SCI",
        "name": "Science",
        "description": None,
        "status": "inactive",
    },
]

SAMPLE_SUBJECT = SAMPLE_SUBJECTS[0]


class SubjectUITests(unittest.TestCase):

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
        self.user = {"id": 1, "role": "admin"}
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)
        self.root.update_idletasks()

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

    @patch("ui.subjects.subject_form.messagebox.showinfo")
    @patch("ui.subjects.subject_form.create_subject")
    def test_01_create_subject(
        self,
        mock_create,
        mock_message,
    ):
        on_saved = Mock()

        form = SubjectForm(
            self.frame,
            user=self.user,
            on_saved=on_saved,
        )
        form.pack(fill="both", expand=True)

        form.subject_code_var.set("MATH")
        form.name_var.set("Mathematics")
        form.description_text.insert(
            "1.0",
            "Mathematics subject",
        )

        form.save_subject()

        mock_create.assert_called_once_with({
            "subject_code": "MATH",
            "name": "Mathematics",
            "description": "Mathematics subject",
            "status": "active",
        }, actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.subjects.subject_form.messagebox.showinfo")
    @patch("ui.subjects.subject_form.update_subject")
    def test_02_edit_subject(
        self,
        mock_update,
        mock_message,
    ):
        on_saved = Mock()

        form = SubjectForm(
            self.frame,
            user=self.user,
            on_saved=on_saved,
            subject=SAMPLE_SUBJECT,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.subject_code_var.get(),
            "MATH",
        )
        self.assertEqual(
            form.name_var.get(),
            "Mathematics",
        )
        self.assertEqual(
            form.description_text.get("1.0", "end-1c"),
            "Mathematics subject",
        )

        form.subject_code_var.set("MATH2")
        form.name_var.set("Advanced Mathematics")
        form.description_text.delete("1.0", "end")
        form.description_text.insert(
            "1.0",
            "Advanced subject",
        )
        form.status_var.set("inactive")

        form.save_subject()

        mock_update.assert_called_once_with(
            1,
            {
                "subject_code": "MATH2",
                "name": "Advanced Mathematics",
                "description": "Advanced subject",
                "status": "inactive",
            },
            actor_user_id=1,
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.subjects.subject_form.messagebox.showwarning")
    @patch(
        "ui.subjects.subject_form.create_subject",
        side_effect=ValueError("Subject name is required."),
    )
    def test_03_display_validation_error(
        self,
        mock_create,
        mock_warning,
    ):
        form = SubjectForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.subject_code_var.set("MATH")
        form.save_subject()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    @patch("ui.subjects.subject_form.messagebox.showerror")
    @patch(
        "ui.subjects.subject_form.create_subject",
        side_effect=RuntimeError("Database unavailable."),
    )
    def test_04_display_unexpected_error(
        self,
        mock_create,
        mock_error,
    ):
        form = SubjectForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.subject_code_var.set("MATH")
        form.name_var.set("Mathematics")
        form.save_subject()

        mock_create.assert_called_once()
        mock_error.assert_called_once()

    def test_05_create_form_status_is_disabled(self):
        form = SubjectForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        self.assertEqual(
            str(form.status_box["state"]),
            "disabled",
        )

    def test_06_clear_create_form(self):
        form = SubjectForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.subject_code_var.set("MATH")
        form.name_var.set("Mathematics")
        form.description_text.insert("1.0", "Description")

        form.clear_form()

        self.assertEqual(form.subject_code_var.get(), "")
        self.assertEqual(form.name_var.get(), "")
        self.assertEqual(
            form.description_text.get("1.0", "end-1c"),
            "",
        )
        self.assertEqual(form.status_var.get(), "active")

    def test_07_clear_edit_form_preserves_status(self):
        form = SubjectForm(
            self.frame,
            user=self.user,
            subject={
                **SAMPLE_SUBJECT,
                "status": "inactive",
            },
        )
        form.pack(fill="both", expand=True)

        form.clear_form()

        self.assertEqual(form.subject_code_var.get(), "")
        self.assertEqual(form.name_var.get(), "")
        self.assertEqual(form.status_var.get(), "inactive")

    def test_08_form_back_callback(self):
        on_back = Mock()

        form = SubjectForm(
            self.frame,
            user=self.user,
            on_back=on_back,
        )
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()

    # --------------------------------------------------
    # LIST TESTS
    # --------------------------------------------------

    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_09_list_displays_subjects(self, mock_subjects):
        list_frame = SubjectListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock(),
        )
        list_frame.pack(fill="both", expand=True)

        rows = list_frame.tree.get_children()

        self.assertEqual(len(rows), 2)

        first = list_frame.tree.item(rows[0], "values")
        second = list_frame.tree.item(rows[1], "values")

        self.assertEqual(first[0], "1")
        self.assertEqual(first[1], "MATH")
        self.assertEqual(first[2], "Mathematics")
        self.assertEqual(first[4], "Active")

        self.assertEqual(second[0], "2")
        self.assertEqual(second[1], "SCI")
        self.assertEqual(second[4], "Inactive")

        mock_subjects.assert_called_once_with(
            search="",
            status=None,
            actor_user_id=1,
        )

    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_10_search_and_filter_by_status(self, mock_subjects):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("Math")
        list_frame.status_var.set("Active")

        list_frame.load_subjects()

        mock_subjects.assert_called_with(
            search="Math",
            status="active",
            actor_user_id=1,
        )

    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_11_reset_search_and_status(self, mock_subjects):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("Math")
        list_frame.status_var.set("Inactive")

        list_frame.reset_filters()

        self.assertEqual(list_frame.search_var.get(), "")
        self.assertEqual(list_frame.status_var.get(), "All")

        mock_subjects.assert_called_with(
            search="",
            status=None,
            actor_user_id=1,
        )

    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_12_edit_selected_subject(self, mock_subjects):
        on_edit = Mock()

        list_frame = SubjectListFrame(
            self.frame,
            user=self.user,
            on_edit=on_edit,
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.edit_selected()

        on_edit.assert_called_once_with(1)

    @patch(
        "ui.subjects.subject_list.messagebox.showwarning"
    )
    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=[],
    )
    def test_13_reject_edit_without_selection(
        self,
        mock_subjects,
        mock_warning,
    ):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        self.assertIsNone(
            list_frame.get_selected_subject_id()
        )

        mock_warning.assert_called_once()

    @patch(
        "ui.subjects.subject_list.messagebox.showinfo"
    )
    @patch(
        "ui.subjects.subject_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.subjects.subject_list.update_subject_status"
    )
    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_14_deactivate_selected_subject(
        self,
        mock_subjects,
        mock_update_status,
        mock_confirm,
        mock_message,
    ):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("inactive")

        mock_confirm.assert_called_once()
        mock_update_status.assert_called_once_with(1, "inactive", actor_user_id=1)
        mock_message.assert_called_once()

    @patch(
        "ui.subjects.subject_list.messagebox.showwarning"
    )
    @patch(
        "ui.subjects.subject_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.subjects.subject_list.update_subject_status",
        side_effect=ValueError(
            "Cannot deactivate a subject with active assignments."
        ),
    )
    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_15_handle_status_change_validation_error(
        self,
        mock_subjects,
        mock_update_status,
        mock_confirm,
        mock_warning,
    ):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("inactive")

        mock_update_status.assert_called_once_with(1, "inactive", actor_user_id=1)
        mock_warning.assert_called_once()

    @patch(
        "ui.subjects.subject_list.messagebox.askyesno",
        return_value=False,
    )
    @patch(
        "ui.subjects.subject_list.update_subject_status"
    )
    @patch(
        "ui.subjects.subject_list.get_subjects",
        return_value=SAMPLE_SUBJECTS,
    )
    def test_16_cancel_status_change(
        self,
        mock_subjects,
        mock_update_status,
        mock_confirm,
    ):
        list_frame = SubjectListFrame(self.frame,
            user=self.user,)
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status("inactive")

        mock_confirm.assert_called_once()
        mock_update_status.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
