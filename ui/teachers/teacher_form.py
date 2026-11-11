import tkinter as tk
from tkinter import ttk, messagebox

from services.teacher_service import (
    create_teacher,
    update_teacher
)


class TeacherForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        teacher=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)
        self.user = user

        self.on_back = on_back
        self.on_saved = on_saved
        self.teacher = teacher
        self.variables = {}

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.teacher:
            self.load_teacher_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Teacher Information"
            if self.teacher
            else "Teacher Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Enter the teacher's personal and employment information.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Teacher Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        fields = [
            ("Employee Number", "employee_no", 0, 0),
            ("First Name", "first_name", 0, 2),
            ("Last Name", "last_name", 1, 0),
            ("Date of Birth (YYYY-MM-DD)", "date_of_birth", 1, 2),
            ("Gender", "gender", 2, 0),
            ("Phone Number", "phone", 2, 2),
            ("Email Address", "email", 3, 0),
            ("Qualification", "qualification", 3, 2),
            ("Specialization", "specialization", 4, 0),
            ("Department", "department", 4, 2),
            ("Employment Date (YYYY-MM-DD)", "employment_date", 5, 0),
            ("Status", "status", 5, 2),
        ]

        for label_text, field_name, row, column in fields:
            ttk.Label(
                form,
                text=label_text
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=8,
                pady=10
            )

            variable = tk.StringVar()
            self.variables[field_name] = variable

            if field_name == "gender":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=["Male", "Female", "Other"],
                    state="readonly"
                )

            elif field_name == "status":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=[
                        "active",
                        "inactive",
                        "resigned",
                        "terminated"
                    ],
                    state="readonly"
                )
                variable.set("active")

            else:
                widget = ttk.Entry(
                    form,
                    textvariable=variable,
                    width=30
                )

            widget.grid(
                row=row,
                column=column + 1,
                sticky="ew",
                padx=8,
                pady=10
            )

        ttk.Label(
            form,
            text="Address"
        ).grid(
            row=6,
            column=0,
            sticky="nw",
            padx=8,
            pady=10
        )

        self.address_text = tk.Text(
            form,
            height=4,
            width=40,
            font=("Segoe UI", 10),
            wrap="word"
        )

        self.address_text.grid(
            row=6,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=8,
            pady=10
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_teacher_data(self):
        for field, variable in self.variables.items():
            variable.set(
                self.teacher.get(field) or ""
            )

        self.address_text.insert(
            "1.0",
            self.teacher.get("address") or ""
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Teacher"
            if self.teacher
            else "Save Teacher"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_teacher
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

    def save_teacher(self):
        teacher_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        teacher_data["address"] = self.address_text.get(
            "1.0",
            "end"
        ).strip()

        try:
            if self.teacher:
                update_teacher(
                    self.teacher["id"],
                    teacher_data,
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Teacher information updated successfully."
                )

            else:
                teacher_id = create_teacher(
                    teacher_data,
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Teacher registered successfully.\n"
                    f"Teacher ID: {teacher_id}"
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
                "Invalid Teacher Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save teacher information:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        for variable in self.variables.values():
            variable.set("")

        self.variables["status"].set("active")
        self.address_text.delete("1.0", "end")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
