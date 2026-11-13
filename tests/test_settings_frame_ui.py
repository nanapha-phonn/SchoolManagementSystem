import tkinter as tk
import unittest

from tkinter import ttk
from unittest.mock import Mock, patch

from ui.settings.settings_frame import SettingsFrame


class SettingsFrameUITests(unittest.TestCase):

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
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

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

        self.on_restored = Mock()
        self.school_profile_patch = patch(
            "ui.settings.school_profile_section.get_school_profile",
            return_value=None,
        )
        self.mock_get_school_profile = (
            self.school_profile_patch.start()
        )
        self.addCleanup(self.school_profile_patch.stop)

    def tearDown(self):
        for child in self.container.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

        self.container.destroy()
        self.root.update_idletasks()

    def create_settings(self, user=None):
        if user is None:
            user = self.admin

        return SettingsFrame(
            self.container,
            user=user,
            on_restored=self.on_restored,
        )

    # --------------------------------------------------
    # INITIAL DISPLAY
    # --------------------------------------------------

    def test_01_admin_sees_backup_and_restore_controls(self):
        settings = self.create_settings()

        self.assertEqual(
            str(settings.backup_button["state"]),
            "normal",
        )
        self.assertEqual(
            str(settings.restore_button["state"]),
            "normal",
        )

    def test_02_staff_controls_are_disabled(self):
        settings = self.create_settings(self.staff)

        self.assertEqual(
            str(settings.backup_button["state"]),
            "disabled",
        )
        self.assertEqual(
            str(settings.restore_button["state"]),
            "disabled",
        )

    # --------------------------------------------------
    # CREATE BACKUP
    # --------------------------------------------------

    def test_03_create_backup_calls_service(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.create_backup_service",
            return_value="/tmp/school_backup.zip",
        ) as mock_backup, patch(
            "ui.settings.settings_frame.messagebox.showinfo"
        ) as mock_info:
            settings.create_backup()

        mock_backup.assert_called_once_with(
            actor_user_id=1,
        )
        mock_info.assert_called_once()

        self.assertIn(
            "school_backup.zip",
            mock_info.call_args.args[1],
        )

    def test_04_backup_failure_displays_error(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.create_backup_service",
            side_effect=OSError("Storage unavailable"),
        ) as mock_backup, patch(
            "ui.settings.settings_frame.messagebox.showerror"
        ) as mock_error:
            settings.create_backup()

        mock_backup.assert_called_once()
        mock_error.assert_called_once()

    def test_05_staff_cannot_create_backup(self):
        settings = self.create_settings(self.staff)

        with patch(
            "ui.settings.settings_frame.create_backup_service"
        ) as mock_backup, patch(
            "ui.settings.settings_frame.messagebox.showerror"
        ) as mock_error:
            settings.create_backup()

        mock_backup.assert_not_called()
        mock_error.assert_called_once()

    # --------------------------------------------------
    # RESTORE
    # --------------------------------------------------

    def test_06_cancelled_file_selection_does_not_restore(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.filedialog.askopenfilename",
            return_value="",
        ), patch(
            "ui.settings.settings_frame.restore_backup_service"
        ) as mock_restore:
            settings.restore_backup()

        mock_restore.assert_not_called()
        self.on_restored.assert_not_called()

    def test_07_declined_confirmation_does_not_restore(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.filedialog.askopenfilename",
            return_value="/tmp/school_backup.zip",
        ), patch(
            "ui.settings.settings_frame.messagebox.askyesno",
            return_value=False,
        ) as mock_confirm, patch(
            "ui.settings.settings_frame.restore_backup_service"
        ) as mock_restore:
            settings.restore_backup()

        mock_confirm.assert_called_once()
        mock_restore.assert_not_called()
        self.on_restored.assert_not_called()

    def test_08_confirmed_restore_calls_service_and_relogin(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.filedialog.askopenfilename",
            return_value="/tmp/school_backup.zip",
        ), patch(
            "ui.settings.settings_frame.messagebox.askyesno",
            return_value=True,
        ), patch(
            "ui.settings.settings_frame.restore_backup_service"
        ) as mock_restore, patch(
            "ui.settings.settings_frame.messagebox.showinfo"
        ) as mock_info:
            settings.restore_backup()

        mock_restore.assert_called_once_with(
            "/tmp/school_backup.zip",
            actor_user_id=1,
        )
        mock_info.assert_called_once()
        self.on_restored.assert_called_once_with()

    def test_09_restore_failure_does_not_trigger_relogin(self):
        settings = self.create_settings()

        with patch(
            "ui.settings.settings_frame.filedialog.askopenfilename",
            return_value="/tmp/invalid_backup.zip",
        ), patch(
            "ui.settings.settings_frame.messagebox.askyesno",
            return_value=True,
        ), patch(
            "ui.settings.settings_frame.restore_backup_service",
            side_effect=ValueError("Invalid archive"),
        ) as mock_restore, patch(
            "ui.settings.settings_frame.messagebox.showerror"
        ) as mock_error:
            settings.restore_backup()

        mock_restore.assert_called_once()
        mock_error.assert_called_once()
        self.on_restored.assert_not_called()

    def test_10_staff_cannot_restore_backup(self):
        settings = self.create_settings(self.staff)

        with patch(
            "ui.settings.settings_frame.filedialog.askopenfilename"
        ) as mock_dialog, patch(
            "ui.settings.settings_frame.restore_backup_service"
        ) as mock_restore, patch(
            "ui.settings.settings_frame.messagebox.showerror"
        ) as mock_error:
            settings.restore_backup()

        mock_dialog.assert_not_called()
        mock_restore.assert_not_called()
        mock_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
