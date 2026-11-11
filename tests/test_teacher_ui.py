import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.teachers.teacher_form import TeacherForm
from ui.teachers.teacher_list import TeacherListFrame
from ui.teachers.teacher_profile import TeacherProfile


SAMPLE_TEACHER = {
    "id": 101,
    "employee_no": "EMP-TEST-001",
    "first_name": "John",
    "last_name": "Smith",
    "date_of_birth": "1990-05-15",
    "gender": "Male",
    "phone": "0123456789",
    "email": "john@example.com",
    "address": "Phnom Penh",
    "qualification": "Bachelor Degree",
    "specialization": "Mathematics",
    "department": "Science",
    "employment_date": "2020-01-10",
    "status": "active",
    "created_at": "2026-11-02 10:00:00",
}


def find_widgets(parent, widget_type):
    """Recursively find widgets of a particular type."""
    found = []

    for child in parent.winfo_children():
        if isinstance(child, widget_type):
            found.append(child)

        found.extend(find_widgets(child, widget_type))

    return found


def find_button(parent, button_text):
    """Find a ttk button by its displayed text."""
    for button in find_widgets(parent, ttk.Button):
        if button.cget("text") == button_text:
            return button

    raise AssertionError(
        f"Button not found: {button_text}"
    )


class TeacherUITests(unittest.TestCase):

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
        try:
            cls.root.update_idletasks()
            cls.root.update()
        finally:
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
    # TEACHER FORM TESTS
    # --------------------------------------------------

    @patch("ui.teachers.teacher_form.messagebox.showinfo")
    @patch("ui.teachers.teacher_form.create_teacher", return_value=101)
    def test_teacher_registration(self, mock_create, mock_message):
        on_saved = Mock()

        form = TeacherForm(
            self.frame,
            on_saved=on_saved,
        user=self.user,
        )
        form.pack(fill="both", expand=True)

        form.variables["employee_no"].set("EMP-TEST-001")
        form.variables["first_name"].set("John")
        form.variables["last_name"].set("Smith")
        form.variables["department"].set("Science")

        form.save_teacher()

        mock_create.assert_called_once()
        self.assertEqual(
            mock_create.call_args.kwargs["actor_user_id"],
            self.user["id"],
        )

        saved_data = mock_create.call_args[0][0]

        self.assertEqual(
            saved_data["employee_no"],
            "EMP-TEST-001"
        )
        self.assertEqual(saved_data["first_name"], "John")
        self.assertEqual(saved_data["last_name"], "Smith")
        self.assertEqual(saved_data["status"], "active")

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.teachers.teacher_form.messagebox.showinfo")
    @patch("ui.teachers.teacher_form.update_teacher")
    def test_teacher_editing(self, mock_update, mock_message):
        on_saved = Mock()

        form = TeacherForm(
            self.frame,
            on_saved=on_saved,
            teacher=SAMPLE_TEACHER,
        user=self.user,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.variables["employee_no"].get(),
            "EMP-TEST-001"
        )

        form.variables["first_name"].set("Updated")
        form.save_teacher()

        mock_update.assert_called_once()
        self.assertEqual(
            mock_update.call_args.kwargs["actor_user_id"],
            self.user["id"],
        )

        teacher_id = mock_update.call_args[0][0]
        teacher_data = mock_update.call_args[0][1]

        self.assertEqual(teacher_id, 101)
        self.assertEqual(teacher_data["first_name"], "Updated")

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    def test_teacher_form_clear(self):
        form = TeacherForm(self.frame, user=self.user)
        form.pack(fill="both", expand=True)

        form.variables["employee_no"].set("EMP-TEST-001")
        form.variables["first_name"].set("John")
        form.address_text.insert("1.0", "Phnom Penh")

        form.clear_form()

        self.assertEqual(
            form.variables["employee_no"].get(),
            ""
        )
        self.assertEqual(
            form.variables["first_name"].get(),
            ""
        )
        self.assertEqual(
            form.variables["status"].get(),
            "active"
        )
        self.assertEqual(
            form.address_text.get("1.0", "end").strip(),
            ""
        )

    def test_teacher_form_back_callback(self):
        on_back = Mock()

        form = TeacherForm(
            self.frame,
            on_back=on_back,
        user=self.user,
        )
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()

    # --------------------------------------------------
    # TEACHER LIST TESTS
    # --------------------------------------------------

    @patch(
        "ui.teachers.teacher_list.get_teachers",
        return_value=[SAMPLE_TEACHER]
    )
    def test_teacher_list_display(self, mock_get):
        list_frame = TeacherListFrame(
            self.frame,
            on_register=Mock(),
            on_profile=Mock(),
            on_edit=Mock(),
        user=self.user,
        )
        list_frame.pack(fill="both", expand=True)

        rows = list_frame.tree.get_children()

        self.assertEqual(len(rows), 1)

        values = list_frame.tree.item(rows[0], "values")

        self.assertEqual(values[0], "101")
        self.assertEqual(values[1], "EMP-TEST-001")
        self.assertEqual(values[2], "John Smith")
        self.assertEqual(values[3], "Science")
        self.assertEqual(values[5], "active")

        mock_get.assert_called_once_with("", actor_user_id=self.user["id"])

    @patch(
        "ui.teachers.teacher_list.get_teachers",
        return_value=[SAMPLE_TEACHER]
    )
    def test_teacher_search(self, mock_get):
        list_frame = TeacherListFrame(
            self.frame,
            on_register=Mock(),
            on_profile=Mock(),
            on_edit=Mock(),
        user=self.user,
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("EMP-TEST-001")
        list_frame.load_teachers()

        mock_get.assert_called_with("EMP-TEST-001", actor_user_id=self.user["id"])

        list_frame.clear_search()

        self.assertEqual(list_frame.search_var.get(), "")
        mock_get.assert_called_with("", actor_user_id=self.user["id"])

    @patch(
        "ui.teachers.teacher_list.get_teachers",
        return_value=[SAMPLE_TEACHER]
    )
    def test_teacher_profile_and_edit_callbacks(self, mock_get):
        on_profile = Mock()
        on_edit = Mock()

        list_frame = TeacherListFrame(
            self.frame,
            on_register=Mock(),
            on_profile=on_profile,
            on_edit=on_edit,
        user=self.user,
        )
        list_frame.pack(fill="both", expand=True)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.view_profile()
        on_profile.assert_called_once_with(101)

        list_frame.edit_teacher()
        on_edit.assert_called_once_with(101)

    # --------------------------------------------------
    # TEACHER PROFILE TESTS
    # --------------------------------------------------

    def test_teacher_profile_display(self):
        on_back = Mock()
        on_edit = Mock()

        profile = TeacherProfile(
            self.frame,
            teacher=SAMPLE_TEACHER,
            on_back=on_back,
            on_edit=on_edit
        )
        profile.pack(fill="both", expand=True)

        labels = [
            widget.cget("text")
            for widget in find_widgets(profile, ttk.Label)
        ]

        self.assertIn("Teacher Profile", labels)
        self.assertIn("John", labels)
        self.assertIn("Smith", labels)
        self.assertIn("EMP-TEST-001", labels)
        self.assertIn("Science", labels)

        find_button(profile, "Back to Records").invoke()
        on_back.assert_called_once()

        find_button(profile, "Edit Teacher").invoke()
        on_edit.assert_called_once()

    # --------------------------------------------------
    # TEACHER STATUS TEST
    # --------------------------------------------------

    @patch("ui.teachers.teacher_list.messagebox.showinfo")
    @patch("ui.teachers.teacher_list.update_teacher_status")
    @patch(
        "ui.teachers.teacher_list.get_teacher",
        return_value=SAMPLE_TEACHER
    )
    @patch(
        "ui.teachers.teacher_list.get_teachers",
        return_value=[SAMPLE_TEACHER]
    )
    def test_teacher_status_change(
        self,
        mock_get_teachers,
        mock_get_teacher,
        mock_update_status,
        mock_message
    ):
        list_frame = TeacherListFrame(
            self.frame,
            on_register=Mock(),
            on_profile=Mock(),
            on_edit=Mock(),
        user=self.user,
        )
        self.root.deiconify()
        self.root.update()

        list_frame.pack(fill="both", expand=True)
        self.root.update()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.change_status()
        self.root.update()

        dialogs = find_widgets(list_frame, tk.Toplevel)

        self.assertEqual(len(dialogs), 1)

        dialog = dialogs[0]

        status_boxes = find_widgets(dialog, ttk.Combobox)
        self.assertEqual(len(status_boxes), 1)

        status_boxes[0].set("resigned")

        find_button(dialog, "Save").invoke()
        self.root.update()

        mock_update_status.assert_called_once_with(
            101,
            "resigned",
            actor_user_id=self.user["id"],
        )

        mock_message.assert_called_once()

        self.assertEqual(
            len(find_widgets(list_frame, tk.Toplevel)),
            0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
