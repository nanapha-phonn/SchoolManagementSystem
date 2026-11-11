import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.teacher_subject_assignments.assignment_list import (
    TeacherSubjectAssignmentListFrame,
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
    "employee_no": "T001",
    "teacher_name": "John Smith",
    "subject_code": "MATH",
    "subject_name": "Mathematics",
    "section_name": "A",
    "class_name": "Grade 10",
    "academic_year_name": "2026-2027",
}

SAMPLE_INACTIVE_ASSIGNMENT = {
    **SAMPLE_ASSIGNMENT,
    "status": "inactive",
    "ended_on": "2026-11-03",
}


class TeacherSubjectAssignmentUITests(unittest.TestCase):

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

        self.patches = [
            patch(
                "ui.teacher_subject_assignments.assignment_list.get_teachers",
                return_value=SAMPLE_TEACHERS,
            ),
            patch(
                "ui.teacher_subject_assignments.assignment_list.get_subjects",
                return_value=SAMPLE_SUBJECTS,
            ),
            patch(
                "ui.teacher_subject_assignments.assignment_list.get_sections",
                return_value=SAMPLE_SECTIONS,
            ),
            patch(
                "ui.teacher_subject_assignments.assignment_list.get_academic_years",
                return_value=SAMPLE_YEARS,
            ),
            patch(
                "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignments",
                return_value=[SAMPLE_ASSIGNMENT],
            ),
        ]

        self.mocks = [item.start() for item in self.patches]

        for item in self.patches:
            self.addCleanup(item.stop)

        self.root.update_idletasks()

    def tearDown(self):
        for child in self.frame.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

        self.frame.destroy()
        self.root.update_idletasks()

    def create_list(self, **kwargs):
        kwargs.setdefault("user", self.user)
        list_frame = TeacherSubjectAssignmentListFrame(
            self.frame,
            **kwargs,
        )
        list_frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        return list_frame

    # --------------------------------------------------
    # LIST AND FILTER TESTS
    # --------------------------------------------------

    def test_01_list_displays_assignments(self):
        list_frame = self.create_list()

        rows = list_frame.tree.get_children()
        self.assertEqual(len(rows), 1)

        values = list_frame.tree.item(rows[0], "values")

        self.assertEqual(values[0], "1")
        self.assertEqual(values[1], "John Smith")
        self.assertEqual(values[2], "MATH - Mathematics")
        self.assertEqual(values[3], "Grade 10")
        self.assertEqual(values[4], "A")
        self.assertEqual(values[5], "2026-2027")
        self.assertEqual(values[6], "2026-11-01")
        self.assertEqual(values[7], "")
        self.assertEqual(values[8], "Active")

        self.mocks[4].assert_called_once_with(
            search="",
            teacher_id=None,
            subject_id=None,
            section_id=None,
            academic_year_id=None,
            status=None,
            actor_user_id=self.user["id"],
        )

    def test_02_loads_reference_filter_values(self):
        list_frame = self.create_list()

        self.assertEqual(
            list(list_frame.teacher_id_by_label.values()),
            [1],
        )
        self.assertEqual(
            list(list_frame.subject_id_by_label.values()),
            [1],
        )
        self.assertEqual(
            list(list_frame.section_id_by_label.values()),
            [1],
        )
        self.assertEqual(
            list(list_frame.year_id_by_label.values()),
            [1],
        )

    def test_03_search_and_all_filters(self):
        list_frame = self.create_list()

        list_frame.search_var.set("Mathematics")
        list_frame.teacher_var.set("T001 - John Smith")
        list_frame.subject_var.set("MATH - Mathematics")
        list_frame.section_var.set("Grade 10 - A")
        list_frame.year_var.set("2026-2027 (Current)")
        list_frame.status_var.set("Active")

        list_frame.load_assignments()

        self.mocks[4].assert_called_with(
            search="Mathematics",
            teacher_id=1,
            subject_id=1,
            section_id=1,
            academic_year_id=1,
            status="active",
            actor_user_id=self.user["id"],
        )

    def test_04_reset_filters(self):
        list_frame = self.create_list()

        list_frame.search_var.set("Math")
        list_frame.teacher_var.set("T001 - John Smith")
        list_frame.subject_var.set("MATH - Mathematics")
        list_frame.section_var.set("Grade 10 - A")
        list_frame.year_var.set("2026-2027 (Current)")
        list_frame.status_var.set("Active")

        list_frame.reset_filters()

        self.assertEqual(list_frame.search_var.get(), "")
        self.assertEqual(list_frame.teacher_var.get(), "All")
        self.assertEqual(list_frame.subject_var.get(), "All")
        self.assertEqual(list_frame.section_var.get(), "All")
        self.assertEqual(list_frame.year_var.get(), "All")
        self.assertEqual(list_frame.status_var.get(), "All")

        self.mocks[4].assert_called_with(
            search="",
            teacher_id=None,
            subject_id=None,
            section_id=None,
            academic_year_id=None,
            status=None,
            actor_user_id=self.user["id"],
        )

    def test_05_empty_assignment_list(self):
        self.mocks[4].return_value = []

        list_frame = self.create_list()

        self.assertEqual(
            len(list_frame.tree.get_children()),
            0,
        )

    def test_06_empty_reference_data(self):
        self.mocks[0].return_value = []
        self.mocks[1].return_value = []
        self.mocks[2].return_value = []
        self.mocks[3].return_value = []
        self.mocks[4].return_value = []

        list_frame = self.create_list()

        self.assertEqual(list_frame.teacher_id_by_label, {})
        self.assertEqual(list_frame.subject_id_by_label, {})
        self.assertEqual(list_frame.section_id_by_label, {})
        self.assertEqual(list_frame.year_id_by_label, {})
        self.assertEqual(len(list_frame.tree.get_children()), 0)

    # --------------------------------------------------
    # SELECTION AND NAVIGATION
    # --------------------------------------------------

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showwarning"
    )
    def test_07_reject_selection_when_nothing_selected(
        self,
        mock_warning,
    ):
        list_frame = self.create_list()

        self.assertIsNone(
            list_frame.get_selected_assignment_id()
        )

        mock_warning.assert_called_once()

    def test_08_create_assignment_callback(self):
        on_create = Mock()
        list_frame = self.create_list(on_create=on_create)

        list_frame.create_assignment()

        on_create.assert_called_once()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_ASSIGNMENT,
    )
    def test_09_reassign_active_assignment(
        self,
        mock_get_assignment,
    ):
        on_reassign = Mock()
        list_frame = self.create_list(on_reassign=on_reassign)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.reassign_selected_assignment()

        mock_get_assignment.assert_called_once_with(
            1, actor_user_id=self.user["id"]
        )
        on_reassign.assert_called_once_with(1)

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showwarning"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_INACTIVE_ASSIGNMENT,
    )
    def test_10_reject_reassignment_of_inactive_assignment(
        self,
        mock_get_assignment,
        mock_warning,
    ):
        on_reassign = Mock()
        list_frame = self.create_list(on_reassign=on_reassign)

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.reassign_selected_assignment()

        mock_get_assignment.assert_called_once_with(
            1, actor_user_id=self.user["id"]
        )
        mock_warning.assert_called_once()
        on_reassign.assert_not_called()

    # --------------------------------------------------
    # END ASSIGNMENT TESTS
    # --------------------------------------------------

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showinfo"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.simpledialog.askstring",
        return_value="2026-11-04",
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.end_teacher_subject_assignment"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_ASSIGNMENT,
    )
    def test_11_end_active_assignment(
        self,
        mock_get_assignment,
        mock_end,
        mock_date,
        mock_confirm,
        mock_message,
    ):
        list_frame = self.create_list()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.end_selected_assignment()

        mock_get_assignment.assert_called_once_with(
            1, actor_user_id=self.user["id"]
        )
        mock_date.assert_called_once()
        mock_confirm.assert_called_once()
        mock_end.assert_called_once_with(
            1, "2026-11-04", actor_user_id=self.user["id"]
        )
        mock_message.assert_called_once()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showwarning"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_INACTIVE_ASSIGNMENT,
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.simpledialog.askstring"
    )
    def test_12_reject_ending_inactive_assignment(
        self,
        mock_date,
        mock_get_assignment,
        mock_warning,
    ):
        list_frame = self.create_list()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.end_selected_assignment()

        mock_get_assignment.assert_called_once_with(
            1, actor_user_id=self.user["id"]
        )
        mock_warning.assert_called_once()
        mock_date.assert_not_called()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.askyesno",
        return_value=False,
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.simpledialog.askstring",
        return_value="2026-11-04",
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.end_teacher_subject_assignment"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_ASSIGNMENT,
    )
    def test_13_cancel_ending_assignment(
        self,
        mock_get_assignment,
        mock_end,
        mock_date,
        mock_confirm,
    ):
        list_frame = self.create_list()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.end_selected_assignment()

        mock_confirm.assert_called_once()
        mock_end.assert_not_called()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showwarning"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.askyesno",
        return_value=True,
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.simpledialog.askstring",
        return_value="2026-11-04",
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.end_teacher_subject_assignment",
        side_effect=ValueError("End date cannot be before assignment date."),
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=SAMPLE_ASSIGNMENT,
    )
    def test_14_handle_end_assignment_validation_error(
        self,
        mock_get_assignment,
        mock_end,
        mock_date,
        mock_confirm,
        mock_warning,
    ):
        list_frame = self.create_list()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        list_frame.end_selected_assignment()

        mock_end.assert_called_once_with(
            1, "2026-11-04", actor_user_id=self.user["id"]
        )
        mock_warning.assert_called_once()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showerror"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignments",
        side_effect=RuntimeError("Database unavailable."),
    )
    def test_15_handle_assignment_loading_error(
        self,
        mock_get_assignments,
        mock_error,
    ):
        list_frame = self.create_list()

        mock_get_assignments.assert_called_once()
        self.assertEqual(
            mock_get_assignments.call_args.kwargs["actor_user_id"],
            self.user["id"],
        )
        mock_error.assert_called_once()

    @patch(
        "ui.teacher_subject_assignments.assignment_list.messagebox.showwarning"
    )
    @patch(
        "ui.teacher_subject_assignments.assignment_list.get_teacher_subject_assignment",
        return_value=None,
    )
    def test_16_handle_missing_selected_assignment(
        self,
        mock_get_assignment,
        mock_warning,
    ):
        list_frame = self.create_list()

        row = list_frame.tree.get_children()[0]
        list_frame.tree.selection_set(row)

        self.assertIsNone(
            list_frame.get_selected_assignment()
        )

        mock_get_assignment.assert_called_once_with(
            1, actor_user_id=self.user["id"]
        )
        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
