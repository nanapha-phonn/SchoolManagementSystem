import tkinter as tk
from tkinter import ttk, messagebox

from services.assessment_period_service import get_assessment_periods
from services.student_subject_result_service import (
    get_student_subject_results,
    delete_student_subject_result,
)


class StudentResultListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create=None,
        on_edit=None,
        on_view_report_card=None,
        *,
        user,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit
        self.on_view_report_card = on_view_report_card

        self.search_var = tk.StringVar()
        self.period_var = tk.StringVar(value="All")

        self.periods = {"All": None}
        self.results_by_id = {}

        self.create_widgets()
        self.load_period_options()
        self.load_results()

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="Student Results Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Enter Student Marks",
            command=self.create_result,
        ).pack(side="right")

        ttk.Label(
            self,
            text=(
                "Search and manage student marks by assessment period. "
                "Completed assessment results are locked, but their "
                "report cards remain available."
            ),
            font=("Segoe UI", 10),
            wraplength=950,
        ).pack(anchor="w", pady=(0, 16))

        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=12,
        )
        filters.pack(fill="x", pady=(0, 12))

        ttk.Label(
            filters,
            text="Search:",
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=35,
        )
        search_entry.grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )
        search_entry.bind(
            "<Return>",
            lambda event: self.load_results(),
        )

        ttk.Label(
            filters,
            text="Assessment Period:",
        ).grid(row=0, column=2, padx=(15, 5), pady=5, sticky="w")

        self.period_combo = ttk.Combobox(
            filters,
            textvariable=self.period_var,
            state="readonly",
            width=35,
        )
        self.period_combo.grid(
            row=0, column=3, padx=5, pady=5, sticky="w"
        )
        self.period_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_results(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_results,
        ).grid(row=0, column=4, padx=(15, 5), pady=5)

        ttk.Button(
            filters,
            text="Reset",
            command=self.reset_filters,
        ).grid(row=0, column=5, padx=5, pady=5)

        filters.columnconfigure(1, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "admission_no",
            "student",
            "class_section",
            "subject",
            "assessment",
            "marks",
            "percentage",
            "teacher",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "admission_no": "Admission No.",
            "student": "Student",
            "class_section": "Class / Section",
            "subject": "Subject",
            "assessment": "Assessment",
            "marks": "Marks",
            "percentage": "Percentage",
            "teacher": "Teacher",
            "status": "Period Status",
        }

        widths = {
            "id": 45,
            "admission_no": 105,
            "student": 155,
            "class_section": 110,
            "subject": 130,
            "assessment": 125,
            "marks": 85,
            "percentage": 85,
            "teacher": 145,
            "status": 95,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                minwidth=45,
                anchor="center" if column in ("id", "marks", "percentage") else "w",
            )

        vertical = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        horizontal = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind(
            "<<TreeviewSelect>>",
            lambda event: self.apply_selection_controls(),
        )
        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected(),
        )

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 0))

        self.edit_button = ttk.Button(
            actions,
            text="Edit Marks",
            command=self.edit_selected,
            state="disabled",
        )
        self.edit_button.pack(side="left", padx=(0, 5))

        self.delete_button = ttk.Button(
            actions,
            text="Delete Result",
            command=self.delete_selected,
            state="disabled",
        )
        self.delete_button.pack(side="left", padx=5)

        self.report_button = ttk.Button(
            actions,
            text="View Student Report Card",
            command=self.view_report_card,
            state="disabled",
        )
        self.report_button.pack(side="left", padx=5)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right")

        self.status_label = ttk.Label(
            self,
            text="",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(anchor="w", pady=(8, 0))

    def load_period_options(self):
        try:
            periods = get_assessment_periods(
                actor_user_id=self.user["id"]
            )

            for period in periods:
                label = (
                    f"{period['name']} | "
                    f"{period['academic_year_name']} | "
                    f"{period['status'].title()} "
                    f"[ID:{period['id']}]"
                )
                self.periods[label] = period["id"]

            self.period_combo["values"] = list(self.periods)

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load assessment periods:\n{error}",
                parent=self,
            )

    def load_results(self):
        self.tree.delete(*self.tree.get_children())
        self.results_by_id.clear()

        period_id = self.periods.get(self.period_var.get())

        try:
            results = get_student_subject_results(
                assessment_period_id=period_id,
                search=self.search_var.get().strip(),
            )

            for result in results:
                result_id = result["id"]
                percentage = (
                    float(result["marks_obtained"])
                    * 100.0
                    / float(result["maximum_marks"])
                )

                values = (
                    result_id,
                    result["admission_no"],
                    (
                        f"{result['student_first_name']} "
                        f"{result['student_last_name']}"
                    ),
                    (
                        f"{result['class_name']} / "
                        f"{result['section_name']}"
                    ),
                    (
                        f"{result['subject_code']} - "
                        f"{result['subject_name']}"
                    ),
                    result["assessment_period_name"],
                    (
                        f"{result['marks_obtained']:g} / "
                        f"{result['maximum_marks']:g}"
                    ),
                    f"{percentage:.2f}%",
                    result["teacher_name"],
                    result["assessment_period_status"].title(),
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=str(result_id),
                    values=values,
                )

                self.results_by_id[result_id] = result

            self.status_label.configure(
                text=f"Total results: {len(results)}"
            )

            self.apply_selection_controls()

        except Exception as error:
            self.status_label.configure(
                text="Could not load student results."
            )
            messagebox.showerror(
                "Loading Error",
                str(error),
                parent=self,
            )

    def get_selected_result(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a student result first.",
                parent=self,
            )
            return None

        result_id = int(selection[0])
        return self.results_by_id.get(result_id)

    def apply_selection_controls(self):
        result = None
        selection = self.tree.selection()

        if selection:
            result = self.results_by_id.get(int(selection[0]))

        if not result:
            self.edit_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
            self.report_button.configure(state="disabled")
            return

        is_active = result["assessment_period_status"] == "active"

        self.edit_button.configure(
            state="normal" if is_active else "disabled"
        )
        self.delete_button.configure(
            state="normal" if is_active else "disabled"
        )

        # Reports remain readable after an assessment is completed.
        self.report_button.configure(state="normal")

    def create_result(self):
        if self.on_create:
            self.on_create()

    def edit_selected(self):
        result = self.get_selected_result()

        if not result:
            return

        if result["assessment_period_status"] != "active":
            messagebox.showwarning(
                "Read Only",
                "Only active assessment-period results can be edited.",
                parent=self,
            )
            return

        if self.on_edit:
            self.on_edit(result)

    def delete_selected(self):
        result = self.get_selected_result()

        if not result:
            return

        if result["assessment_period_status"] != "active":
            messagebox.showwarning(
                "Read Only",
                "Completed assessment results cannot be deleted.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Deletion",
            (
                "Delete this student's subject result?\n\n"
                f"Student: {result['student_first_name']} "
                f"{result['student_last_name']}\n"
                f"Subject: {result['subject_name']}\n"
                f"Assessment: {result['assessment_period_name']}"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            delete_student_subject_result(result["id"])

            messagebox.showinfo(
                "Success",
                "Student result deleted successfully.",
                parent=self,
            )

            self.load_results()

        except Exception as error:
            messagebox.showerror(
                "Deletion Error",
                str(error),
                parent=self,
            )

    def view_report_card(self):
        result = self.get_selected_result()

        if not result:
            return

        if self.on_view_report_card:
            self.on_view_report_card(
                result["enrollment_id"],
                result["assessment_period_id"],
            )

    def reset_filters(self):
        self.search_var.set("")
        self.period_var.set("All")
        self.load_results()

    def refresh(self):
        self.load_period_options()
        self.load_results()
