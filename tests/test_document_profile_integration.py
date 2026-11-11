import tkinter as tk
import unittest
from unittest.mock import patch

from ui.students.student_profile import StudentProfile
from ui.teachers.teacher_profile import TeacherProfile
from ui.transport.staff_profile import TransportStaffProfile


class DocumentProfileIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.update_idletasks()
            cls.root.update()
        finally:
            cls.root.destroy()

    def setUp(self):
        self.user = {"id": 1, "username": "admin", "role": "admin"}
        self.back_called = False
        self.edit_called = False

    def on_back(self):
        self.back_called = True

    def on_edit(self):
        self.edit_called = True

    def tab_texts(self, profile):
        notebook = next(
            widget
            for widget in profile.winfo_children()
            if isinstance(widget, tk.ttk.Notebook)
        )
        return [
            notebook.tab(tab_id, "text")
            for tab_id in notebook.tabs()
        ]

    def buttons(self, widget):
        found = []

        for child in widget.winfo_children():
            if isinstance(child, tk.ttk.Button):
                found.append(child)
            found.extend(self.buttons(child))

        return found

    def test_student_profile_integrates_document_panel(self):
        student = {"id": 101, "first_name": "Test", "last_name": "Student"}

        with patch(
            "ui.students.student_profile.DocumentPanel"
        ) as panel:
            profile = StudentProfile(
                self.root,
                student,
                self.on_back,
                self.on_edit,
                user=self.user,
            )

            self.assertEqual(
                self.tab_texts(profile),
                ["Information", "Documents"],
            )

            panel.assert_called_once()
            args, kwargs = panel.call_args

            self.assertEqual(kwargs["owner_type"], "student")
            self.assertEqual(kwargs["owner_id"], 101)
            self.assertEqual(kwargs["user"], self.user)
            panel.return_value.pack.assert_called_once_with(
                fill="both",
                expand=True,
            )

            profile.destroy()

    def test_teacher_profile_integrates_document_panel(self):
        teacher = {"id": 202, "first_name": "Test", "last_name": "Teacher"}

        with patch(
            "ui.teachers.teacher_profile.DocumentPanel"
        ) as panel:
            profile = TeacherProfile(
                self.root,
                teacher,
                self.on_back,
                self.on_edit,
                user=self.user,
            )

            self.assertEqual(
                self.tab_texts(profile),
                ["Information", "Documents"],
            )

            panel.assert_called_once()
            _, kwargs = panel.call_args

            self.assertEqual(kwargs["owner_type"], "teacher")
            self.assertEqual(kwargs["owner_id"], 202)
            self.assertEqual(kwargs["user"], self.user)

            profile.destroy()

    def test_transport_staff_profile_integrates_document_panel(self):
        staff = {"id": 303, "first_name": "Test", "last_name": "Driver"}

        with patch(
            "ui.transport.staff_profile.DocumentPanel"
        ) as panel:
            profile = TransportStaffProfile(
                self.root,
                staff,
                self.on_back,
                self.on_edit,
                user=self.user,
            )

            self.assertEqual(
                self.tab_texts(profile),
                ["Information", "Documents"],
            )

            panel.assert_called_once()
            _, kwargs = panel.call_args

            self.assertEqual(kwargs["owner_type"], "transport_staff")
            self.assertEqual(kwargs["owner_id"], 303)
            self.assertEqual(kwargs["user"], self.user)

            profile.destroy()

    def test_profiles_remain_compatible_without_user(self):
        profiles = [
            (
                StudentProfile,
                {"id": 101, "first_name": "Test"},
                "ui.students.student_profile.DocumentPanel",
            ),
            (
                TeacherProfile,
                {"id": 202, "first_name": "Test"},
                "ui.teachers.teacher_profile.DocumentPanel",
            ),
            (
                TransportStaffProfile,
                {"id": 303, "first_name": "Test"},
                "ui.transport.staff_profile.DocumentPanel",
            ),
        ]

        for profile_class, record, panel_path in profiles:
            with self.subTest(profile=profile_class.__name__):
                with patch(panel_path) as panel:
                    profile = profile_class(
                        self.root,
                        record,
                        self.on_back,
                        self.on_edit,
                    )

                    self.assertIsNone(profile.user)
                    panel.assert_not_called()

                    self.assertEqual(
                        self.tab_texts(profile),
                        ["Information", "Documents"],
                    )

                    profile.destroy()

    def test_student_profile_keeps_back_and_edit_buttons(self):
        profile = StudentProfile(
            self.root,
            {"id": 101, "first_name": "Test"},
            self.on_back,
            self.on_edit,
        )

        buttons = self.buttons(profile)
        button_texts = [button.cget("text") for button in buttons]

        self.assertIn("Back to Records", button_texts)
        self.assertIn("Edit Student", button_texts)

        profile.destroy()

    def test_teacher_profile_keeps_back_and_edit_buttons(self):
        profile = TeacherProfile(
            self.root,
            {"id": 202, "first_name": "Test"},
            self.on_back,
            self.on_edit,
        )

        buttons = self.buttons(profile)
        button_texts = [button.cget("text") for button in buttons]

        self.assertIn("Back to Records", button_texts)
        self.assertIn("Edit Teacher", button_texts)

        profile.destroy()

    def test_transport_staff_profile_keeps_back_and_edit_buttons(self):
        profile = TransportStaffProfile(
            self.root,
            {"id": 303, "first_name": "Test"},
            self.on_back,
            self.on_edit,
        )

        buttons = self.buttons(profile)
        button_texts = [button.cget("text") for button in buttons]

        self.assertIn("Back to Staff Records", button_texts)
        self.assertIn("Edit Staff", button_texts)

        profile.destroy()


if __name__ == "__main__":
    unittest.main()
