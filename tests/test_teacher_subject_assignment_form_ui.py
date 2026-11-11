import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

from ui.teacher_subject_assignments.assignment_form import (
    TeacherSubjectAssignmentForm,
)


SAMPLE_TEACHERS = [
    {
        "id": 1,
        "employee_no": "T001",
        "first_name": "John",
        "last_name": "Smith",
        "status": "active",
    },
]

SAMPLE_SUBJECTS = [
    {
        "id": 1,
        "subject_code": "MATH",
        "name": "Mathematics",
        "status": "active",
    },
]

SAMPLE_SECTIONS = [
    {
        "id": 1,
        "class_id": 1,
        "class_name": "Grade 10",
        "name": "A",
    },
]

SAMPLE_YEARS = [
    {
        "id": 1,
        "name": "2026-2027",
        "is_current": 1,
    },
]

SAMPLE_ASSIGNMENT = {
    "id": 1,
    "teacher_id": 1,
    "subject_id": 1,
    "section_id": 1,
    "academic_year_id": 1,
    "assigned_on": "2026-11-01",
    "ended_on": None,
    "status": "active",
}


class TeacherSubjectAssignmentFormUITests(unittest.TestCase):

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
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.reference_patches = {
            "teachers": patch(
                "ui.teacher_subject_assignments.assignment_form.get_teachers",
                return_value=SAMPLE_TEACHERS,
            ),
            "subjects": patch(
                "ui.teacher_subject_assignments.assignment_form.get_subjects",
                return_value=SAMPLE_SUBJECTS,
            ),
            "sections": patch(
                "ui.teacher_subject_assignments.assignment_form.get_sections",
                return_value=SAMPLE_SECTIONS,
            ),
            "years": patch(
                "ui.teacher_subject_assignments.assignment_form.get_academic_years",
                return_value=SAMPLE_YEARS,
            ),
        }

        self.reference_mocks = {
            name: mocked.start()
            for name, mocked in self.reference_patches.items()
        }

        for mocked in self.reference_patches.values():
            self.addCleanup(mocked.stop)

    def tearDown(self):
        for child in self.container.winfo_children():
            child.destroy()

        self.container.destroy()
        self.root.update_idletasks()

    def create_form(self, **kwargs):
        kwargs.setdefault("user", self.user)
        form = TeacherSubjectAssignmentForm(
            self.container,
            **kwargs,
        )
        form.pack(fill="both", expand=True)
        self.root.update_idletasks()
        return form

    @staticmethod
    def get_all_labels(widget):
        labels = []

        for child in widget.winfo_children():
            if isinstance(child, ttk.Label):
                labels.append(child)

            labels.extend(
                TeacherSubjectAssignmentFormUITests.get_all_labels(
                    child
                )
            )

        return labels

    def test_01_missing_sections_disables_save_and_displays_warning(self):
        self.reference_mocks["sections"].return_value = []

        form = self.create_form()

        self.assertTrue(form.save_button.instate(["disabled"]))

        label_texts = [
            label.cget("text")
            for label in self.get_all_labels(form)
        ]

        self.assertTrue(
            any(
                "No class sections are available" in text
                for text in label_texts
            )
        )

    def test_02_missing_teachers_disables_save(self):
        self.reference_mocks["teachers"].return_value = []

        form = self.create_form()

        self.assertTrue(form.save_button.instate(["disabled"]))
        self.assertIn(
            "active teachers",
            form.get_missing_reference_data(),
        )

    def test_03_missing_subjects_disables_save(self):
        self.reference_mocks["subjects"].return_value = []

        form = self.create_form()

        self.assertTrue(form.save_button.instate(["disabled"]))
        self.assertIn(
            "active subjects",
            form.get_missing_reference_data(),
        )

    def test_04_missing_academic_years_disables_save(self):
        self.reference_mocks["years"].return_value = []

        form = self.create_form()

        self.assertTrue(form.save_button.instate(["disabled"]))
        self.assertIn(
            "academic years",
            form.get_missing_reference_data(),
        )

    def test_05_complete_reference_data_keeps_save_enabled(self):
        form = self.create_form()

        self.assertFalse(form.get_missing_reference_data())
        self.assertTrue(form.save_button.instate(["!disabled"]))

    @patch(
        "ui.teacher_subject_assignments.assignment_form.create_teacher_subject_assignment"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_form.messagebox.showwarning"
    )
    def test_06_save_rejects_missing_reference_data(
        self,
        mock_warning,
        mock_create,
    ):
        self.reference_mocks["sections"].return_value = []

        form = self.create_form()
        form.save_assignment()

        mock_warning.assert_called_once()
        self.assertEqual(
            mock_warning.call_args.args[0],
            "Reference Data Missing",
        )
        mock_create.assert_not_called()

    def test_07_reassignment_is_not_blocked_by_missing_sections(self):
        self.reference_mocks["sections"].return_value = []

        form = self.create_form(
            assignment=SAMPLE_ASSIGNMENT,
            reassign=True,
        )

        self.assertTrue(form.reassign)
        self.assertTrue(form.save_button.instate(["!disabled"]))
        self.assertEqual(
            str(form.teacher_combo.cget("state")),
            "readonly",
        )
        self.assertEqual(
            str(form.subject_combo.cget("state")),
            "disabled",
        )
        self.assertEqual(
            str(form.section_combo.cget("state")),
            "disabled",
        )
        self.assertEqual(
            str(form.year_combo.cget("state")),
            "disabled",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
