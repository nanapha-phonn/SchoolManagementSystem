import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.enrollments.enrollment_form import EnrollmentForm
from ui.enrollments.enrollment_list import EnrollmentListFrame


SAMPLE_STUDENTS = [
    {
        "id": 1,
        "admission_no": "STU-001",
        "first_name": "John",
        "last_name": "Smith",
        "status": "active",
    },
    {
        "id": 2,
        "admission_no": "STU-002",
        "first_name": "Jane",
        "last_name": "Doe",
        "status": "active",
    },
    {
        "id": 3,
        "admission_no": "STU-003",
        "first_name": "Inactive",
        "last_name": "Student",
        "status": "inactive",
    },
]

SAMPLE_YEARS = [
    {
        "id": 10,
        "name": "2026-2027",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
        "is_current": 1,
    },
    {
        "id": 11,
        "name": "2027-2028",
        "start_date": "2027-09-01",
        "end_date": "2028-06-30",
        "is_current": 0,
    },
]

SAMPLE_CLASSES = [
    {"id": 20, "name": "Grade 1"},
    {"id": 21, "name": "Grade 2"},
]

SAMPLE_SECTIONS = [
    {
        "id": 30,
        "class_id": 20,
        "name": "A",
        "class_name": "Grade 1",
    },
    {
        "id": 31,
        "class_id": 20,
        "name": "B",
        "class_name": "Grade 1",
    },
]

SAMPLE_ENROLLMENT = {
    "id": 101,
    "student_id": 1,
    "section_id": 30,
    "academic_year_id": 10,
    "enrolled_on": "2026-09-01",
    "status": "enrolled",
    "admission_no": "STU-001",
    "first_name": "John",
    "last_name": "Smith",
    "student_name": "John Smith",
    "student_status": "active",
    "section_name": "A",
    "class_id": 20,
    "class_name": "Grade 1",
    "academic_year_name": "2026-2027",
    "academic_year_start": "2026-09-01",
    "academic_year_end": "2027-06-30",
}


class EnrollmentUITests(unittest.TestCase):
    TEST_USER = {"id": 1, "role": "admin"}


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

    def form_patches(self):
        return (
            patch(
                "ui.enrollments.enrollment_form.get_students",
                return_value=SAMPLE_STUDENTS
            ),
            patch(
                "ui.enrollments.enrollment_form.get_academic_years",
                return_value=SAMPLE_YEARS
            ),
            patch(
                "ui.enrollments.enrollment_form.get_classes",
                return_value=SAMPLE_CLASSES
            ),
            patch(
                "ui.enrollments.enrollment_form.get_sections",
                return_value=SAMPLE_SECTIONS
            ),
        )

    @patch("ui.enrollments.enrollment_form.messagebox.showinfo")
    @patch(
        "ui.enrollments.enrollment_form.create_enrollment",
        return_value=101
    )
    def test_01_create_enrollment(
        self,
        mock_create,
        mock_message
    ):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        on_saved = Mock()

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER,
            on_saved=on_saved
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            tuple(form.student_combo["values"]),
            (
                "STU-001 - John Smith",
                "STU-002 - Jane Doe",
            )
        )

        form.student_var.set("STU-001 - John Smith")
        form.academic_year_var.set("10 - 2026-2027 (Current)")
        form.class_var.set("20 - Grade 1")
        form.load_section_choices()
        form.section_var.set("30 - A")
        form.enrolled_on_var.set("2026-09-01")
        form.status_var.set("enrolled")

        form.save_enrollment()

        mock_create.assert_called_once_with({
            "student_id": 1,
            "section_id": 30,
            "academic_year_id": 10,
            "enrolled_on": "2026-09-01",
            "status": "enrolled",
        }, actor_user_id=1)

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showinfo")
    @patch(
        "ui.enrollments.enrollment_form.update_enrollment"
    )
    def test_02_edit_enrollment(
        self,
        mock_update,
        mock_message
    ):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        on_saved = Mock()

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER,
            on_saved=on_saved,
            enrollment=SAMPLE_ENROLLMENT
        )
        form.pack(fill="both", expand=True)

        self.assertTrue(
            form.student_combo.instate(["disabled"])
        )

        self.assertTrue(
            form.academic_year_combo.instate(["disabled"])
        )

        form.section_var.set("31 - B")
        form.enrolled_on_var.set("2026-09-10")
        form.status_var.set("completed")

        form.save_enrollment()

        mock_update.assert_called_once_with(
            101,
            {
                "section_id": 31,
                "enrolled_on": "2026-09-10",
                "status": "completed",
            },
            actor_user_id=1,
        )

        mock_message.assert_called_once()
        on_saved.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showinfo")
    @patch(
        "ui.enrollments.enrollment_form.create_enrollment",
        return_value=102
    )
    def test_03_promotion_creates_new_enrollment(
        self,
        mock_create,
        mock_message
    ):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER,
            promote_student_id=1,
            initial_class_id=20,
            initial_section_id=30,
        )
        form.pack(fill="both", expand=True)

        self.assertEqual(
            form.student_var.get(),
            "STU-001 - John Smith"
        )

        self.assertTrue(
            form.student_combo.instate(["disabled"])
        )

        self.assertEqual(
            form.academic_year_var.get(),
            ""
        )

        form.academic_year_var.set("11 - 2027-2028")
        form.section_var.set("30 - A")
        form.enrolled_on_var.set("2027-09-01")

        form.save_enrollment()

        mock_create.assert_called_once_with({
            "student_id": 1,
            "section_id": 30,
            "academic_year_id": 11,
            "enrolled_on": "2027-09-01",
            "status": "enrolled",
        }, actor_user_id=1)

        mock_message.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showwarning")
    def test_04_require_student(self, mock_warning):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.save_enrollment()

        mock_warning.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showwarning")
    def test_05_require_academic_year(self, mock_warning):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.student_var.set("STU-001 - John Smith")
        form.save_enrollment()

        mock_warning.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showwarning")
    def test_06_require_section(self, mock_warning):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.student_var.set("STU-001 - John Smith")
        form.academic_year_var.set("10 - 2026-2027 (Current)")
        form.class_var.set("20 - Grade 1")

        form.save_enrollment()

        mock_warning.assert_called_once()

    @patch("ui.enrollments.enrollment_form.messagebox.showwarning")
    def test_07_require_class(self, mock_warning):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.student_var.set("STU-001 - John Smith")
        form.academic_year_var.set("10 - 2026-2027 (Current)")

        form.save_enrollment()

        mock_warning.assert_called_once()

    @patch("ui.enrollments.enrollment_form.get_sections")
    def test_08_class_change_refreshes_sections(self, mock_get_sections):
        patches = self.form_patches()

        for item in patches[:3]:
            item.start()
            self.addCleanup(item.stop)

        mock_get_sections.return_value = SAMPLE_SECTIONS

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.class_var.set("20 - Grade 1")
        form.on_class_changed()

        mock_get_sections.assert_called_with(class_id=20, actor_user_id=1)

        self.assertEqual(
            tuple(form.section_combo["values"]),
            ("30 - A", "31 - B")
        )

    def test_09_clear_new_enrollment_form(self):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER)
        form.pack(fill="both", expand=True)

        form.student_var.set("STU-001 - John Smith")
        form.academic_year_var.set("10 - 2026-2027 (Current)")
        form.class_var.set("20 - Grade 1")
        form.section_var.set("30 - A")
        form.status_var.set("completed")

        form.clear_form()

        self.assertEqual(form.student_var.get(), "")
        self.assertEqual(form.academic_year_var.get(), "")
        self.assertEqual(form.class_var.get(), "")
        self.assertEqual(form.section_var.get(), "")
        self.assertEqual(form.status_var.get(), "enrolled")

    def test_10_form_back_callback(self):
        patches = self.form_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        on_back = Mock()

        form = EnrollmentForm(
            self.frame,
            user=self.TEST_USER,
            on_back=on_back
        )
        form.pack(fill="both", expand=True)

        form.go_back()

        on_back.assert_called_once()

    # --------------------------------------------------
    # LIST TESTS
    # --------------------------------------------------

    def list_patches(self):
        return (
            patch(
                "ui.enrollments.enrollment_list.get_academic_years",
                return_value=SAMPLE_YEARS
            ),
            patch(
                "ui.enrollments.enrollment_list.get_classes",
                return_value=SAMPLE_CLASSES
            ),
            patch(
                "ui.enrollments.enrollment_list.get_enrollments",
                return_value=[SAMPLE_ENROLLMENT]
            ),
        )

    def test_11_list_displays_enrollments(self):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=Mock(),
            on_promote=Mock(),
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        rows = list_frame.tree.get_children()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], "101")

        values = list_frame.tree.item(rows[0], "values")

        self.assertEqual(values[1], "STU-001")
        self.assertEqual(values[2], "John Smith")
        self.assertEqual(values[3], "2026-2027")
        self.assertEqual(values[4], "Grade 1")
        self.assertEqual(values[5], "A")

    def test_12_search_and_filter_enrollments(self):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=Mock(),
            on_promote=Mock(),
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("John")
        list_frame.year_filter_var.set("10 - 2026-2027")
        list_frame.class_filter_var.set("20 - Grade 1")
        list_frame.status_filter_var.set("enrolled")

        list_frame.load_enrollments()

        from ui.enrollments.enrollment_list import get_enrollments

        get_enrollments.assert_called_with(
            search="John",
            academic_year_id=10,
            class_id=20,
            status="enrolled",
            actor_user_id=self.TEST_USER["id"],
        )

    def test_13_clear_enrollment_filters(self):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=Mock(),
            on_promote=Mock(),
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.search_var.set("John")
        list_frame.year_filter_var.set("10 - 2026-2027")
        list_frame.class_filter_var.set("20 - Grade 1")
        list_frame.status_filter_var.set("completed")

        list_frame.clear_filters()

        self.assertEqual(list_frame.search_var.get(), "")
        self.assertEqual(
            list_frame.year_filter_var.get(),
            "All Academic Years"
        )
        self.assertEqual(
            list_frame.class_filter_var.get(),
            "All Classes"
        )
        self.assertEqual(
            list_frame.status_filter_var.get(),
            "All Statuses"
        )

    def test_14_edit_selected_enrollment(self):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        on_edit = Mock()

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=on_edit,
            on_promote=Mock(),
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.tree.selection_set("101")
        list_frame.edit_enrollment()

        on_edit.assert_called_once_with(101)

    def test_15_promote_selected_student(self):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        on_promote = Mock()

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=Mock(),
            on_promote=on_promote,
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        list_frame.tree.selection_set("101")
        list_frame.promote_student()

        on_promote.assert_called_once_with(101)

    @patch("ui.enrollments.enrollment_list.messagebox.showwarning")
    def test_16_reject_actions_without_selection(self, mock_warning):
        patches = self.list_patches()

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        list_frame = EnrollmentListFrame(
            self.frame,
            on_create=Mock(),
            on_edit=Mock(),
            on_promote=Mock(),
            user=self.TEST_USER,
        )
        list_frame.pack(fill="both", expand=True)

        self.assertIsNone(
            list_frame.get_selected_enrollment_id()
        )

        mock_warning.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
