from tkinter import ttk, messagebox

from services.student_transport_assignment_service import (
    get_student_transport_assignments_by_student,
)


class StudentTransportAssignmentProfile(ttk.Frame):

    def __init__(self, master, assignment, on_back, on_edit):
        super().__init__(master, padding=25)

        self.assignment = assignment
        self.on_back = on_back
        self.on_edit = on_edit

        self.create_header()
        self.create_details()
        self.create_history()
        self.create_buttons()

        self.load_history()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 15))

        ttk.Label(
            header,
            text="Student Transportation Profile",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="View assignment details and the student's transportation history.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # ASSIGNMENT DETAILS
    # --------------------------------------------------

    def create_details(self):
        details_frame = ttk.Frame(self)
        details_frame.pack(fill="x", pady=(0, 15))

        student_frame = ttk.LabelFrame(
            details_frame,
            text="Student Information",
            padding=15,
        )
        student_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 7),
        )

        assignment_frame = ttk.LabelFrame(
            details_frame,
            text="Assignment Information",
            padding=15,
        )
        assignment_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(7, 0),
        )

        student_name = (
            f'{self.assignment.get("student_first_name") or ""} '
            f'{self.assignment.get("student_last_name") or ""}'
        ).strip()

        student_details = [
            ("Admission Number", self.assignment.get("admission_no")),
            ("Student Name", student_name),
            ("Student ID", self.assignment.get("student_id")),
        ]

        assignment_details = [
            ("Assignment ID", self.assignment.get("id")),
            ("Route Code", self.assignment.get("route_code")),
            ("Route Name", self.assignment.get("route_name")),
            ("Pickup Stop", self.assignment.get("pickup_stop_name")),
            ("Drop-off Stop", self.assignment.get("dropoff_stop_name")),
            ("Start Date", self.assignment.get("start_date")),
            ("End Date", self.assignment.get("end_date")),
            ("Status", self.assignment.get("status")),
            ("Registration Date", self.assignment.get("created_at")),
        ]

        self.add_detail_labels(student_frame, student_details)
        self.add_detail_labels(assignment_frame, assignment_details)

    @staticmethod
    def add_detail_labels(container, details):
        for row, (label, value) in enumerate(details):
            ttk.Label(
                container,
                text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row,
                column=0,
                sticky="nw",
                padx=5,
                pady=6,
            )

            ttk.Label(
                container,
                text=str(value) if value not in (None, "") else "-",
                font=("Segoe UI", 9),
                wraplength=230,
            ).grid(
                row=row,
                column=1,
                sticky="nw",
                padx=5,
                pady=6,
            )

        container.columnconfigure(1, weight=1)

    # --------------------------------------------------
    # TRANSPORTATION HISTORY
    # --------------------------------------------------

    def create_history(self):
        history_frame = ttk.LabelFrame(
            self,
            text="Student Transportation History",
            padding=12,
        )
        history_frame.pack(fill="both", expand=True)

        ttk.Label(
            history_frame,
            text="All current and previous transportation assignments for this student.",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(history_frame)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "route_code",
            "route_name",
            "pickup",
            "dropoff",
            "start_date",
            "end_date",
            "status",
        )

        self.history_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "Assignment ID",
            "route_code": "Route Code",
            "route_name": "Route Name",
            "pickup": "Pickup Stop",
            "dropoff": "Drop-off Stop",
            "start_date": "Start Date",
            "end_date": "End Date",
            "status": "Status",
        }

        widths = {
            "id": 90,
            "route_code": 110,
            "route_name": 130,
            "pickup": 130,
            "dropoff": 130,
            "start_date": 100,
            "end_date": 100,
            "status": 90,
        }

        for column in columns:
            self.history_tree.heading(
                column,
                text=headings[column],
            )

            self.history_tree.column(
                column,
                width=widths[column],
                minwidth=70,
                anchor="center",
                stretch=False,
            )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.history_tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.history_tree.xview,
        )

        self.history_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.history_tree.grid(
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

        self.history_count_label = ttk.Label(
            history_frame,
            text="Transportation records: 0",
            font=("Segoe UI", 9),
        )
        self.history_count_label.pack(anchor="w", pady=(8, 0))

    # --------------------------------------------------
    # LOAD HISTORY
    # --------------------------------------------------

    def load_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        try:
            history = get_student_transport_assignments_by_student(
                self.assignment["student_id"]
            )

            for record in history:
                self.history_tree.insert(
                    "",
                    "end",
                    values=(
                        record["id"],
                        record["route_code"],
                        record["route_name"],
                        record.get("pickup_stop_name") or "-",
                        record.get("dropoff_stop_name") or "-",
                        record["start_date"],
                        record.get("end_date") or "-",
                        record["status"],
                    ),
                )

            self.history_count_label.configure(
                text=f"Transportation records: {len(history)}"
            )

        except Exception as error:
            messagebox.showerror(
                "History Loading Error",
                f"Could not load student transportation history:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # NAVIGATION BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=15)

        ttk.Button(
            buttons,
            text="Back to Assignments",
            command=self.on_back,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Edit Assignment",
            command=self.on_edit,
        ).pack(side="right", padx=5)
