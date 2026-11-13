import tkinter as tk
from tkinter import messagebox, ttk

from services.school_profile_service import (
    get_school_profile,
    save_school_profile,
)


class SchoolProfileSection(ttk.LabelFrame):
    """Manage the single-school profile."""

    def __init__(self, master, user):
        super().__init__(master, text="School Profile", padding=18)

        self.user = user
        self.actor_user_id = user["id"]
        self.is_admin = user.get("role") == "admin"

        self.variables = {
            "name": tk.StringVar(),
            "address": tk.StringVar(),
            "phone": tk.StringVar(),
            "email": tk.StringVar(),
        }

        self.create_widgets()

        self.load_profile()

    def create_widgets(self):
        fields = [
            ("name", "School Name"),
            ("address", "Address"),
            ("phone", "Phone"),
            ("email", "Email"),
        ]

        for key, label_text in fields:
            row = ttk.Frame(self)
            row.pack(fill="x", pady=5)

            ttk.Label(
                row,
                text=label_text,
                width=15,
            ).pack(side="left")

            entry = ttk.Entry(
                row,
                textvariable=self.variables[key],
                state="normal" if self.is_admin else "disabled",
            )
            entry.pack(side="left", fill="x", expand=True)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 0))

        self.save_button = ttk.Button(
            actions,
            text="Save School Profile",
            command=self.save_profile,
            state="normal" if self.is_admin else "disabled",
        )
        self.save_button.pack(side="left")

        self.status_var = tk.StringVar(
            value=(
                "Loading school profile..."
                if self.is_admin
                else "Administrator permission is required."
            )
        )

        ttk.Label(
            actions,
            textvariable=self.status_var,
            foreground="#64748B",
        ).pack(side="left", padx=12)

    def load_profile(self):
        try:
            profile = get_school_profile(
                actor_user_id=self.actor_user_id,
            )

            for key, variable in self.variables.items():
                variable.set(
                    (profile or {}).get(key) or ""
                )

            self.status_var.set(
                "School profile loaded."
                if profile
                else "No school profile configured yet."
            )

        except Exception as error:
            self.status_var.set("Could not load school profile.")
            messagebox.showerror(
                "School Profile Error",
                str(error),
                parent=self.winfo_toplevel(),
            )

    def save_profile(self):
        if not self.is_admin:
            messagebox.showerror(
                "Permission Denied",
                "Only administrators can manage the school profile.",
                parent=self.winfo_toplevel(),
            )
            return

        profile_data = {
            key: variable.get()
            for key, variable in self.variables.items()
        }

        try:
            save_school_profile(
                profile_data,
                actor_user_id=self.actor_user_id,
            )

            self.load_profile()

            messagebox.showinfo(
                "School Profile Saved",
                "The school profile was saved successfully.",
                parent=self.winfo_toplevel(),
            )

        except (ValueError, PermissionError) as error:
            messagebox.showerror(
                "Invalid School Profile",
                str(error),
                parent=self.winfo_toplevel(),
            )

        except Exception as error:
            messagebox.showerror(
                "Save Failed",
                str(error),
                parent=self.winfo_toplevel(),
            )
