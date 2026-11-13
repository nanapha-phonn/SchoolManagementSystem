import tkinter as tk
import unittest

from tkinter import ttk
from unittest.mock import patch

from ui.settings.school_profile_section import SchoolProfileSection


def sample_profile():
    return {
        "id": 1,
        "name": "Demo International School",
        "address": "Phnom Penh, Cambodia",
        "phone": "+855 12 345 678",
        "email": "info@demo-school.example",
        "created_at": "2026-11-12 10:00:00",
    }


class SchoolProfileUITests(unittest.TestCase):

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

    def tearDown(self):
        self.container.destroy()
        self.root.update_idletasks()

    def test_01_admin_loads_existing_profile(self):
        with patch(
            "ui.settings.school_profile_section.get_school_profile",
            return_value=sample_profile(),
        ) as mock_get:
            section = SchoolProfileSection(
                self.container,
                user=self.admin,
            )

        mock_get.assert_called_once_with(actor_user_id=1)
        self.assertEqual(
            section.variables["name"].get(),
            "Demo International School",
        )
        self.assertEqual(
            section.variables["address"].get(),
            "Phnom Penh, Cambodia",
        )
        self.assertEqual(
            section.variables["phone"].get(),
            "+855 12 345 678",
        )
        self.assertEqual(
            section.variables["email"].get(),
            "info@demo-school.example",
        )

    def test_02_admin_sees_empty_profile_message(self):
        with patch(
            "ui.settings.school_profile_section.get_school_profile",
            return_value=None,
        ):
            section = SchoolProfileSection(
                self.container,
                user=self.admin,
            )

        self.assertEqual(
            section.status_var.get(),
            "No school profile configured yet.",
        )

    def test_03_admin_saves_school_profile(self):
        with patch(
            "ui.settings.school_profile_section.get_school_profile",
            side_effect=[None, sample_profile()],
        ), patch(
            "ui.settings.school_profile_section.save_school_profile",
            return_value=1,
        ) as mock_save, patch(
            "ui.settings.school_profile_section.messagebox.showinfo",
        ) as mock_info:
            section = SchoolProfileSection(
                self.container,
                user=self.admin,
            )

            section.variables["name"].set("Demo International School")
            section.variables["address"].set("Phnom Penh, Cambodia")
            section.variables["phone"].set("+855 12 345 678")
            section.variables["email"].set(
                "info@demo-school.example"
            )

            section.save_profile()

        mock_save.assert_called_once_with(
            {
                "name": "Demo International School",
                "address": "Phnom Penh, Cambodia",
                "phone": "+855 12 345 678",
                "email": "info@demo-school.example",
            },
            actor_user_id=1,
        )
        mock_info.assert_called_once()

    def test_04_invalid_profile_displays_validation_error(self):
        with patch(
            "ui.settings.school_profile_section.get_school_profile",
            return_value=None,
        ), patch(
            "ui.settings.school_profile_section.save_school_profile",
            side_effect=ValueError("School name is required."),
        ) as mock_save, patch(
            "ui.settings.school_profile_section.messagebox.showerror",
        ) as mock_error:
            section = SchoolProfileSection(
                self.container,
                user=self.admin,
            )

            section.save_profile()

        mock_save.assert_called_once()
        mock_error.assert_called_once()
        self.assertIn(
            "School name is required.",
            mock_error.call_args.args[1],
        )

    def test_05_staff_can_view_but_cannot_edit_school_profile(self):
        with patch(
            "ui.settings.school_profile_section.get_school_profile",
            return_value=sample_profile(),
        ) as mock_get:
            section = SchoolProfileSection(
                self.container,
                user=self.staff,
            )

        mock_get.assert_called_once_with(actor_user_id=2)
        self.assertEqual(
            section.variables["name"].get(),
            "Demo International School",
        )
        self.assertEqual(
            section.variables["address"].get(),
            "Phnom Penh, Cambodia",
        )

        self.assertEqual(
            str(section.save_button["state"]),
            "disabled",
        )

        entries = []

        def collect_entries(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Entry):
                    entries.append(child)
                collect_entries(child)

        collect_entries(section)

        self.assertEqual(len(entries), 4)

        for entry in entries:
            self.assertEqual(str(entry["state"]), "disabled")


if __name__ == "__main__":
    unittest.main()
