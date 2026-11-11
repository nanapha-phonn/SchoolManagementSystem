import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.classes.class_form import ClassForm
from ui.classes.class_list import ClassListFrame


SAMPLE_CLASS = {
    "id": 101,
    "name": "Grade 1",
    "description": "First grade students",
}


def find_widgets(parent, widget_type):
    found = []

    for child in parent.winfo_children():
        if isinstance(child, widget_type):
            found.append(child)

        found.extend(find_widgets(child, widget_type))

    return found


class ClassUITests(unittest.TestCase):

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

    @patch("ui.classes.class_form.messagebox.showinfo")
    @patch(
        "ui.classes.class_form.create_class",
        return_value=101
    )
    def test_01_create_class(self, mock_create, mock_message):
        on_saved = Mock()

        form = ClassForm(
            self.frame,
            user=self.user,
            on_saved=on_saved
        )
        form.pack(fill="both", expand=True)

        form.name_var.set("Grade 1")
        form.description_text.insert(
            "1.0",
            "First grade students"
        )

        form.save_class()

        mock_create.assert_called_once_with({
            "name": "Grade 1",
            "description": "First grade students",
        }, actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.classes.class_form.messagebox.showinfo")
    @patch("ui.classes.class_form.update_class")
    def test_02_edit_class(self, mock_update, mock_message):
        on_saved = Mock()

        form = ClassForm(
            self.frame,
            user=self.user,
            on_saved=on_saved,
            school_class=SAMPLE_CLASS
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.name_var.get(),
            "Grade 1"
        )

        form.name_var.set("Grade 1 Updated")
        form.save_class()

        mock_update.assert_called_once_with(
            101,
            {
                "name": "Grade 1 Updated",
                "description": "First grade students",
            }
        , actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.classes.class_form.messagebox.showwarning")
    @patch(
        "ui.classes.class_form.create_class",
        side_effect=ValueError("Class name is required.")
    )
    def test_03_display_validation_error(
        self,
        mock_create,
        mock_warning
    ):
        form = ClassForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.save_class()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    def test_04_clear_form(self):
        form = ClassForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.name_var.set("Grade 1")
        form.description_text.insert("1.0", "Description")

        form.clear_form()

        self.assertEqual(form.name_var.get(), "")
        self.assertEqual(
            form.description_text.get("1.0", "end").strip(),
            ""
        )

    def test_05_form_back_callback(self):
        on_back = Mock()

        form = ClassForm(
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
        "ui.classes.class_list.get_classes",
        return_value=[SAMPLE_CLASS]
    )
    def test_06_list_displays_classes(self, mock_get):
        list_frame = ClassListFrame(
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
        self.assertEqual(values[1], "Grade 1")
        self.assertEqual(values[2], "First grade students")

        mock_get.assert_called_once_with("", actor_user_id=1)

    @patch(
        "ui.classes.class_list.get_classes",
        return_value=[SAMPLE_CLASS]
    )
    def test_07_search_and_clear(self, mock_get):
        list_frame = ClassListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("Grade")
        list_frame.load_classes()

        mock_get.assert_called_with("Grade", actor_user_id=1)

        list_frame.clear_search()

        self.assertEqual(list_frame.search_var.get(), "")
        mock_get.assert_called_with("", actor_user_id=1)

    @patch(
        "ui.classes.class_list.get_classes",
        return_value=[SAMPLE_CLASS]
    )
    def test_08_edit_selected_class(self, mock_get):
        on_edit = Mock()

        list_frame = ClassListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=on_edit
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.edit_class()

        on_edit.assert_called_once_with(101)

    @patch("ui.classes.class_list.messagebox.showwarning")
    def test_09_reject_edit_without_selection(self, mock_warning):
        list_frame = ClassListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        self.assertIsNone(
            list_frame.get_selected_class_id()
        )

        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
