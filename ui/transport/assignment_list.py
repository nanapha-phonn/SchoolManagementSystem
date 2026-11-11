import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.student_transport_assignment_service import (
    get_student_transport_assignments,
    update_student_transport_assignment_status,
)


class StudentTransportAssignmentListFrame(ttk.Frame):

    def __init__(self, master, on_register, on_profile, on_edit):
        super().__init__(master, padding=25)

        self.on_register = on_register
        self.on_profile = on_profile
        self.on_edit = on_edit

        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="All")

        self.assignments = []

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_assignments()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 18))

        ttk.Label(
            header,
            text="Student Transportation",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register students, manage bus assignments and review transportation history.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # SEARCH AND FILTER
    # --------------------------------------------------

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search:",
        ).pack(side="left", padx=(0, 8))

        entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=28,
        )
        entry.pack(side="left", padx=5)

        entry.bind(
            "<Return>",
            lambda event: self.load_assignments(),
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_assignments,
        ).pack(side="left", padx=4)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
        ).pack(side="left", padx=4)

        ttk.Label(
            search_frame,
            text="Status:",
        ).pack(side="left", padx=(15, 5))

        self.status_combo = ttk.Combobox(
            search_frame,
            textvariable=self.status_filter_var,
            values=[
                "All",
                "active",
                "completed",
                "cancelled",
            ],
            state="readonly",
            width=13,
        )
        self.status_combo.pack(side="left", padx=4)

        self.status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_assignments(),
        )

    # --------------------------------------------------
    # ASSIGNMENT TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "admission_no",
            "student",
            "route",
            "pickup",
            "dropoff",
            "start_date",
            "end_date",
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
            "student": "Student Name",
            "route": "Bus Route",
            "pickup": "Pickup Stop",
            "dropoff": "Drop-off Stop",
            "start_date": "Start Date",
            "end_date": "End Date",
            "status": "Status",
        }

        widths = {
            "id": 45,
            "admission_no": 110,
            "student": 135,
            "route": 120,
            "pickup": 130,
            "dropoff": 130,
            "start_date": 100,
            "end_date": 100,
            "status": 90,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=65,
                anchor="center",
                stretch=False,
            )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind(
            "<Double-1>",
            lambda event: self.view_profile(),
        )

    # --------------------------------------------------
    # ACTION BUTTONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Student",
            command=self.on_register,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="View Assignment",
            command=self.view_profile,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Edit Assignment",
            command=self.edit_assignment,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_assignments,
        ).pack(side="right", padx=3)

    # --------------------------------------------------
    # LOAD ASSIGNMENTS
    # --------------------------------------------------

    def load_assignments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.assignments = get_student_transport_assignments(
                self.search_var.get()
            )

            selected_status = self.status_filter_var.get()

            for assignment in self.assignments:
                if (
                    selected_status != "All"
                    and assignment["status"] != selected_status
                ):
                    continue

                student_name = (
                    f'{assignment["student_first_name"]} '
                    f'{assignment["student_last_name"]}'
                )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        assignment["id"],
                        assignment["admission_no"],
                        student_name,
                        (
                            f'{assignment["route_code"]} - '
                            f'{assignment["route_name"]}'
                        ),
                        assignment.get("pickup_stop_name") or "-",
                        assignment.get("dropoff_stop_name") or "-",
                        assignment["start_date"],
                        assignment.get("end_date") or "-",
                        assignment["status"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load transportation assignments:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_assignment_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Assignment Selected",
                "Please select a transportation assignment first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    def view_profile(self):
        assignment_id = self.get_selected_assignment_id()

        if assignment_id is not None:
            self.on_profile(assignment_id)

    def edit_assignment(self):
        assignment_id = self.get_selected_assignment_id()

        if assignment_id is not None:
            self.on_edit(assignment_id)

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def change_status(self):
        assignment_id = self.get_selected_assignment_id()

        if assignment_id is None:
            return

        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, "values")
        current_status = values[8]

        new_status = simpledialog.askstring(
            "Change Assignment Status",
            "Enter status: active, completed, or cancelled",
            initialvalue=current_status,
            parent=self,
        )

        if new_status is None:
            return

        new_status = new_status.strip().lower()

        try:
            update_student_transport_assignment_status(
                assignment_id,
                new_status,
            )

            messagebox.showinfo(
                "Success",
                "Transportation assignment status updated successfully.",
                parent=self,
            )

            self.load_assignments()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Assignment Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Update Error",
                f"Could not update assignment status:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR SEARCH
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.status_filter_var.set("All")
        self.load_assignments()
