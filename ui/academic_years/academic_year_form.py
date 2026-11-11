import tkinter as tk
from tkinter import ttk, messagebox

from services.academic_year_service import (
    create_academic_year,
    update_academic_year,
)


class AcademicYearForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        academic_year=None,
        *,
        user
    ):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or user.get("id") is None:
            raise ValueError("An authenticated user is required.")

        if user.get("role") != "admin":
            raise PermissionError(
                "Only administrators can configure academic years."
            )

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.academic_year = academic_year

        self.name_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.is_current_var = tk.BooleanVar(value=False)

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.academic_year:
            self.load_academic_year_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Academic Year"
            if self.academic_year
            else "Academic Year Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Create and manage academic-year dates "
                "and the current academic year."
            ),
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Academic Year Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        fields = [
            (
                "Academic Year Name",
                self.name_var,
                "Example: 2026-2027"
            ),
            (
                "Start Date (YYYY-MM-DD)",
                self.start_date_var,
                "Example: 2026-09-01"
            ),
            (
                "End Date (YYYY-MM-DD)",
                self.end_date_var,
                "Example: 2027-06-30"
            ),
        ]

        for row, (label_text, variable, placeholder) in enumerate(fields):
            ttk.Label(
                form,
                text=label_text
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=8,
                pady=12
            )

            entry = ttk.Entry(
                form,
                textvariable=variable,
                width=35
            )

            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                padx=8,
                pady=12
            )

        ttk.Checkbutton(
            form,
            text="Set this as the current academic year",
            variable=self.is_current_var
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=8,
            pady=(15, 5)
        )

        ttk.Label(
            form,
            text=(
                "Setting this option will automatically unset "
                "the previously current academic year."
            ),
            foreground="#64748B",
            wraplength=550
        ).grid(
            row=4,
            column=1,
            sticky="w",
            padx=8,
            pady=(0, 8)
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_academic_year_data(self):
        self.name_var.set(
            self.academic_year.get("name") or ""
        )

        self.start_date_var.set(
            self.academic_year.get("start_date") or ""
        )

        self.end_date_var.set(
            self.academic_year.get("end_date") or ""
        )

        self.is_current_var.set(
            bool(self.academic_year.get("is_current"))
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Academic Year"
            if self.academic_year
            else "Save Academic Year"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_academic_year
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Records",
            command=self.go_back
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_academic_year(self):
        year_data = {
            "name": self.name_var.get().strip(),
            "start_date": self.start_date_var.get().strip(),
            "end_date": self.end_date_var.get().strip(),
            "is_current": self.is_current_var.get(),
        }

        try:
            if self.academic_year:
                update_academic_year(
                    self.academic_year["id"],
                    year_data,
                    actor_user_id=self.user["id"]
                )

                message = "Academic year updated successfully."

            else:
                academic_year_id = create_academic_year(
                    year_data,
                    actor_user_id=self.user["id"]
                )

                message = (
                    "Academic year created successfully.\n"
                    f"Academic Year ID: {academic_year_id}"
                )

            messagebox.showinfo(
                "Success",
                message,
                parent=self
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Academic Year Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save academic year:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.name_var.set("")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.is_current_var.set(False)

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
