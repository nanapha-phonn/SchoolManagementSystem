import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.dashboard import DashboardWindow


SAMPLE_STUDENT = {
    "id": 101,
    "admission_no": "STU-001",
    "first_name": "Test",
    "last_name": "Student",
    "status": "active",
}

SAMPLE_TEACHER = {
    "id": 202,
    "employee_no": "EMP-001",
    "first_name": "Test",
    "last_name": "Teacher",
    "status": "active",
}

SAMPLE_STAFF = {
    "id": 303,
    "employee_no": "TR-001",
    "first_name": "Test",
    "last_name": "Driver",
    "status": "active",
}


class DocumentProfileDashboardTests(unittest.TestCase):

    def setUp(self):
        self.dashboard = SimpleNamespace(
            content=object(),
            user={
                "id": 1,
                "username": "admin",
                "full_name": "Test Administrator",
                "role": "admin",
            },
            clear_content=Mock(),
            show_students=Mock(),
            show_student_form=Mock(),
            show_teachers=Mock(),
            show_teacher_form=Mock(),
            show_transport_staff=Mock(),
            show_transport_staff_form=Mock(),
        )

    @patch("ui.dashboard.StudentProfile")
    @patch("ui.dashboard.get_student", return_value=SAMPLE_STUDENT)
    def test_01_student_profile_receives_authenticated_user(
        self,
        mock_get_student,
        mock_profile,
    ):
        profile = mock_profile.return_value

        DashboardWindow.show_student_profile(
            self.dashboard,
            101,
        )

        self.dashboard.clear_content.assert_called_once_with()

        mock_get_student.assert_called_once_with(
            101,
            actor_user_id=1,
        )

        mock_profile.assert_called_once()

        args, kwargs = mock_profile.call_args

        self.assertIs(args[0], self.dashboard.content)
        self.assertEqual(kwargs["student"], SAMPLE_STUDENT)
        self.assertEqual(kwargs["user"], self.dashboard.user)
        self.assertIs(kwargs["on_back"], self.dashboard.show_students)

        profile.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

        kwargs["on_edit"]()
        self.dashboard.show_student_form.assert_called_once_with(101)

    @patch("ui.dashboard.StudentProfile")
    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.get_student", return_value=None)
    def test_02_missing_student_returns_to_student_list(
        self,
        mock_get_student,
        mock_error,
        mock_profile,
    ):
        DashboardWindow.show_student_profile(
            self.dashboard,
            999,
        )

        mock_get_student.assert_called_once_with(
            999,
            actor_user_id=1,
        )

        mock_error.assert_called_once()
        self.dashboard.show_students.assert_called_once_with()
        mock_profile.assert_not_called()

    @patch("ui.dashboard.TeacherProfile")
    @patch("ui.dashboard.get_teacher", return_value=SAMPLE_TEACHER)
    def test_03_teacher_profile_receives_authenticated_user(
        self,
        mock_get_teacher,
        mock_profile,
    ):
        profile = mock_profile.return_value

        DashboardWindow.show_teacher_profile(
            self.dashboard,
            202,
        )

        self.dashboard.clear_content.assert_called_once_with()

        mock_get_teacher.assert_called_once_with(
            202,
            actor_user_id=1,
        )

        mock_profile.assert_called_once()

        args, kwargs = mock_profile.call_args

        self.assertIs(args[0], self.dashboard.content)
        self.assertEqual(kwargs["teacher"], SAMPLE_TEACHER)
        self.assertEqual(kwargs["user"], self.dashboard.user)
        self.assertIs(kwargs["on_back"], self.dashboard.show_teachers)

        profile.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

        kwargs["on_edit"]()
        self.dashboard.show_teacher_form.assert_called_once_with(202)

    @patch("ui.dashboard.TransportStaffProfile")
    @patch(
        "ui.dashboard.get_transport_staff",
        return_value=SAMPLE_STAFF,
    )
    def test_04_transport_staff_profile_receives_authenticated_user(
        self,
        mock_get_staff,
        mock_profile,
    ):
        profile = mock_profile.return_value

        DashboardWindow.show_transport_staff_profile(
            self.dashboard,
            303,
        )

        self.dashboard.clear_content.assert_called_once_with()

        mock_get_staff.assert_called_once_with(303)

        mock_profile.assert_called_once()

        args, kwargs = mock_profile.call_args

        self.assertIs(args[0], self.dashboard.content)
        self.assertEqual(kwargs["staff"], SAMPLE_STAFF)
        self.assertEqual(kwargs["user"], self.dashboard.user)
        self.assertIs(
            kwargs["on_back"],
            self.dashboard.show_transport_staff,
        )

        profile.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

        kwargs["on_edit"]()
        self.dashboard.show_transport_staff_form.assert_called_once_with(303)

    @patch("ui.dashboard.TransportStaffProfile")
    @patch("ui.dashboard.messagebox.showerror")
    @patch("ui.dashboard.get_transport_staff", return_value=None)
    def test_05_missing_transport_staff_returns_to_staff_list(
        self,
        mock_get_staff,
        mock_error,
        mock_profile,
    ):
        DashboardWindow.show_transport_staff_profile(
            self.dashboard,
            999,
        )

        mock_get_staff.assert_called_once_with(999)
        mock_error.assert_called_once()
        self.dashboard.show_transport_staff.assert_called_once_with()
        mock_profile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
