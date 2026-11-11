import io
import tempfile
import tkinter as tk
import unittest

from pathlib import Path
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.documents.document_list_frame import DocumentListFrame


SAMPLE_DOCUMENT = {
    "id": 501,
    "student_id": 101,
    "teacher_id": None,
    "transport_staff_id": None,
    "category": "birth_certificate",
    "title": "Birth Certificate",
    "original_filename": "birth.pdf",
    "file_extension": ".pdf",
    "size_bytes": 2048,
    "created_at": "2026-11-10 10:00:00",
    "status": "active",
}

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


class DocumentListFrameUITests(unittest.TestCase):

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

        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_list_ui_test_"
        )
        self.destination_dir = Path(self.temp_dir.name)

        self.admin = {
            "id": 1,
            "username": "admin",
            "full_name": "Test Administrator",
            "role": "admin",
        }

        self.staff = {
            "id": 2,
            "username": "staff",
            "full_name": "Test Staff",
            "role": "staff",
        }

    def tearDown(self):
        for child in self.frame.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

        self.frame.destroy()
        self.temp_dir.cleanup()
        self.root.update_idletasks()

    def create_page(self, user=None, documents=None):
        if user is None:
            user = self.admin

        if documents is None:
            documents = [SAMPLE_DOCUMENT]

        with patch(
            "ui.documents.document_list_frame.get_documents",
            return_value=documents,
        ) as mock_documents, patch(
            "ui.documents.document_list_frame.get_students",
            return_value=[SAMPLE_STUDENT],
        ) as mock_students, patch(
            "ui.documents.document_list_frame.get_teachers",
            return_value=[SAMPLE_TEACHER],
        ) as mock_teachers, patch(
            "ui.documents.document_list_frame.get_transport_staff_list",
            return_value=[SAMPLE_STAFF],
        ) as mock_staff:
            page = DocumentListFrame(
                self.frame,
                user=user,
            )

        return (
            page,
            mock_documents,
            mock_students,
            mock_teachers,
            mock_staff,
        )

    # --------------------------------------------------
    # INITIAL DISPLAY
    # --------------------------------------------------

    def test_01_loads_global_documents_with_active_status(self):
        (
            page,
            mock_documents,
            mock_students,
            mock_teachers,
            mock_staff,
        ) = self.create_page()

        mock_documents.assert_called_once_with(
            search="",
            owner_type=None,
            category=None,
            status="active",
            actor_user_id=1,
        )

        mock_students.assert_called_once_with(
            actor_user_id=1,
        )
        mock_teachers.assert_called_once_with(
            actor_user_id=1,
        )
        mock_staff.assert_called_once_with()

        self.assertEqual(page.tree.get_children(), ("501",))
        self.assertIn(501, page.documents_by_id)

    def test_02_displays_owner_identity_and_document_fields(self):
        page, *_ = self.create_page()

        values = page.tree.item("501", "values")

        self.assertEqual(values[0], "Student")
        self.assertEqual(values[1], "STU-001 — Alice Student")
        self.assertEqual(values[2], "Birth Certificate")
        self.assertEqual(values[3], "Birth Certificate")
        self.assertEqual(values[4], "birth.pdf")
        self.assertEqual(values[5], "2.0 KB")
        self.assertEqual(values[7], "Active")

    def test_03_uses_record_id_when_owner_lookup_fails(self):
        with patch(
            "ui.documents.document_list_frame.get_documents",
            return_value=[SAMPLE_DOCUMENT],
        ), patch(
            "ui.documents.document_list_frame.get_students",
            side_effect=RuntimeError("Lookup failed"),
        ), patch(
            "ui.documents.document_list_frame.get_teachers",
            return_value=[],
        ), patch(
            "ui.documents.document_list_frame.get_transport_staff_list",
            return_value=[],
        ):
            page = DocumentListFrame(
                self.frame,
                user=self.admin,
            )

        values = page.tree.item("501", "values")

        self.assertEqual(values[0], "Student")
        self.assertEqual(values[1], "ID 101")

    def test_04_empty_result_displays_empty_message(self):
        page, *_ = self.create_page(documents=[])

        self.assertEqual(page.tree.get_children(), ())
        self.assertTrue(page.empty_label.winfo_manager())
        self.assertEqual(
            page.empty_label.cget("text"),
            "No documents found.",
        )

    # --------------------------------------------------
    # SEARCH AND FILTERS
    # --------------------------------------------------

    def test_05_search_and_filters_reach_document_service(self):
        page, *_ = self.create_page()

        page.search_var.set("contract")
        page.owner_type_var.set("Teacher")
        page.load_categories()
        page.category_var.set("Qualification Certificate")
        page.status_var.set("Archived")

        with patch(
            "ui.documents.document_list_frame.get_documents",
            return_value=[],
        ) as mock_documents:
            page.load_documents()

        mock_documents.assert_called_once_with(
            search="contract",
            owner_type="teacher",
            category="qualification_certificate",
            status="archived",
            actor_user_id=1,
        )

    def test_06_all_status_filter_passes_none(self):
        page, *_ = self.create_page()

        page.status_var.set("All")

        with patch(
            "ui.documents.document_list_frame.get_documents",
            return_value=[],
        ) as mock_documents:
            page.load_documents()

        self.assertIsNone(
            mock_documents.call_args.kwargs["status"]
        )

    def test_07_owner_filter_restricts_available_categories(self):
        page, *_ = self.create_page()

        page.owner_type_var.set("Transport Staff")
        page.load_categories()

        self.assertIn(
            "Drivers License",
            page.category_codes,
        )
        self.assertNotIn(
            "Birth Certificate",
            page.category_codes,
        )
        self.assertEqual(
            page.category_var.get(),
            "All Categories",
        )

    def test_08_owner_type_change_reloads_documents(self):
        page, *_ = self.create_page()

        with patch.object(
            page,
            "load_documents",
        ) as mock_load:
            page.owner_type_var.set("Teacher")
            page.on_owner_type_changed()

        mock_load.assert_called_once_with()
        self.assertIn(
            "Qualification Certificate",
            page.category_codes,
        )

    # --------------------------------------------------
    # ROLE-BASED ARCHIVING
    # --------------------------------------------------

    def test_09_admin_sees_archive_button(self):
        page, *_ = self.create_page(user=self.admin)

        self.assertIsNotNone(page.archive_button)
        self.assertTrue(page.archive_button.winfo_manager())

    def test_10_staff_does_not_see_archive_button(self):
        page, *_ = self.create_page(user=self.staff)

        self.assertIsNone(page.archive_button)

    def test_11_staff_cannot_archive_document(self):
        page, *_ = self.create_page(user=self.staff)
        page.tree.selection_set("501")

        with patch(
            "ui.documents.document_list_frame.archive_document"
        ) as mock_archive, patch(
            "ui.documents.document_list_frame.messagebox.showerror"
        ) as mock_error:
            page.archive_selected()

        mock_archive.assert_not_called()
        mock_error.assert_called_once()

    def test_12_admin_can_archive_selected_document(self):
        page, *_ = self.create_page(user=self.admin)
        page.tree.selection_set("501")

        with patch(
            "ui.documents.document_list_frame.messagebox.askyesno",
            return_value=True,
        ), patch(
            "ui.documents.document_list_frame.archive_document"
        ) as mock_archive, patch.object(
            page,
            "load_documents",
        ) as mock_load:
            page.archive_selected()

        mock_archive.assert_called_once_with(
            501,
            actor_user_id=1,
        )
        mock_load.assert_called_once_with()

    def test_13_already_archived_document_is_not_archived_again(self):
        archived_document = dict(
            SAMPLE_DOCUMENT,
            status="archived",
        )
        page, *_ = self.create_page(
            documents=[archived_document],
        )
        page.tree.selection_set("501")

        with patch(
            "ui.documents.document_list_frame.archive_document"
        ) as mock_archive, patch(
            "ui.documents.document_list_frame.messagebox.showinfo"
        ) as mock_info:
            page.archive_selected()

        mock_archive.assert_not_called()
        mock_info.assert_called_once()

    # --------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------

    def test_14_downloads_selected_document(self):
        page, *_ = self.create_page()
        page.tree.selection_set("501")

        destination = self.destination_dir / "downloaded_birth.pdf"

        with patch(
            "ui.documents.document_list_frame.filedialog.asksaveasfilename",
            return_value=str(destination),
        ), patch(
            "ui.documents.document_list_frame.open_document",
            return_value=io.BytesIO(b"%PDF-1.4\nverified content"),
        ) as mock_open, patch(
            "ui.documents.document_list_frame.messagebox.showinfo"
        ) as mock_info:
            page.download_selected()

        mock_open.assert_called_once_with(
            501,
            actor_user_id=1,
        )

        self.assertTrue(destination.is_file())
        self.assertEqual(
            destination.read_bytes(),
            b"%PDF-1.4\nverified content",
        )
        mock_info.assert_called_once()

    def test_15_cancelled_download_does_not_open_document(self):
        page, *_ = self.create_page()
        page.tree.selection_set("501")

        with patch(
            "ui.documents.document_list_frame.filedialog.asksaveasfilename",
            return_value="",
        ), patch(
            "ui.documents.document_list_frame.open_document"
        ) as mock_open:
            page.download_selected()

        mock_open.assert_not_called()

    def test_16_download_failure_does_not_replace_destination(self):
        page, *_ = self.create_page()
        page.tree.selection_set("501")

        destination = self.destination_dir / "existing.pdf"
        destination.write_bytes(b"original destination")

        with patch(
            "ui.documents.document_list_frame.filedialog.asksaveasfilename",
            return_value=str(destination),
        ), patch(
            "ui.documents.document_list_frame.open_document",
            side_effect=OSError("Storage unavailable"),
        ), patch(
            "ui.documents.document_list_frame.messagebox.showerror"
        ) as mock_error:
            page.download_selected()

        self.assertEqual(
            destination.read_bytes(),
            b"original destination",
        )
        mock_error.assert_called_once()

    def test_17_download_requires_selection(self):
        page, *_ = self.create_page()

        with patch(
            "ui.documents.document_list_frame.messagebox.showwarning"
        ) as mock_warning:
            page.download_selected()

        mock_warning.assert_called_once()

    # --------------------------------------------------
    # UPLOAD
    # --------------------------------------------------

    def test_18_opens_upload_dialog_with_refresh_callback(self):
        page, *_ = self.create_page()

        with patch(
            "ui.documents.document_list_frame.DocumentUploadDialog"
        ) as mock_dialog:
            page.open_upload_dialog()

        mock_dialog.assert_called_once_with(
            page,
            user=self.admin,
            on_uploaded=page.load_documents,
        )

    # --------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------

    def test_19_document_service_error_displays_error(self):
        page, *_ = self.create_page()

        with patch(
            "ui.documents.document_list_frame.get_documents",
            side_effect=RuntimeError("Database unavailable"),
        ), patch(
            "ui.documents.document_list_frame.messagebox.showerror"
        ) as mock_error:
            page.load_documents()

        self.assertEqual(page.documents_by_id, {})
        self.assertEqual(page.tree.get_children(), ())
        self.assertEqual(
            page.empty_label.cget("text"),
            "Could not load documents.",
        )
        mock_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
