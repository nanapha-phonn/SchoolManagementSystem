import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from services.student_service import get_students
from services.academic_year_service import get_academic_years
from services.class_service import get_classes
from services.section_service import get_sections
from services.enrollment_service import (
    create_enrollment,
    update_enrollment,
)


ENROLLMENT_STATUSES = [
    "enrolled",
    "completed",
    "withdrawn",
    "transferred",
]


class EnrollmentForm(ttk.Frame):

    def __init__(
        self,
        master,
        user,
        on_back=None,
        on_saved=None,
        enrollment=None,
        promote_student_id=None,
        initial_class_id=None,
        initial_section_id=None,
    ):
        super().__init__(master, padding=25)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")
        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.enrollment = enrollment
        self.promote_student_id = promote_student_id
        self.initial_class_id = initial_class_id
        self.initial_section_id = initial_section_id

        self.student_var = tk.StringVar()
        self.academic_year_var = tk.StringVar()
        self.class_var = tk.StringVar()
        self.section_var = tk.StringVar()
        self.enrolled_on_var = tk.StringVar(
            value=date.today().isoformat()
        )
        self.status_var = tk.StringVar(value="enrolled")

        self.student_id_by_label = {}
        self.year_id_by_label = {}
        self.class_id_by_label = {}
        self.section_id_by_label = {}

        self.student_label_by_id = {}
        self.year_label_by_id = {}
        self.class_label_by_id = {}
        self.section_label_by_id = {}

        self.load_reference_data()
        self.create_header()
        self.create_form()
        self.create_buttons()
        self.apply_initial_values()

    # --------------------------------------------------
    # REFERENCE DATA
    # --------------------------------------------------

    def load_reference_data(self):
        try:
            students = get_students(actor_user_id=self.user["id"])

            # New enrollments use active students only.
            # Editing and promotion retain their selected student.
            selected_student_id = None

            if self.enrollment:
                selected_student_id = self.enrollment["student_id"]
            elif self.promote_student_id is not None:
                selected_student_id = self.promote_student_id

            self.student_id_by_label.clear()
            self.student_label_by_id.clear()

            for student in students:
                if (
                    student["status"] != "active"
                    and student["id"] != selected_student_id
                ):
                    continue

                label = (
                    f'{student["admission_no"]} - '
                    f'{student["first_name"]} '
                    f'{student["last_name"]}'
                )

                if student["status"] != "active":
                    label += f' ({student["status"]})'

                self.student_id_by_label[label] = student["id"]
                self.student_label_by_id[student["id"]] = label

            academic_years = get_academic_years(
                actor_user_id=self.user["id"]
            )

            self.year_id_by_label.clear()
            self.year_label_by_id.clear()

            for year in academic_years:
                label = (
                    f'{year["id"]} - {year["name"]}'
                    + (" (Current)" if year["is_current"] else "")
                )

                self.year_id_by_label[label] = year["id"]
                self.year_label_by_id[year["id"]] = label

            classes = get_classes(actor_user_id=self.user["id"])

            self.class_id_by_label.clear()
            self.class_label_by_id.clear()

            for school_class in classes:
                label = (
                    f'{school_class["id"]} - '
                    f'{school_class["name"]}'
                )

                self.class_id_by_label[label] = school_class["id"]
                self.class_label_by_id[school_class["id"]] = label

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load enrollment reference data:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        if self.enrollment:
            title = "Edit Student Enrollment"
            description = (
                "Update the section, enrollment date or status. "
                "Student and academic year cannot be changed."
            )
        elif self.promote_student_id is not None:
            title = "Promote Student"
            description = (
                "Create a new enrollment for the selected student "
                "in another academic year. Previous enrollment "
                "history will be retained."
            )
        else:
            title = "New Student Enrollment"
            description = (
                "Enroll an active student in a class section "
                "for an academic year."
            )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=description,
            font=("Segoe UI", 10),
            wraplength=750,
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Enrollment Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # Student
        ttk.Label(
            form,
            text="Student"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=10
        )

        student_state = (
            "disabled"
            if self.enrollment or self.promote_student_id is not None
            else "readonly"
        )

        self.student_combo = ttk.Combobox(
            form,
            textvariable=self.student_var,
            values=list(self.student_id_by_label.keys()),
            state=student_state,
        )

        self.student_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=10
        )

        # Academic year
        ttk.Label(
            form,
            text="Academic Year"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=8,
            pady=10
        )

        year_state = (
            "disabled"
            if self.enrollment
            else "readonly"
        )

        self.academic_year_combo = ttk.Combobox(
            form,
            textvariable=self.academic_year_var,
            values=list(self.year_id_by_label.keys()),
            state=year_state,
        )

        self.academic_year_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=8,
            pady=10
        )

        # Class
        ttk.Label(
            form,
            text="Class"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=8,
            pady=10
        )

        self.class_combo = ttk.Combobox(
            form,
            textvariable=self.class_var,
            values=list(self.class_id_by_label.keys()),
            state="readonly",
        )

        self.class_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=10
        )

        self.class_combo.bind(
            "<<ComboboxSelected>>",
            self.on_class_changed
        )

        # Section
        ttk.Label(
            form,
            text="Section"
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=8,
            pady=10
        )

        self.section_combo = ttk.Combobox(
            form,
            textvariable=self.section_var,
            values=[],
            state="readonly",
        )

        self.section_combo.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=8,
            pady=10
        )

        # Enrollment date
        ttk.Label(
            form,
            text="Enrollment Date (YYYY-MM-DD)"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=8,
            pady=10
        )

        ttk.Entry(
            form,
            textvariable=self.enrolled_on_var,
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=8,
            pady=10
        )

        # Status
        ttk.Label(
            form,
            text="Enrollment Status"
        ).grid(
            row=2,
            column=2,
            sticky="w",
            padx=8,
            pady=10
        )

        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=ENROLLMENT_STATUSES,
            state="readonly",
        )

        self.status_combo.grid(
            row=2,
            column=3,
            sticky="ew",
            padx=8,
            pady=10
        )

        ttk.Label(
            form,
            text=(
                "Promotion creates a separate enrollment record. "
                "Do not use Edit to change a student's academic year."
            ),
            foreground="#64748B",
            wraplength=700,
        ).grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="w",
            padx=8,
            pady=(12, 5)
        )

    # --------------------------------------------------
    # SECTION OPTIONS
    # --------------------------------------------------

    def load_section_choices(self, selected_section_id=None):
        class_id = self.class_id_by_label.get(
            self.class_var.get()
        )

        self.section_id_by_label.clear()
        self.section_label_by_id.clear()
        self.section_var.set("")

        if class_id is None:
            self.section_combo["values"] = ()
            return

        try:
            sections = get_sections(
                class_id=class_id,
                actor_user_id=self.user["id"],
            )

            for section in sections:
                label = (
                    f'{section["id"]} - {section["name"]}'
                )

                self.section_id_by_label[label] = section["id"]
                self.section_label_by_id[section["id"]] = label

            labels = list(self.section_id_by_label.keys())
            self.section_combo["values"] = labels

            if selected_section_id in self.section_label_by_id:
                self.section_var.set(
                    self.section_label_by_id[selected_section_id]
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load sections:\n{error}",
                parent=self,
            )

    def on_class_changed(self, event=None):
        self.load_section_choices()

    # --------------------------------------------------
    # INITIAL VALUES
    # --------------------------------------------------

    def apply_initial_values(self):
        if self.enrollment:
            student_id = self.enrollment["student_id"]
            year_id = self.enrollment["academic_year_id"]
            class_id = self.enrollment["class_id"]

            self.student_var.set(
                self.student_label_by_id.get(student_id, "")
            )

            self.academic_year_var.set(
                self.year_label_by_id.get(year_id, "")
            )

            self.class_var.set(
                self.class_label_by_id.get(class_id, "")
            )

            self.load_section_choices(
                self.enrollment["section_id"]
            )

            self.enrolled_on_var.set(
                self.enrollment["enrolled_on"]
            )

            self.status_var.set(
                self.enrollment["status"]
            )

        elif self.promote_student_id is not None:
            self.student_var.set(
                self.student_label_by_id.get(
                    self.promote_student_id,
                    ""
                )
            )

            self.academic_year_var.set("")

            self.class_var.set(
                self.class_label_by_id.get(
                    self.initial_class_id,
                    ""
                )
            )

            self.load_section_choices(
                self.initial_section_id
            )

        else:
            self.student_var.set("")
            self.academic_year_var.set("")
            self.class_var.set("")
            self.load_section_choices()

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Enrollment"
            if self.enrollment
            else "Save Enrollment"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_enrollment
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Enrollments",
            command=self.go_back
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_enrollment(self):
        student_id = self.student_id_by_label.get(
            self.student_var.get()
        )

        academic_year_id = self.year_id_by_label.get(
            self.academic_year_var.get()
        )

        class_id = self.class_id_by_label.get(
            self.class_var.get()
        )

        section_id = self.section_id_by_label.get(
            self.section_var.get()
        )

        if self.enrollment:
            student_id = self.enrollment["student_id"]
            academic_year_id = self.enrollment["academic_year_id"]

        if student_id is None:
            messagebox.showwarning(
                "Student Required",
                "Please select a student.",
                parent=self
            )
            return

        if academic_year_id is None:
            messagebox.showwarning(
                "Academic Year Required",
                "Please select an academic year.",
                parent=self
            )
            return

        if class_id is None:
            messagebox.showwarning(
                "Class Required",
                "Please select a class.",
                parent=self
            )
            return

        if section_id is None:
            messagebox.showwarning(
                "Section Required",
                "Please select a section.",
                parent=self
            )
            return

        try:
            if self.enrollment:
                update_enrollment(
                    self.enrollment["id"],
                    {
                        "section_id": section_id,
                        "enrolled_on": self.enrolled_on_var.get().strip(),
                        "status": self.status_var.get(),
                    },
                    actor_user_id=self.user["id"],
                )

                message = "Enrollment updated successfully."

            else:
                enrollment_id = create_enrollment(
                    {
                        "student_id": student_id,
                        "section_id": section_id,
                        "academic_year_id": academic_year_id,
                        "enrolled_on": self.enrolled_on_var.get().strip(),
                        "status": self.status_var.get(),
                    },
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Enrollment created successfully.\n"
                    f"Enrollment ID: {enrollment_id}"
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
                "Invalid Enrollment Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save enrollment:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.enrolled_on_var.set(date.today().isoformat())
        self.status_var.set("enrolled")

        if self.enrollment:
            self.apply_initial_values()
            return

        if self.promote_student_id is not None:
            self.student_var.set(
                self.student_label_by_id.get(
                    self.promote_student_id,
                    ""
                )
            )
        else:
            self.student_var.set("")

        self.academic_year_var.set("")
        self.class_var.set("")
        self.load_section_choices()

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
