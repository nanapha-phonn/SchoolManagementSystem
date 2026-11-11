import tkinter as tk
import unittest

from tkinter import ttk
from unittest.mock import Mock, patch

from ui.documents.document_upload_dialog import DocumentUploadDialog


SAMPLE_STUDENT = {
    "id": 101,
    "admission_no": "STU-001",
    "first_name": "Alice",
    "last_name": "Student",
}

SAMPLE_TEACHER = {
    "id": 202,
    "employee_no": "EMP-001",
    "first_name": "Bob",
    "last_name": "Teacher",
}

SAMPLE_STAFF = {
    "id": 303,
    "employee_no": "TR-001",
    "first_name": "Chris",
    "last_name": "Driver",
}


class DocumentUploadDialogUITests(unittest.TestCase):

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
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.user = {
            "id": 2,
            "username": "staff",
            "full_name": "Test Staff",
            "role": "staff",
        }

        self.on_uploaded = Mock()

    def tearDown(self):
        for child in self.frame.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

        self.frame.destroy()
        self.root.update_idletasks()

    def create_dialog(self):
        with patch(
            "ui.documents.document_upload_dialog.get_students",
            return_value=[SAMPLE_STUDENT],
        ) as mock_students, patch(
            "ui.documents.document_upload_dialog.get_teachers",
            return_value=[SAMPLE_TEACHER],
        ) as mock_teachers, patch(
            "ui.documents.document_upload_dialog.get_transport_staff_list",
            return_value=[SAMPLE_STAFF],
        ) as mock_staff:
            dialog = DocumentUploadDialog(
                self.frame,
                user=self.user,
                on_uploaded=self.on_uploaded,
            )

        return dialog, mock_students, mock_teachers, mock_staff

    def test_01_initializes_student_owner_and_categories(self):
        dialog, mock_students, _, _ = self.create_dialog()

        mock_students.assert_called_once_with(
            search="",
            actor_user_id=2,
        )

        self.assertEqual(dialog.selected_owner_type, "student")
        self.assertEqual(
            dialog.owner_records,
            {"STU-001 — Alice Student (ID: 101)": 101},
        )
        self.assertEqual(
            dialog.category_codes["Birth Certificate"],
            "birth_certificate",
        )
        self.assertEqual(dialog.category_var.get(), "Other")

    def test_02_switching_to_teacher_loads_teacher_categories(self):
        dialog, _, mock_teachers, _ = self.create_dialog()

        dialog.owner_type_var.set("Teacher")
        dialog.owner_search_var.set("Bob")

        with patch(
            "ui.documents.document_upload_dialog.get_teachers",
            return_value=[SAMPLE_TEACHER],
        ) as mock_lookup:
            dialog.on_owner_type_changed()

        mock_lookup.assert_called_once_with(
            search="Bob",
            actor_user_id=2,
        )

        self.assertEqual(dialog.selected_owner_type, "teacher")
        self.assertEqual(
            dialog.owner_records,
            {"EMP-001 — Bob Teacher (ID: 202)": 202},
        )
        self.assertIn(
            "Qualification Certificate",
            dialog.category_codes,
        )
        self.assertNotIn(
            "Birth Certificate",
            dialog.category_codes,
        )

    def test_03_switching_to_transport_staff_loads_staff_records(self):
        dialog, _, _, _ = self.create_dialog()

        dialog.owner_type_var.set("Transport Staff")

        with patch(
            "ui.documents.document_upload_dialog.get_transport_staff_list",
            return_value=[SAMPLE_STAFF],
        ) as mock_lookup:
            dialog.on_owner_type_changed()

        mock_lookup.assert_called_once_with(search="")

        self.assertEqual(
            dialog.selected_owner_type,
            "transport_staff",
        )
        self.assertEqual(
            dialog.owner_records,
            {"TR-001 — Chris Driver (ID: 303)": 303},
        )
        self.assertIn(
            "Drivers License",
            dialog.category_codes,
        )

    def test_04_owner_search_refreshes_student_records(self):
        dialog, _, _, _ = self.create_dialog()

        dialog.owner_search_var.set("Alice")

        with patch(
            "ui.documents.document_upload_dialog.get_students",
            return_value=[SAMPLE_STUDENT],
        ) as mock_lookup:
            dialog.load_owners()

        mock_lookup.assert_called_once_with(
            search="Alice",
            actor_user_id=2,
        )

    def test_05_browse_file_updates_filename_and_default_title(self):
        dialog, *_ = self.create_dialog()

        with patch(
            "ui.documents.document_upload_dialog.filedialog.askopenfilename",
            return_value="/tmp/birth_certificate.pdf",
        ):
            dialog.browse_file()

        self.assertEqual(
            str(dialog.selected_file_path),
            "/tmp/birth_certificate.pdf",
        )
        self.assertEqual(
            dialog.file_var.get(),
            "birth_certificate.pdf",
        )
        self.assertEqual(
            dialog.title_var.get(),
            "birth_certificate",
        )

    def test_06_upload_uses_document_service_and_selected_owner(self):
        dialog, *_ = self.create_dialog()

        dialog.selected_file_path = "/tmp/birth_certificate.pdf"
        dialog.title_var.set("Birth Certificate")
        dialog.category_var.set("Birth Certificate")
        dialog.description_text.insert(
            "1.0",
            "Original birth certificate",
        )

        with patch(
            "ui.documents.document_upload_dialog.upload_document",
            return_value={"id": 9001},
        ) as mock_upload, patch(
            "ui.documents.document_upload_dialog.messagebox.showinfo",
        ):
            dialog.submit_upload()

        mock_upload.assert_called_once_with(
            dialog.selected_file_path,
            "student",
            101,
            "birth_certificate",
            "Birth Certificate",
            "Original birth certificate",
            actor_user_id=2,
        )

        self.on_uploaded.assert_called_once()

    def test_07_requires_file_before_upload(self):
        dialog, *_ = self.create_dialog()

        with patch(
            "ui.documents.document_upload_dialog.upload_document"
        ) as mock_upload, patch(
            "ui.documents.document_upload_dialog.messagebox.showwarning"
        ) as mock_warning:
            dialog.submit_upload()

        mock_upload.assert_not_called()
        mock_warning.assert_called_once()

    def test_08_requires_valid_owner_before_upload(self):
        dialog, *_ = self.create_dialog()

        dialog.selected_file_path = "/tmp/document.pdf"
        dialog.owner_var.set("Invalid record")

        with patch(
            "ui.documents.document_upload_dialog.upload_document"
        ) as mock_upload, patch(
            "ui.documents.document_upload_dialog.messagebox.showwarning"
        ) as mock_warning:
            dialog.submit_upload()

        mock_upload.assert_not_called()
        mock_warning.assert_called_once()

    def test_09_requires_title_before_upload(self):
        dialog, *_ = self.create_dialog()

        dialog.selected_file_path = "/tmp/document.pdf"
        dialog.title_var.set("")

        with patch(
            "ui.documents.document_upload_dialog.upload_document"
        ) as mock_upload, patch(
            "ui.documents.document_upload_dialog.messagebox.showwarning"
        ) as mock_warning:
            dialog.submit_upload()

        mock_upload.assert_not_called()
        mock_warning.assert_called_once()

    def test_10_displays_service_validation_errors(self):
        dialog, *_ = self.create_dialog()

        dialog.selected_file_path = "/tmp/invalid.pdf"
        dialog.title_var.set("Invalid File")

        with patch(
            "ui.documents.document_upload_dialog.upload_document",
            side_effect=ValueError("Unsupported document file type."),
        ) as mock_upload, patch(
            "ui.documents.document_upload_dialog.messagebox.showerror"
        ) as mock_error:
            dialog.submit_upload()

        mock_upload.assert_called_once()
        mock_error.assert_called_once()

        self.assertIn(
            "Unsupported document file type.",
            mock_error.call_args.args[1],
        )

        self.on_uploaded.assert_not_called()

    def test_11_owner_lookup_failure_clears_owner_options(self):
        dialog, *_ = self.create_dialog()

        with patch(
            "ui.documents.document_upload_dialog.get_students",
            side_effect=RuntimeError("Database unavailable"),
        ), patch(
            "ui.documents.document_upload_dialog.messagebox.showerror"
        ) as mock_error:
            dialog.load_owners()

        self.assertEqual(dialog.owner_records, {})
        self.assertFalse(
            dialog.owner_combo.cget("values"),
        )
        mock_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
