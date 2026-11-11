import io
import tempfile
import tkinter as tk
import unittest

from pathlib import Path
from tkinter import ttk
from unittest.mock import Mock, patch

from ui.documents.document_panel import DocumentPanel


SAMPLE_DOCUMENT = {
    "id": 1,
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


class DocumentPanelUITests(unittest.TestCase):

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

        self.admin = {
            "id": 1,
            "full_name": "Test Administrator",
            "role": "admin",
        }

        self.staff = {
            "id": 2,
            "full_name": "Test Staff",
            "role": "staff",
        }

        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_panel_ui_test_"
        )
        self.destination_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.frame.destroy()
        self.temp_dir.cleanup()
        self.root.update_idletasks()

    def create_panel(self, user=None, documents=None):
        if user is None:
            user = self.admin

        if documents is None:
            documents = [SAMPLE_DOCUMENT]

        with patch(
            "ui.documents.document_panel.get_documents",
            return_value=documents,
        ) as mock_get_documents:
            panel = DocumentPanel(
                self.frame,
                owner_type="student",
                owner_id=101,
                user=user,
            )

        return panel, mock_get_documents

    # --------------------------------------------------
    # INITIAL DISPLAY
    # --------------------------------------------------

    def test_01_loads_documents_for_correct_owner(self):
        panel, mock_get_documents = self.create_panel()

        mock_get_documents.assert_called_once_with(
            owner_type="student",
            owner_id=101,
            status="active",
            actor_user_id=self.admin["id"],
        )

        rows = panel.tree.get_children()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], "1")

        values = panel.tree.item(rows[0], "values")

        self.assertEqual(values[0], "Birth Certificate")
        self.assertEqual(values[1], "Birth Certificate")
        self.assertEqual(values[2], "birth.pdf")
        self.assertEqual(values[3], "2.0 KB")
        self.assertEqual(values[5], "Active")

        self.assertIn(1, panel.documents_by_id)

    def test_02_empty_document_list_displays_empty_message(self):
        panel, _ = self.create_panel(documents=[])

        self.assertEqual(panel.tree.get_children(), ())
        self.assertTrue(panel.empty_label.winfo_manager())

    def test_03_status_filter_loads_archived_documents(self):
        archived_document = dict(
            SAMPLE_DOCUMENT,
            status="archived",
        )

        with patch(
            "ui.documents.document_panel.get_documents",
            return_value=[SAMPLE_DOCUMENT],
        ) as mock_get_documents:
            panel = DocumentPanel(
                self.frame,
                owner_type="student",
                owner_id=101,
                user=self.admin,
            )

            mock_get_documents.reset_mock()
            mock_get_documents.return_value = [archived_document]

            panel.status_var.set("Archived")
            panel.on_status_changed()

        mock_get_documents.assert_called_once_with(
            owner_type="student",
            owner_id=101,
            status="archived",
            actor_user_id=self.admin["id"],
        )

        values = panel.tree.item("1", "values")
        self.assertEqual(values[5], "Archived")

    def test_04_all_status_filter_passes_none(self):
        with patch(
            "ui.documents.document_panel.get_documents",
            return_value=[],
        ) as mock_get_documents:
            panel = DocumentPanel(
                self.frame,
                owner_type="student",
                owner_id=101,
                user=self.admin,
            )

            mock_get_documents.reset_mock()

            panel.status_var.set("All")
            panel.on_status_changed()

        mock_get_documents.assert_called_once_with(
            owner_type="student",
            owner_id=101,
            status=None,
            actor_user_id=self.admin["id"],
        )

    # --------------------------------------------------
    # ROLE-BASED CONTROLS
    # --------------------------------------------------

    def test_05_admin_sees_archive_button(self):
        panel, _ = self.create_panel(user=self.admin)

        self.assertIsNotNone(panel.archive_button)
        self.assertTrue(panel.archive_button.winfo_manager())

    def test_06_staff_does_not_see_archive_button(self):
        panel, _ = self.create_panel(user=self.staff)

        self.assertIsNone(panel.archive_button)

    def test_07_staff_cannot_archive_document(self):
        panel, _ = self.create_panel(user=self.staff)
        panel.tree.selection_set("1")

        with patch(
            "ui.documents.document_panel.archive_document"
        ) as mock_archive, patch(
            "ui.documents.document_panel.messagebox.showerror"
        ) as mock_error:
            panel.archive_selected()

        mock_archive.assert_not_called()
        mock_error.assert_called_once()

    def test_08_admin_can_archive_selected_document(self):
        panel, _ = self.create_panel(user=self.admin)
        panel.tree.selection_set("1")

        with patch(
            "ui.documents.document_panel.messagebox.askyesno",
            return_value=True,
        ), patch(
            "ui.documents.document_panel.archive_document"
        ) as mock_archive:
            panel.load_documents = Mock()
            panel.archive_selected()

        mock_archive.assert_called_once_with(
            1,
            actor_user_id=self.admin["id"],
        )
        panel.load_documents.assert_called_once()

    def test_09_cancelled_archive_does_not_call_service(self):
        panel, _ = self.create_panel(user=self.admin)
        panel.tree.selection_set("1")

        with patch(
            "ui.documents.document_panel.messagebox.askyesno",
            return_value=False,
        ), patch(
            "ui.documents.document_panel.archive_document"
        ) as mock_archive:
            panel.archive_selected()

        mock_archive.assert_not_called()

    # --------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------

    def test_10_downloads_selected_document(self):
        panel, _ = self.create_panel()
        panel.tree.selection_set("1")

        destination = self.destination_dir / "downloaded_birth.pdf"

        with patch(
            "ui.documents.document_panel.filedialog.asksaveasfilename",
            return_value=str(destination),
        ), patch(
            "ui.documents.document_panel.open_document",
            return_value=io.BytesIO(b"%PDF-1.4\nverified content"),
        ) as mock_open, patch(
            "ui.documents.document_panel.messagebox.showinfo"
        ) as mock_info:
            panel.download_selected()

        mock_open.assert_called_once_with(
            1,
            actor_user_id=self.admin["id"],
        )

        self.assertTrue(destination.is_file())
        self.assertEqual(
            destination.read_bytes(),
            b"%PDF-1.4\nverified content",
        )
        mock_info.assert_called_once()

    def test_11_cancelled_download_does_not_open_document(self):
        panel, _ = self.create_panel()
        panel.tree.selection_set("1")

        with patch(
            "ui.documents.document_panel.filedialog.asksaveasfilename",
            return_value="",
        ), patch(
            "ui.documents.document_panel.open_document"
        ) as mock_open:
            panel.download_selected()

        mock_open.assert_not_called()

    def test_12_download_failure_does_not_replace_destination(self):
        panel, _ = self.create_panel()
        panel.tree.selection_set("1")

        destination = self.destination_dir / "existing.pdf"
        destination.write_bytes(b"original destination content")

        with patch(
            "ui.documents.document_panel.filedialog.asksaveasfilename",
            return_value=str(destination),
        ), patch(
            "ui.documents.document_panel.open_document",
            side_effect=OSError("Integrity verification failed"),
        ), patch(
            "ui.documents.document_panel.messagebox.showerror"
        ) as mock_error:
            panel.download_selected()

        self.assertEqual(
            destination.read_bytes(),
            b"original destination content",
        )
        mock_error.assert_called_once()

    # --------------------------------------------------
    # VALIDATION AND DISPLAY HELPERS
    # --------------------------------------------------

    def test_13_rejects_unsupported_owner_type(self):
        with self.assertRaises(ValueError):
            DocumentPanel(
                self.frame,
                owner_type="unknown",
                owner_id=101,
                user=self.admin,
            )

    def test_14_category_and_size_formatting(self):
        self.assertEqual(
            DocumentPanel.format_category("birth_certificate"),
            "Birth Certificate",
        )

        self.assertEqual(
            DocumentPanel.format_size(500),
            "500 B",
        )

        self.assertEqual(
            DocumentPanel.format_size(2048),
            "2.0 KB",
        )

        self.assertEqual(
            DocumentPanel.format_size(2 * 1024 * 1024),
            "2.00 MB",
        )


if __name__ == "__main__":
    unittest.main()
