import tkinter as tk
import unittest

from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ui.dashboard import DashboardWindow


class DocumentDashboardRouteTests(unittest.TestCase):

    def setUp(self):
        self.user = {
            "id": 1,
            "username": "admin",
            "full_name": "Test Administrator",
            "role": "admin",
        }

        self.dashboard = SimpleNamespace(
            content=object(),
            user=self.user,
            clear_content=Mock(),
            _check_permission=Mock(return_value=True),
        )

    @patch("ui.dashboard.DocumentListFrame")
    def test_01_opens_documents_page(self, mock_page_class):
        page = mock_page_class.return_value

        DashboardWindow.show_documents(self.dashboard)

        self.dashboard._check_permission.assert_called_once_with(
            "documents.view",
        )
        self.dashboard.clear_content.assert_called_once_with()

        mock_page_class.assert_called_once_with(
            self.dashboard.content,
            user=self.user,
        )

        page.pack.assert_called_once_with(
            fill="both",
            expand=True,
        )

    @patch("ui.dashboard.DocumentListFrame")
    def test_02_denied_permission_does_not_open_page(self, mock_page_class):
        self.dashboard._check_permission.return_value = False

        DashboardWindow.show_documents(self.dashboard)

        self.dashboard._check_permission.assert_called_once_with(
            "documents.view",
        )
        self.dashboard.clear_content.assert_not_called()
        mock_page_class.assert_not_called()


class DocumentDashboardSidebarTests(unittest.TestCase):

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
        self.window = None

    def tearDown(self):
        if self.window is not None:
            try:
                self.window.unbind_all("<MouseWheel>")
                self.window.unbind_all("<Button-4>")
                self.window.unbind_all("<Button-5>")
                self.window.destroy()
                self.root.update_idletasks()
            except tk.TclError:
                pass

    def create_dashboard(self, denied_permission=None):
        self.window = DashboardWindow.__new__(DashboardWindow)
        tk.Toplevel.__init__(self.window, self.root)

        self.window.user = {
            "id": 1,
            "username": "test",
            "full_name": "Test User",
            "role": "staff",
        }

        def check_permission(user_id, permission):
            if permission == denied_permission:
                raise PermissionError("Access denied.")

            return True

        with patch(
            "ui.dashboard.require_permission",
            side_effect=check_permission,
        ) as mock_permission:
            DashboardWindow.setup_styles(self.window)
            DashboardWindow.create_sidebar(self.window)

        return mock_permission

    @staticmethod
    def find_buttons(parent):
        buttons = []

        for child in parent.winfo_children():
            if isinstance(child, ttk.Button):
                buttons.append(child)

            buttons.extend(
                DocumentDashboardSidebarTests.find_buttons(child)
            )

        return buttons

    def test_03_sidebar_shows_documents_with_permission(self):
        mock_permission = self.create_dashboard()

        buttons = self.find_buttons(self.window)
        labels = [button.cget("text") for button in buttons]

        self.assertIn("Documents", labels)
        self.assertIn("documents.view", [
            call.args[1] for call in mock_permission.call_args_list
        ])

    def test_04_sidebar_hides_documents_without_permission(self):
        self.create_dashboard(
            denied_permission="documents.view",
        )

        buttons = self.find_buttons(self.window)
        labels = [button.cget("text") for button in buttons]

        self.assertNotIn("Documents", labels)


if __name__ == "__main__":
    unittest.main()
