import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.sections.section_form import SectionForm
from ui.sections.section_list import SectionListFrame


SAMPLE_CLASSES = [
    {"id": 1, "name": "Grade 1", "description": None},
    {"id": 2, "name": "Grade 2", "description": None},
]

SAMPLE_SECTION = {
    "id": 101,
    "class_id": 1,
    "name": "A",
    "class_name": "Grade 1",
}


class SectionUITests(unittest.TestCase):

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

    @patch(
        "ui.sections.section_form.messagebox.showinfo"
    )
    @patch(
        "ui.sections.section_form.create_section",
        return_value=101
    )
    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_01_create_section(
        self,
        mock_classes,
        mock_create,
        mock_message
    ):
        on_saved = Mock()

        form = SectionForm(
            self.frame,
            user=self.user,
            on_saved=on_saved
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            tuple(form.class_box["values"]),
            ("1 - Grade 1", "2 - Grade 2")
        )

        form.class_var.set("1 - Grade 1")
        form.name_var.set("A")
        form.save_section()

        mock_create.assert_called_once_with({
            "class_id": 1,
            "name": "A",
        }, actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch(
        "ui.sections.section_form.messagebox.showinfo"
    )
    @patch(
        "ui.sections.section_form.update_section"
    )
    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_02_edit_section(
        self,
        mock_classes,
        mock_update,
        mock_message
    ):
        on_saved = Mock()

        form = SectionForm(
            self.frame,
            user=self.user,
            on_saved=on_saved,
            section=SAMPLE_SECTION
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.class_var.get(),
            "1 - Grade 1"
        )

        self.assertEqual(form.name_var.get(), "A")

        form.class_var.set("2 - Grade 2")
        form.name_var.set("B")
        form.save_section()

        mock_update.assert_called_once_with(
            101,
            {
                "class_id": 2,
                "name": "B",
            }
        , actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch(
        "ui.sections.section_form.messagebox.showwarning"
    )
    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_03_require_class_selection(
        self,
        mock_classes,
        mock_warning
    ):
        form = SectionForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.name_var.set("A")
        form.class_var.set("")

        with patch(
            "ui.sections.section_form.create_section"
        ) as mock_create:
            form.save_section()

        mock_create.assert_not_called()
        mock_warning.assert_called_once()

    @patch(
        "ui.sections.section_form.messagebox.showwarning"
    )
    @patch(
        "ui.sections.section_form.get_classes",
        return_value=[]
    )
    def test_04_handle_no_available_classes(
        self,
        mock_classes,
        mock_warning
    ):
        form = SectionForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        self.assertEqual(
            tuple(form.class_box["values"]),
            ()
        )

        form.name_var.set("A")
        form.save_section()

        mock_warning.assert_called_once()

    @patch(
        "ui.sections.section_form.messagebox.showwarning"
    )
    @patch(
        "ui.sections.section_form.create_section",
        side_effect=ValueError("Section name is required.")
    )
    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_05_display_validation_error(
        self,
        mock_classes,
        mock_create,
        mock_warning
    ):
        form = SectionForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.class_var.set("1 - Grade 1")
        form.save_section()

        mock_create.assert_called_once()
        mock_warning.assert_called_once()

    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_06_clear_form(self, mock_classes):
        form = SectionForm(self.frame,
            user=self.user,)
        form.pack(fill="both", expand=True)

        form.class_var.set("1 - Grade 1")
        form.name_var.set("Section A")

        form.clear_form()

        self.assertEqual(form.class_var.get(), "")
        self.assertEqual(form.name_var.get(), "")

    @patch(
        "ui.sections.section_form.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_07_form_back_callback(self, mock_classes):
        on_back = Mock()

        form = SectionForm(
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
        "ui.sections.section_list.get_sections",
        return_value=[SAMPLE_SECTION]
    )
    @patch(
        "ui.sections.section_list.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_08_list_displays_sections(
        self,
        mock_classes,
        mock_sections
    ):
        list_frame = SectionListFrame(
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
        self.assertEqual(values[1], "A")
        self.assertEqual(values[2], "Grade 1")

        mock_sections.assert_called_once_with(
            search="",
            class_id=None
        , actor_user_id=1)

    @patch(
        "ui.sections.section_list.get_sections",
        return_value=[SAMPLE_SECTION]
    )
    @patch(
        "ui.sections.section_list.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_09_search_and_filter_by_class(
        self,
        mock_classes,
        mock_sections
    ):
        list_frame = SectionListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("Section")
        list_frame.class_filter_var.set("2 - Grade 2")

        list_frame.load_sections()

        mock_sections.assert_called_with(
            search="Section",
            class_id=2
        , actor_user_id=1)

    @patch(
        "ui.sections.section_list.get_sections",
        return_value=[SAMPLE_SECTION]
    )
    @patch(
        "ui.sections.section_list.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_10_clear_search_and_class_filter(
        self,
        mock_classes,
        mock_sections
    ):
        list_frame = SectionListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("Section")
        list_frame.class_filter_var.set("2 - Grade 2")

        list_frame.clear_search()

        self.assertEqual(list_frame.search_var.get(), "")
        self.assertEqual(
            list_frame.class_filter_var.get(),
            "All Classes"
        )

        mock_sections.assert_called_with(
            search="",
            class_id=None
        , actor_user_id=1)

    @patch(
        "ui.sections.section_list.get_sections",
        return_value=[SAMPLE_SECTION]
    )
    @patch(
        "ui.sections.section_list.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_11_edit_selected_section(
        self,
        mock_classes,
        mock_sections
    ):
        on_edit = Mock()

        list_frame = SectionListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=on_edit
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.edit_section()

        on_edit.assert_called_once_with(101)

    @patch(
        "ui.sections.section_list.messagebox.showwarning"
    )
    @patch(
        "ui.sections.section_list.get_sections",
        return_value=[]
    )
    @patch(
        "ui.sections.section_list.get_classes",
        return_value=SAMPLE_CLASSES
    )
    def test_12_reject_edit_without_selection(
        self,
        mock_classes,
        mock_sections,
        mock_warning
    ):
        list_frame = SectionListFrame(
            self.frame,
            user=self.user,
            on_create=Mock(),
            on_edit=Mock()
        )
        list_frame.pack(fill="both", expand=True)

        self.assertIsNone(
            list_frame.get_selected_section_id()
        )

        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
