import tkinter as tk
from tkinter import ttk, messagebox

from services.academic_year_service import get_academic_years
from services.assessment_period_service import (
    create_assessment_period,
    update_assessment_period,
)


PERIOD_TYPE_OPTIONS = {
    "Midterm": "midterm",
    "Final": "final",
    "Term": "term",
    "Semester": "semester",
    "Other": "other",
}

STATUS_LABELS = {
    "planned": "Planned",
    "active": "Active",
    "completed": "Completed",
}


class AssessmentPeriodForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        assessment_period=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.assessment_period = assessment_period

        self.academic_years = []
        self.academic_year_id_by_label = {}
        self.academic_year_label_by_id = {}

        self.academic_year_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.period_type_var = tk.StringVar(value="Midterm")
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        self.academic_year_combo = None
        self.name_entry = None
        self.period_type_combo = None
        self.start_date_entry = None
        self.end_date_entry = None
        self.save_button = None
        self.clear_button = None

        self.current_status = (
            str(assessment_period.get("status") or "planned").lower()
            if assessment_period
            else "planned"
        )
        self.is_locked = self.current_status == "completed"
        self.load_error = None

        try:
            self.academic_years = get_academic_years(actor_user_id=self.user['id'])
        except Exception as error:
            self.load_error = error

        self.create_header()
        self.create_form()
        self.load_academic_year_options()

        if self.assessment_period:
            self.load_assessment_period_data()

        self.create_buttons()
        self.apply_form_state()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Assessment Period"
            if self.assessment_period
            else "Assessment Period Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Define assessment periods within an academic year. "
                "Periods cannot overlap, and completed periods are locked."
            ),
            font=("Segoe UI", 10),
            wraplength=850,
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Assessment Period Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        ttk.Label(
            form,
            text="Academic Year",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.academic_year_combo = ttk.Combobox(
            form,
            textvariable=self.academic_year_var,
            state="readonly",
            width=48,
        )
        self.academic_year_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="Assessment Period Name",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.name_entry = ttk.Entry(
            form,
            textvariable=self.name_var,
            width=40,
        )
        self.name_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="Period Type",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.period_type_combo = ttk.Combobox(
            form,
            textvariable=self.period_type_var,
            values=list(PERIOD_TYPE_OPTIONS.keys()),
            state="readonly",
            width=25,
        )
        self.period_type_combo.grid(
            row=2,
            column=1,
            sticky="w",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="Start Date (YYYY-MM-DD)",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.start_date_entry = ttk.Entry(
            form,
            textvariable=self.start_date_var,
            width=25,
        )
        self.start_date_entry.grid(
            row=3,
            column=1,
            sticky="w",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="End Date (YYYY-MM-DD)",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.end_date_entry = ttk.Entry(
            form,
            textvariable=self.end_date_var,
            width=25,
        )
        self.end_date_entry.grid(
            row=4,
            column=1,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.status_label = ttk.Label(
            form,
            text="New periods start with status: Planned",
            foreground="#64748B",
            wraplength=650,
        )
        self.status_label.grid(
            row=5,
            column=1,
            sticky="w",
            padx=8,
            pady=(12, 5),
        )

        self.year_warning_label = ttk.Label(
            form,
            text="",
            foreground="#B45309",
            wraplength=650,
        )
        self.year_warning_label.grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            padx=8,
            pady=(8, 0),
        )

    # --------------------------------------------------
    # ACADEMIC YEAR OPTIONS
    # --------------------------------------------------

    def load_academic_year_options(self):
        labels = []

        for year in self.academic_years:
            year_id = int(year["id"])
            label = (
                f'{year["name"]} '
                f'({year["start_date"]} to {year["end_date"]})'
            )

            self.academic_year_id_by_label[label] = year_id
            self.academic_year_label_by_id[year_id] = label
            labels.append(label)

        self.academic_year_combo["values"] = labels

        if self.load_error:
            self.year_warning_label.configure(
                text=f"Could not load academic years: {self.load_error}"
            )
        elif not self.academic_years:
            self.year_warning_label.configure(
                text=(
                    "No academic years are registered. "
                    "Create an academic year before adding an assessment period."
                )
            )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_assessment_period_data(self):
        period = self.assessment_period

        academic_year_id = int(period["academic_year_id"])
        label = self.academic_year_label_by_id.get(academic_year_id)

        if label is None:
            label = (
                f'Academic Year #{academic_year_id} '
                f'({period.get("academic_year_name", "recorded year")})'
            )
            self.academic_year_id_by_label[label] = academic_year_id
            self.academic_year_label_by_id[academic_year_id] = label
            self.academic_year_combo["values"] = (
                *self.academic_year_combo["values"],
                label,
            )

        self.academic_year_var.set(label)
        self.name_var.set(period.get("name") or "")

        period_type = str(period.get("period_type") or "").lower()
        display_type = next(
            (
                display
                for display, stored in PERIOD_TYPE_OPTIONS.items()
                if stored == period_type
            ),
            "Other",
        )
        self.period_type_var.set(display_type)

        self.start_date_var.set(period.get("start_date") or "")
        self.end_date_var.set(period.get("end_date") or "")

        status_text = STATUS_LABELS.get(
            self.current_status,
            self.current_status.title(),
        )

        self.status_label.configure(
            text=f"Current status: {status_text}"
        )

        if self.is_locked:
            self.status_label.configure(
                text=(
                    "Status: Completed. This assessment period is "
                    "permanently locked and cannot be edited."
                ),
                foreground="#B45309",
            )

    # --------------------------------------------------
    # FORM STATE
    # --------------------------------------------------

    def apply_form_state(self):
        if self.assessment_period:
            # An existing period cannot be moved to another year.
            self.academic_year_combo.configure(state="disabled")

        if self.is_locked:
            self.name_entry.configure(state="disabled")
            self.period_type_combo.configure(state="disabled")
            self.start_date_entry.configure(state="disabled")
            self.end_date_entry.configure(state="disabled")

        no_academic_years = (
            not self.academic_years
            and self.assessment_period is None
        )

        if self.load_error or no_academic_years or self.is_locked:
            self.save_button.configure(state="disabled")

        if self.is_locked:
            self.clear_button.configure(state="disabled")

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Assessment Period"
            if self.assessment_period
            else "Save Assessment Period"
        )

        self.save_button = ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_assessment_period,
        )
        self.save_button.pack(side="right", padx=5)

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form,
        )
        self.clear_button.pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Records",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_assessment_period(self):
        if self.is_locked:
            messagebox.showwarning(
                "Assessment Period Locked",
                "Completed assessment periods cannot be changed.",
                parent=self,
            )
            return

        selected_year = self.academic_year_var.get().strip()
        academic_year_id = self.academic_year_id_by_label.get(
            selected_year
        )

        period_type = PERIOD_TYPE_OPTIONS.get(
            self.period_type_var.get()
        )

        if academic_year_id is None:
            messagebox.showwarning(
                "Invalid Assessment Period Information",
                "Please select an academic year.",
                parent=self,
            )
            return

        if period_type is None:
            messagebox.showwarning(
                "Invalid Assessment Period Information",
                "Please select a valid assessment period type.",
                parent=self,
            )
            return

        period_data = {
            "academic_year_id": academic_year_id,
            "name": self.name_var.get().strip(),
            "period_type": period_type,
            "start_date": self.start_date_var.get().strip(),
            "end_date": self.end_date_var.get().strip(),
            "status": self.current_status,
        }

        try:
            if self.assessment_period:
                update_assessment_period(
                    self.assessment_period["id"],
                    period_data,
                    actor_user_id=self.user["id"],
                )
                message = "Assessment period updated successfully."
            else:
                period_data["status"] = "planned"
                assessment_period_id = create_assessment_period(
                    period_data,
                    actor_user_id=self.user["id"],
                )
                message = (
                    "Assessment period created successfully.\n"
                    f"Assessment Period ID: {assessment_period_id}"
                )

            messagebox.showinfo(
                "Success",
                message,
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Assessment Period Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save assessment period:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.name_var.set("")
        self.period_type_var.set("Midterm")
        self.start_date_var.set("")
        self.end_date_var.set("")

        if not self.assessment_period:
            self.academic_year_var.set("")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
