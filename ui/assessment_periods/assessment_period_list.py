import tkinter as tk
from tkinter import ttk, messagebox

from services.academic_year_service import get_academic_years
from services.assessment_period_service import (
    get_assessment_periods,
    update_assessment_period_status,
)


class AssessmentPeriodListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create=None,
        on_edit=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()
        self.academic_year_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")

        self.academic_year_id_by_label = {"All": None}

        self.create_widgets()
        self.load_academic_year_options()
        self.load_assessment_periods()

    # --------------------------------------------------
    # WIDGETS
    # --------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Assessment Period Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Create Assessment Period",
            command=self.create_assessment_period,
        ).pack(side="right")

        ttk.Label(
            self,
            text=(
                "Manage assessment periods within academic years. "
                "Periods cannot overlap or be permanently deleted. "
                "Completed periods are locked."
            ),
            font=("Segoe UI", 10),
            wraplength=900,
        ).pack(anchor="w", pady=(0, 18))

        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=12,
        )
        filters.pack(fill="x", pady=(0, 12))

        ttk.Label(
            filters,
            text="Search:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=28,
        )
        search_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=5,
            pady=5,
        )
        search_entry.bind(
            "<Return>",
            lambda event: self.load_assessment_periods(),
        )

        ttk.Label(
            filters,
            text="Academic Year:",
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(15, 5),
            pady=5,
        )

        self.academic_year_combo = ttk.Combobox(
            filters,
            textvariable=self.academic_year_var,
            state="readonly",
            width=27,
        )
        self.academic_year_combo.grid(
            row=0,
            column=3,
            sticky="w",
            padx=5,
            pady=5,
        )
        self.academic_year_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_assessment_periods(),
        )

        ttk.Label(
            filters,
            text="Status:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        self.status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=("All", "Planned", "Active", "Completed"),
            state="readonly",
            width=15,
        )
        self.status_combo.grid(
            row=1,
            column=1,
            sticky="w",
            padx=5,
            pady=5,
        )
        self.status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_assessment_periods(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_assessment_periods,
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=5,
            pady=5,
        )

        ttk.Button(
            filters,
            text="Reset Filters",
            command=self.reset_filters,
        ).grid(
            row=1,
            column=3,
            sticky="w",
            padx=5,
            pady=5,
        )

        filters.columnconfigure(1, weight=1)

        self.create_table()
        self.create_actions()

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "name",
            "period_type",
            "academic_year",
            "start_date",
            "end_date",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=16,
        )

        headings = {
            "id": "ID",
            "name": "Assessment Period",
            "period_type": "Type",
            "academic_year": "Academic Year",
            "start_date": "Start Date",
            "end_date": "End Date",
            "status": "Status",
        }

        widths = {
            "id": 55,
            "name": 210,
            "period_type": 105,
            "academic_year": 140,
            "start_date": 115,
            "end_date": 115,
            "status": 100,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected(),
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Edit Selected",
            command=self.edit_selected,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Activate",
            command=lambda: self.change_status("active"),
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Complete",
            command=lambda: self.change_status("completed"),
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # ACADEMIC YEAR FILTER
    # --------------------------------------------------

    def load_academic_year_options(self):
        selected_label = self.academic_year_var.get()

        self.academic_year_id_by_label = {"All": None}
        labels = ["All"]

        try:
            academic_years = get_academic_years(actor_user_id=self.user['id'])

            for year in academic_years:
                year_id = int(year["id"])
                label = (
                    f'{year["name"]} '
                    f'({year["start_date"]} to {year["end_date"]})'
                )

                self.academic_year_id_by_label[label] = year_id
                labels.append(label)

            self.academic_year_combo["values"] = labels

            if selected_label in self.academic_year_id_by_label:
                self.academic_year_var.set(selected_label)
            else:
                self.academic_year_var.set("All")

        except Exception as error:
            self.academic_year_combo["values"] = labels
            self.academic_year_var.set("All")

            messagebox.showerror(
                "Loading Error",
                f"Could not load academic-year filters:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_assessment_periods(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_year_label = self.academic_year_var.get()
        academic_year_id = self.academic_year_id_by_label.get(
            selected_year_label
        )

        selected_status = self.status_var.get()
        status = (
            None
            if selected_status == "All"
            else selected_status.lower()
        )

        try:
            periods = get_assessment_periods(
                academic_year_id=academic_year_id,
                status=status,
                search=self.search_var.get().strip(),
                actor_user_id=self.user["id"],
            )

            for period in periods:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        period["id"],
                        period["name"],
                        period["period_type"].capitalize(),
                        period["academic_year_name"],
                        period["start_date"],
                        period["end_date"],
                        period["status"].capitalize(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load assessment periods:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_assessment_period(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select an assessment period first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return {
            "id": int(values[0]),
            "name": values[1],
            "period_type": values[2],
            "academic_year_name": values[3],
            "start_date": values[4],
            "end_date": values[5],
            "status": str(values[6]).lower(),
        }

    # --------------------------------------------------
    # CREATE / EDIT
    # --------------------------------------------------

    def create_assessment_period(self):
        if self.on_create:
            self.on_create()

    def edit_selected(self):
        period = self.get_selected_assessment_period()

        if period is not None and self.on_edit:
            self.on_edit(period["id"])

    # --------------------------------------------------
    # STATUS TRANSITIONS
    # --------------------------------------------------

    def change_status(self, new_status):
        period = self.get_selected_assessment_period()

        if period is None:
            return

        allowed_transitions = {
            "planned": "active",
            "active": "completed",
        }

        current_status = period["status"]

        if allowed_transitions.get(current_status) != new_status:
            if current_status == "completed":
                message = (
                    "Completed assessment periods are permanently locked."
                )
            elif new_status == "active":
                message = (
                    "Only planned assessment periods can be activated."
                )
            else:
                message = (
                    "Only active assessment periods can be completed."
                )

            messagebox.showwarning(
                "Invalid Status Transition",
                message,
                parent=self,
            )
            return

        action = (
            "activate"
            if new_status == "active"
            else "complete"
        )

        confirmed = messagebox.askyesno(
            "Confirm Assessment Period Status",
            (
                f"Are you sure you want to {action} this assessment period?\n\n"
                f'Period: {period["name"]}\n'
                f'Academic Year: {period["academic_year_name"]}\n'
                f'Status: {current_status.capitalize()} → '
                f'{new_status.capitalize()}\n\n'
                "This status transition cannot be reversed."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            update_assessment_period_status(
                period["id"],
                new_status,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                f"Assessment period {action}d successfully.",
                parent=self,
            )

            self.load_assessment_periods()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Change Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not change assessment period status:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # FILTERS / REFRESH
    # --------------------------------------------------

    def reset_filters(self):
        self.search_var.set("")
        self.academic_year_var.set("All")
        self.status_var.set("All")
        self.load_assessment_periods()

    def refresh(self):
        self.load_academic_year_options()
        self.load_assessment_periods()
