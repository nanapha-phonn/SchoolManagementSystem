import tkinter as tk
from tkinter import ttk, messagebox

from services.assessment_period_service import get_assessment_periods
from services.teacher_subject_assignment_service import (
    get_teacher_subject_assignments,
)
from services.enrollment_service import get_enrollments
from services.grading_scheme_service import get_grading_schemes
from services.student_subject_result_service import (
    create_student_subject_result,
    update_student_subject_result,
)


class StudentResultForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        result=None,
        user=None,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.result = result

        self.periods = {}
        self.assignments = {}
        self.enrollments = {}
        self.grading_scheme = None

        self.period_var = tk.StringVar()
        self.assignment_var = tk.StringVar()
        self.enrollment_var = tk.StringVar()
        self.marks_var = tk.StringVar()
        self.maximum_var = tk.StringVar(value="100")

        self.create_widgets()

        if self.result:
            self.load_existing_result()
        else:
            self.load_periods()

    def create_widgets(self):
        title = (
            "Edit Student Marks"
            if self.result
            else "Enter Student Marks"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", pady=(0, 18))

        form = ttk.LabelFrame(
            self,
            text="Academic Result Information",
            padding=15,
        )
        form.pack(fill="x")

        if not self.result:
            self.period_combo = self.add_combo(
                form, "Assessment Period:", self.period_var, 0
            )
            self.period_combo.bind(
                "<<ComboboxSelected>>",
                self.on_period_selected,
            )

            self.assignment_combo = self.add_combo(
                form, "Subject / Teacher:", self.assignment_var, 1
            )
            self.assignment_combo.bind(
                "<<ComboboxSelected>>",
                self.on_assignment_selected,
            )

            self.enrollment_combo = self.add_combo(
                form, "Student:", self.enrollment_var, 2
            )

            self.reference_label = ttk.Label(
                form,
                text="Select an assessment period and assignment.",
                wraplength=650,
            )
            self.reference_label.grid(
                row=3, column=1, sticky="w", padx=8, pady=8
            )

        else:
            self.reference_label = ttk.Label(
                form,
                text="",
                wraplength=700,
            )
            self.reference_label.grid(
                row=0, column=1, sticky="w", padx=8, pady=8
            )

        first_marks_row = 4 if not self.result else 1

        ttk.Label(
            form,
            text="Marks Obtained:",
        ).grid(
            row=first_marks_row,
            column=0,
            sticky="w",
            padx=8,
            pady=8,
        )

        ttk.Entry(
            form,
            textvariable=self.marks_var,
            width=25,
        ).grid(
            row=first_marks_row,
            column=1,
            sticky="w",
            padx=8,
            pady=8,
        )

        ttk.Label(
            form,
            text="Maximum Marks:",
        ).grid(
            row=first_marks_row + 1,
            column=0,
            sticky="w",
            padx=8,
            pady=8,
        )

        ttk.Entry(
            form,
            textvariable=self.maximum_var,
            width=25,
        ).grid(
            row=first_marks_row + 1,
            column=1,
            sticky="w",
            padx=8,
            pady=8,
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        ttk.Button(
            buttons,
            text="Save",
            command=self.save,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back",
            command=self.go_back,
        ).pack(side="right", padx=5)

        self.save_button = buttons.winfo_children()[0]

        if self.result:
            self.load_existing_result()

    @staticmethod
    def add_combo(parent, label, variable, row):
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=8,
            pady=8,
        )

        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            state="readonly",
            width=65,
        )
        combo.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=8,
            pady=8,
        )
        return combo

    def load_periods(self):
        try:
            periods = get_assessment_periods(
                status="active", actor_user_id=self.user["id"]
            )
        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                str(error),
                parent=self,
            )
            self.save_button.configure(state="disabled")
            return

        for period in periods:
            label = (
                f"{period['name']} | "
                f"{period['academic_year_name']} | "
                f"{period['start_date']} to {period['end_date']}"
                f" [ID:{period['id']}]"
            )
            self.periods[label] = period

        self.period_combo["values"] = list(self.periods)

        if not self.periods:
            self.reference_label.configure(
                text="No active assessment periods are available."
            )
            self.save_button.configure(state="disabled")

    def on_period_selected(self, event=None):
        self.assignment_var.set("")
        self.enrollment_var.set("")

        self.assignments.clear()
        self.enrollments.clear()
        self.grading_scheme = None

        period = self.periods.get(self.period_var.get())

        if not period:
            return

        try:
            assignments = get_teacher_subject_assignments(
                academic_year_id=period["academic_year_id"],
                actor_user_id=self.user["id"],
            )

            for assignment in assignments:
                overlaps = (
                    assignment["assigned_on"] <= period["end_date"]
                    and (
                        not assignment["ended_on"]
                        or assignment["ended_on"] >= period["start_date"]
                    )
                )

                if not overlaps:
                    continue

                label = (
                    f"{assignment['subject_code']} - "
                    f"{assignment['subject_name']} | "
                    f"{assignment['teacher_name']} | "
                    f"{assignment['section_name']} "
                    f"[ID:{assignment['id']}]"
                )
                self.assignments[label] = assignment

            self.assignment_combo["values"] = list(self.assignments)

            if not self.assignments:
                self.reference_label.configure(
                    text="No teacher assignments overlap this assessment period."
                )
                self.save_button.configure(state="disabled")
            else:
                self.reference_label.configure(
                    text="Select a subject and teacher assignment."
                )
                self.save_button.configure(state="normal")

        except Exception as error:
            messagebox.showerror(
                "Assignment Loading Error",
                str(error),
                parent=self,
            )

    def on_assignment_selected(self, event=None):
        self.enrollment_var.set("")
        self.enrollments.clear()
        self.grading_scheme = None

        period = self.periods.get(self.period_var.get())
        assignment = self.assignments.get(
            self.assignment_var.get()
        )

        if not period or not assignment:
            return

        try:
            enrollments = get_enrollments(
                academic_year_id=period["academic_year_id"],
                section_id=assignment["section_id"],
                status="enrolled",
                actor_user_id=self.user["id"],
            )

            for enrollment in enrollments:
                label = (
                    f"{enrollment['admission_no']} - "
                    f"{enrollment['student_name']} "
                    f"[ID:{enrollment['id']}]"
                )
                self.enrollments[label] = enrollment

            self.enrollment_combo["values"] = list(self.enrollments)

            if not enrollments:
                self.reference_label.configure(
                    text="No currently enrolled students in this section."
                )
                self.save_button.configure(state="disabled")
                return

            class_id = enrollments[0]["class_id"]

            schemes = get_grading_schemes(
                class_id=class_id,
                academic_year_id=period["academic_year_id"],
                status="active",
                actor_user_id=self.user["id"],
            )

            if len(schemes) != 1:
                self.reference_label.configure(
                    text=(
                        "This class does not have exactly one active "
                        "grading scheme."
                    )
                )
                self.save_button.configure(state="disabled")
                return

            self.grading_scheme = schemes[0]

            self.reference_label.configure(
                text=(
                    f"Grading scheme: {self.grading_scheme['name']} "
                    f"(Version {self.grading_scheme['version_no']})"
                )
            )
            self.save_button.configure(state="normal")

        except Exception as error:
            self.save_button.configure(state="disabled")
            messagebox.showerror(
                "Student Loading Error",
                str(error),
                parent=self,
            )

    def load_existing_result(self):
        self.reference_label.configure(
            text=(
                f"Student: {self.result['admission_no']} - "
                f"{self.result['student_first_name']} "
                f"{self.result['student_last_name']}\\n"
                f"Subject: {self.result['subject_name']}\\n"
                f"Assessment: {self.result['assessment_period_name']}\\n"
                f"Teacher: {self.result['teacher_name']}\\n"
                f"Grading scheme: {self.result['grading_scheme_name']} "
                f"(Version {self.result['grading_scheme_version']})"
            )
        )

        self.marks_var.set(str(self.result["marks_obtained"]))
        self.maximum_var.set(str(self.result["maximum_marks"]))

        if self.result["assessment_period_status"] != "active":
            self.save_button.configure(state="disabled")

    def save(self):
        try:
            marks = float(self.marks_var.get())
            maximum = float(self.maximum_var.get())

            if not self.result:
                period = self.periods.get(self.period_var.get())
                assignment = self.assignments.get(
                    self.assignment_var.get()
                )
                enrollment = self.enrollments.get(
                    self.enrollment_var.get()
                )

                if not all((period, assignment, enrollment, self.grading_scheme)):
                    raise ValueError(
                        "Select the assessment period, assignment, "
                        "and student first."
                    )

                result_data = {
                    "enrollment_id": enrollment["id"],
                    "assessment_period_id": period["id"],
                    "teacher_subject_assignment_id": assignment["id"],
                    "subject_id": assignment["subject_id"],
                    "grading_scheme_id": self.grading_scheme["id"],
                    "marks_obtained": marks,
                    "maximum_marks": maximum,
                }

                create_student_subject_result(result_data)

            else:
                update_student_subject_result(
                    self.result["id"],
                    {
                        "marks_obtained": marks,
                        "maximum_marks": maximum,
                    },
                )

            messagebox.showinfo(
                "Success",
                "Student marks saved successfully.",
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
                "Save Error",
                str(error),
                parent=self,
            )

    def go_back(self):
        if self.on_back:
            self.on_back()
