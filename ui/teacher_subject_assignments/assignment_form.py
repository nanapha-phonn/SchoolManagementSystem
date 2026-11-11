import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from services.teacher_service import get_teachers
from services.subject_service import get_subjects
from services.section_service import get_sections
from services.academic_year_service import get_academic_years
from services.teacher_subject_assignment_service import (
    create_teacher_subject_assignment,
    reassign_teacher_subject_assignment,
)


class TeacherSubjectAssignmentForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        assignment=None,
        reassign=False,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.assignment = assignment
        self.reassign = bool(reassign and assignment)

        self.teacher_var = tk.StringVar()
        self.subject_var = tk.StringVar()
        self.section_var = tk.StringVar()
        self.academic_year_var = tk.StringVar()
        self.assigned_on_var = tk.StringVar(
            value=date.today().isoformat()
        )
        self.ended_on_var = tk.StringVar(
            value=date.today().isoformat()
        )

        self.teacher_id_by_label = {}
        self.subject_id_by_label = {}
        self.section_id_by_label = {}
        self.year_id_by_label = {}

        self.load_reference_data()
        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.assignment:
            self.load_assignment_data()

    # --------------------------------------------------
    # REFERENCE DATA
    # --------------------------------------------------

    def load_reference_data(self):
        try:
            teachers = get_teachers(actor_user_id=self.user["id"])

            for teacher in teachers:
                if teacher["status"] != "active":
                    continue

                teacher_id = int(teacher["id"])
                label = (
                    f'{teacher["employee_no"]} - '
                    f'{teacher["first_name"]} '
                    f'{teacher["last_name"]}'
                )

                self.teacher_id_by_label[label] = teacher_id

            subjects = get_subjects(
                status="active",
                actor_user_id=self.user["id"],
            )

            for subject in subjects:
                subject_id = int(subject["id"])
                label = (
                    f'{subject["subject_code"]} - '
                    f'{subject["name"]}'
                )

                self.subject_id_by_label[label] = subject_id

            sections = get_sections(actor_user_id=self.user["id"])

            for section in sections:
                section_id = int(section["id"])
                label = (
                    f'{section["class_name"]} - '
                    f'{section["name"]}'
                )

                self.section_id_by_label[label] = section_id

            academic_years = get_academic_years()

            for year in academic_years:
                year_id = int(year["id"])
                label = (
                    f'{year["name"]}'
                    + (
                        " (Current)"
                        if year["is_current"]
                        else ""
                    )
                )

                self.year_id_by_label[label] = year_id

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load assignment reference data:\n{error}",
                parent=self,
            )

    def get_missing_reference_data(self):
        missing = []

        if not self.teacher_id_by_label:
            missing.append("active teachers")

        if not self.subject_id_by_label:
            missing.append("active subjects")

        if not self.section_id_by_label:
            missing.append("class sections")

        if not self.year_id_by_label:
            missing.append("academic years")

        return missing

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        if self.reassign:
            title = "Reassign Subject to Another Teacher"
            description = (
                "End the current teacher assignment and assign "
                "the same subject, section and academic year "
                "to another active teacher."
            )
        else:
            title = "New Teacher–Subject Assignment"
            description = (
                "Assign an active teacher to a subject, "
                "class section and academic year."
            )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=description,
            font=("Segoe UI", 10),
            wraplength=800,
        ).pack(anchor="w", pady=(5, 20))

        missing = self.get_missing_reference_data()

        if missing and not self.reassign:
            if "class sections" in missing:
                warning = (
                    "No class sections are available. "
                    "Create a class and section before creating "
                    "a teacher–subject assignment."
                )
            else:
                warning = (
                    "Assignment creation is unavailable. "
                    "Missing reference data: "
                    + ", ".join(missing)
                    + ". Please create the required records first."
                )

            ttk.Label(
                self,
                text=warning,
                wraplength=800,
            ).pack(anchor="w", pady=(0, 15))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Assignment Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        self.teacher_combo = self._add_combo(
            form,
            "Teacher",
            self.teacher_var,
            list(self.teacher_id_by_label.keys()),
            0,
        )

        self.subject_combo = self._add_combo(
            form,
            "Subject",
            self.subject_var,
            list(self.subject_id_by_label.keys()),
            1,
        )

        self.section_combo = self._add_combo(
            form,
            "Class / Section",
            self.section_var,
            list(self.section_id_by_label.keys()),
            2,
        )

        self.year_combo = self._add_combo(
            form,
            "Academic Year",
            self.academic_year_var,
            list(self.year_id_by_label.keys()),
            3,
        )

        ttk.Label(
            form,
            text="Assignment Date (YYYY-MM-DD)",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.assigned_on_entry = ttk.Entry(
            form,
            textvariable=self.assigned_on_var,
            width=35,
        )
        self.assigned_on_entry.grid(
            row=4,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text="End Date (YYYY-MM-DD)",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.ended_on_entry = ttk.Entry(
            form,
            textvariable=self.ended_on_var,
            width=35,
        )
        self.ended_on_entry.grid(
            row=5,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        if not self.reassign:
            self.ended_on_entry.configure(state="disabled")

        ttk.Label(
            form,
            text=(
                "For reassignment, the new assignment date "
                "must be later than the previous end date."
            ),
            foreground="#64748B",
            wraplength=650,
        ).grid(
            row=6,
            column=1,
            sticky="w",
            padx=8,
            pady=(3, 10),
        )

    def _add_combo(
        self,
        parent,
        label,
        variable,
        values,
        row,
    ):
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            width=45,
        )

        combo.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        return combo

    # --------------------------------------------------
    # EXISTING ASSIGNMENT
    # --------------------------------------------------

    def load_assignment_data(self):
        self.subject_var.set(
            self._find_label(
                self.subject_id_by_label,
                self.assignment["subject_id"],
            )
        )

        self.section_var.set(
            self._find_label(
                self.section_id_by_label,
                self.assignment["section_id"],
            )
        )

        self.academic_year_var.set(
            self._find_label(
                self.year_id_by_label,
                self.assignment["academic_year_id"],
            )
        )

        if self.reassign:
            self.teacher_combo.configure(state="readonly")

            self.teacher_var.set("")
            self.assigned_on_var.set(
                date.today().isoformat()
            )

            self.subject_combo.configure(state="disabled")
            self.section_combo.configure(state="disabled")
            self.year_combo.configure(state="disabled")

        else:
            self.teacher_var.set(
                self._find_label(
                    self.teacher_id_by_label,
                    self.assignment["teacher_id"],
                )
            )

            self.teacher_combo.configure(state="disabled")
            self.subject_combo.configure(state="disabled")
            self.section_combo.configure(state="disabled")
            self.year_combo.configure(state="disabled")

            self.assigned_on_var.set(
                self.assignment["assigned_on"]
            )

            self.assigned_on_entry.configure(state="disabled")

    @staticmethod
    def _find_label(mapping, record_id):
        record_id = int(record_id)

        for label, value in mapping.items():
            if value == record_id:
                return label

        return ""

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        if self.reassign:
            save_text = "Confirm Reassignment"
        elif self.assignment:
            save_text = "Save"
        else:
            save_text = "Create Assignment"

        self.save_button = ttk.Button(
            buttons,
            text=save_text,
            command=self.save_assignment,
        )
        self.save_button.pack(side="right", padx=5)

        # Existing assignments can only be reassigned.
        # Core assignment details must never be edited directly.
        if self.assignment and not self.reassign:
            self.save_button.configure(state="disabled")
        elif not self.reassign and self.get_missing_reference_data():
            self.save_button.configure(state="disabled")

        ttk.Button(
            buttons,
            text="Back",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    def save_assignment(self):
        if self.assignment and not self.reassign:
            messagebox.showwarning(
                "Editing Not Supported",
                "Existing assignments cannot be edited. "
                "Use Reassign Teacher to preserve assignment history.",
                parent=self,
            )
            return

        if not self.reassign:
            missing = self.get_missing_reference_data()

            if missing:
                messagebox.showwarning(
                    "Reference Data Missing",
                    (
                        "Cannot create this assignment. "
                        "Missing reference data: "
                        + ", ".join(missing)
                        + ". Please create the required records first."
                    ),
                    parent=self,
                )
                return

        if self.reassign:
            new_teacher_id = self.teacher_id_by_label.get(
                self.teacher_var.get()
            )

            if new_teacher_id is None:
                messagebox.showwarning(
                    "Teacher Required",
                    "Please select a different active teacher.",
                    parent=self,
                )
                return

            try:
                new_assignment_id = (
                    reassign_teacher_subject_assignment(
                        assignment_id=self.assignment["id"],
                        new_teacher_id=new_teacher_id,
                        ended_on=self.ended_on_var.get().strip(),
                        assigned_on=self.assigned_on_var.get().strip(),
                        actor_user_id=self.user["id"],
                    )
                )

                messagebox.showinfo(
                    "Success",
                    (
                        "Teacher reassigned successfully.\n"
                        f"New assignment ID: {new_assignment_id}"
                    ),
                    parent=self,
                )

                if self.on_saved:
                    self.on_saved()

            except ValueError as error:
                messagebox.showwarning(
                    "Validation Error",
                    str(error),
                    parent=self,
                )

            except Exception as error:
                messagebox.showerror(
                    "Error",
                    f"Could not reassign teacher:\n{error}",
                    parent=self,
                )

            return

        teacher_id = self.teacher_id_by_label.get(
            self.teacher_var.get()
        )
        subject_id = self.subject_id_by_label.get(
            self.subject_var.get()
        )
        section_id = self.section_id_by_label.get(
            self.section_var.get()
        )
        academic_year_id = self.year_id_by_label.get(
            self.academic_year_var.get()
        )

        selections = (
            ("Teacher", teacher_id),
            ("Subject", subject_id),
            ("Section", section_id),
            ("Academic year", academic_year_id),
        )

        for label, value in selections:
            if value is None:
                messagebox.showwarning(
                    "Selection Required",
                    f"Please select a valid {label.lower()}.",
                    parent=self,
                )
                return

        assignment_data = {
            "teacher_id": teacher_id,
            "subject_id": subject_id,
            "section_id": section_id,
            "academic_year_id": academic_year_id,
            "assigned_on": self.assigned_on_var.get().strip(),
            "status": "active",
        }

        try:
            assignment_id = create_teacher_subject_assignment(
                assignment_data,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                (
                    "Teacher–subject assignment created successfully.\n"
                    f"Assignment ID: {assignment_id}"
                ),
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Validation Error",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not create assignment:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
