import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.teacher_service import get_teachers
from services.subject_service import get_subjects
from services.section_service import get_sections
from services.academic_year_service import get_academic_years
from services.teacher_subject_assignment_service import (
    get_teacher_subject_assignments,
    get_teacher_subject_assignment,
    end_teacher_subject_assignment,
)


class TeacherSubjectAssignmentListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create=None,
        on_reassign=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_reassign = on_reassign

        self.search_var = tk.StringVar()
        self.teacher_var = tk.StringVar(value="All")
        self.subject_var = tk.StringVar(value="All")
        self.section_var = tk.StringVar(value="All")
        self.year_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")

        self.teacher_id_by_label = {}
        self.subject_id_by_label = {}
        self.section_id_by_label = {}
        self.year_id_by_label = {}

        self.load_reference_data()
        self.create_widgets()
        self.load_assignments()

    # --------------------------------------------------
    # REFERENCE DATA
    # --------------------------------------------------

    def load_reference_data(self):
        try:
            for teacher in get_teachers(actor_user_id=self.user["id"]):
                label = (
                    f'{teacher["employee_no"]} - '
                    f'{teacher["first_name"]} '
                    f'{teacher["last_name"]}'
                )
                self.teacher_id_by_label[label] = int(
                    teacher["id"]
                )

            for subject in get_subjects(
                actor_user_id=self.user["id"]
            ):
                label = (
                    f'{subject["subject_code"]} - '
                    f'{subject["name"]}'
                )
                self.subject_id_by_label[label] = int(
                    subject["id"]
                )

            for section in get_sections(
                actor_user_id=self.user["id"]
            ):
                label = (
                    f'{section["class_name"]} - '
                    f'{section["name"]}'
                )
                self.section_id_by_label[label] = int(
                    section["id"]
                )

            for year in get_academic_years():
                label = (
                    year["name"]
                    + (
                        " (Current)"
                        if year["is_current"]
                        else ""
                    )
                )
                self.year_id_by_label[label] = int(
                    year["id"]
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load assignment filters:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # WIDGETS
    # --------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Teacher–Subject Assignments",
            font=("Segoe UI", 20, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ New Assignment",
            command=self.create_assignment,
        ).pack(side="right")

        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=12,
        )
        filters.pack(fill="x", pady=(0, 12))

        ttk.Label(filters, text="Search:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=28,
        )
        search_entry.grid(
            row=0, column=1, sticky="ew", padx=5, pady=5
        )
        search_entry.bind(
            "<Return>",
            lambda event: self.load_assignments(),
        )

        self._add_filter(
            filters, "Teacher:", self.teacher_var,
            list(self.teacher_id_by_label.keys()), 0, 2
        )
        self._add_filter(
            filters, "Subject:", self.subject_var,
            list(self.subject_id_by_label.keys()), 0, 4
        )
        self._add_filter(
            filters, "Class / Section:", self.section_var,
            list(self.section_id_by_label.keys()), 1, 0
        )
        self._add_filter(
            filters, "Academic Year:", self.year_var,
            list(self.year_id_by_label.keys()), 1, 2
        )
        self._add_filter(
            filters, "Status:", self.status_var,
            ["Active", "Inactive"], 1, 4
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_assignments,
        ).grid(row=0, column=6, padx=5, pady=5)

        ttk.Button(
            filters,
            text="Reset",
            command=self.reset_filters,
        ).grid(row=1, column=6, padx=5, pady=5)

        filters.columnconfigure(1, weight=1)
        filters.columnconfigure(3, weight=1)
        filters.columnconfigure(5, weight=1)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "teacher",
            "subject",
            "class",
            "section",
            "academic_year",
            "assigned_on",
            "ended_on",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=16,
        )

        headings = {
            "id": "ID",
            "teacher": "Teacher",
            "subject": "Subject",
            "class": "Class",
            "section": "Section",
            "academic_year": "Academic Year",
            "assigned_on": "Assigned On",
            "ended_on": "Ended On",
            "status": "Status",
        }

        widths = {
            "id": 55,
            "teacher": 170,
            "subject": 170,
            "class": 100,
            "section": 90,
            "academic_year": 120,
            "assigned_on": 110,
            "ended_on": 110,
            "status": 85,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="w",
            )

        scrollbar_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar_x = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="End Assignment",
            command=self.end_selected_assignment,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="Reassign Teacher",
            command=self.reassign_selected_assignment,
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_assignments,
        ).pack(side="right")

    def _add_filter(
        self,
        parent,
        label,
        variable,
        values,
        row,
        column,
    ):
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=column,
            sticky="w",
            padx=5,
            pady=5,
        )

        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=["All"] + values,
            state="readonly",
            width=19,
        )
        combo.grid(
            row=row,
            column=column + 1,
            sticky="ew",
            padx=5,
            pady=5,
        )
        combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_assignments(),
        )

        return combo

    # --------------------------------------------------
    # LOAD ASSIGNMENTS
    # --------------------------------------------------

    def load_assignments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

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
            self.year_var.get()
        )

        selected_status = self.status_var.get()
        status = (
            None
            if selected_status == "All"
            else selected_status.lower()
        )

        try:
            assignments = get_teacher_subject_assignments(
                search=self.search_var.get().strip(),
                teacher_id=teacher_id,
                subject_id=subject_id,
                section_id=section_id,
                academic_year_id=academic_year_id,
                status=status,
                actor_user_id=self.user["id"],
            )

            for assignment in assignments:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        assignment["id"],
                        assignment["teacher_name"],
                        (
                            f'{assignment["subject_code"]} - '
                            f'{assignment["subject_name"]}'
                        ),
                        assignment["class_name"],
                        assignment["section_name"],
                        assignment["academic_year_name"],
                        assignment["assigned_on"],
                        assignment["ended_on"] or "",
                        assignment["status"].capitalize(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not load assignments:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_assignment_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select an assignment first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    def get_selected_assignment(self):
        assignment_id = self.get_selected_assignment_id()

        if assignment_id is None:
            return None

        try:
            assignment = get_teacher_subject_assignment(
                assignment_id,
                actor_user_id=self.user["id"],
            )

            if not assignment:
                messagebox.showwarning(
                    "Not Found",
                    "The selected assignment could not be found.",
                    parent=self,
                )
                self.load_assignments()
                return None

            return assignment

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not load assignment:\n{error}",
                parent=self,
            )
            return None

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_assignment(self):
        if self.on_create:
            self.on_create()

    def end_selected_assignment(self):
        assignment = self.get_selected_assignment()

        if assignment is None:
            return

        if assignment["status"] != "active":
            messagebox.showwarning(
                "Already Ended",
                "Only active assignments can be ended.",
                parent=self,
            )
            return

        ended_on = simpledialog.askstring(
            "End Assignment",
            "Enter the assignment end date (YYYY-MM-DD):",
            initialvalue="",
            parent=self,
        )

        if ended_on is None:
            return

        ended_on = ended_on.strip()

        confirmed = messagebox.askyesno(
            "Confirm End Assignment",
            (
                "End this teacher–subject assignment?\n\n"
                f'Teacher: {assignment["teacher_name"]}\n'
                f'Subject: {assignment["subject_name"]}\n'
                f"End date: {ended_on}"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            end_teacher_subject_assignment(
                assignment["id"],
                ended_on,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                "Assignment ended successfully.",
                parent=self,
            )

            self.load_assignments()

        except ValueError as error:
            messagebox.showwarning(
                "Validation Error",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not end assignment:\n{error}",
                parent=self,
            )

    def reassign_selected_assignment(self):
        assignment = self.get_selected_assignment()

        if assignment is None:
            return

        if assignment["status"] != "active":
            messagebox.showwarning(
                "Already Ended",
                "Only active assignments can be reassigned.",
                parent=self,
            )
            return

        if self.on_reassign:
            self.on_reassign(assignment["id"])

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    def reset_filters(self):
        self.search_var.set("")
        self.teacher_var.set("All")
        self.subject_var.set("All")
        self.section_var.set("All")
        self.year_var.set("All")
        self.status_var.set("All")
        self.load_assignments()
