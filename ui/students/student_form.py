import tkinter as tk
from tkinter import ttk, messagebox

from services.student_service import (
    create_student,
    update_student
)


class StudentForm(ttk.Frame):

    def __init__(
        self,
        master,
        user,
        on_back=None,
        on_saved=None,
        student=None
    ):
        super().__init__(master, padding=25)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")
        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.student = student
        self.variables = {}

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.student:
            self.load_student_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Student Information"
            if self.student
            else "Student Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Enter the student's personal and guardian information.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Student Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        fields = [
            ("Admission Number", "admission_no", 0, 0),
            ("First Name", "first_name", 0, 2),
            ("Last Name", "last_name", 1, 0),
            ("Date of Birth (YYYY-MM-DD)", "date_of_birth", 1, 2),
            ("Gender", "gender", 2, 0),
            ("Phone Number", "phone", 2, 2),
            ("Email Address", "email", 3, 0),
            ("Guardian Name", "guardian_name", 3, 2),
            ("Guardian Phone", "guardian_phone", 4, 0),
            ("Status", "status", 4, 2),
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
                        "graduated",
                        "transferred"
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
            row=5,
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
            row=5,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=8,
            pady=10
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_student_data(self):
        for field, variable in self.variables.items():
            variable.set(
                self.student.get(field) or ""
            )

        self.address_text.insert(
            "1.0",
            self.student.get("address") or ""
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Student"
            if self.student
            else "Save Student"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_student
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

    def save_student(self):
        student_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        student_data["address"] = self.address_text.get(
            "1.0",
            "end"
        ).strip()

        try:
            if self.student:
                update_student(
                    self.student["id"],
                    student_data,
                    actor_user_id=self.user["id"]
                )

                message = "Student information updated successfully."

            else:
                student_id = create_student(
                    student_data,
                    actor_user_id=self.user["id"]
                )

                message = (
                    "Student registered successfully.\n"
                    f"Student ID: {student_id}"
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
                "Invalid Student Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save student information:\n{error}",
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