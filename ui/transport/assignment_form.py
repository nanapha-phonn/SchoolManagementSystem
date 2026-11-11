import tkinter as tk
from tkinter import ttk, messagebox

from services.student_service import get_students
from services.transport_route_service import get_transport_routes
from services.route_stop_service import get_route_stops

from services.student_transport_assignment_service import (
    create_student_transport_assignment,
    update_student_transport_assignment,
)


class StudentTransportAssignmentForm(ttk.Frame):

    def __init__(
        self,
        master,
        user,
        on_back=None,
        on_saved=None,
        assignment=None,
    ):
        super().__init__(master, padding=25)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")
        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.assignment = assignment

        self.variables = {}

        self.student_choices = {"Select Student": None}
        self.route_choices = {"Select Route": None}
        self.pickup_choices = {"Not selected": None}
        self.dropoff_choices = {"Not selected": None}

        self.students = []
        self.routes = []
        self.stops = []

        self.load_students()
        self.load_routes()

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.assignment:
            self.load_assignment_data()

    # --------------------------------------------------
    # LOAD STUDENTS
    # --------------------------------------------------

    def load_students(self):
        try:
            self.students = get_students(actor_user_id=self.user["id"])

            current_student_id = (
                self.assignment["student_id"]
                if self.assignment
                else None
            )

            self.student_choices = {"Select Student": None}

            for student in self.students:
                # Only active students are offered for new active
                # assignments. Preserve the existing student when editing.
                if (
                    student["status"] != "active"
                    and student["id"] != current_student_id
                ):
                    continue

                label = (
                    f'{student["admission_no"]} - '
                    f'{student["first_name"]} {student["last_name"]}'
                )

                if student["status"] != "active":
                    label += f' ({student["status"]})'

                self.student_choices[label] = student["id"]

        except Exception as error:
            messagebox.showerror(
                "Student Loading Error",
                f"Could not load students:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # LOAD ROUTES
    # --------------------------------------------------

    def load_routes(self):
        try:
            self.routes = get_transport_routes()

            current_route_id = (
                self.assignment["route_id"]
                if self.assignment
                else None
            )

            self.route_choices = {"Select Route": None}

            for route in self.routes:
                # New active assignments should use active routes.
                # Preserve the current route when editing a historical
                # assignment.
                if (
                    route["status"] != "active"
                    and route["id"] != current_route_id
                ):
                    continue

                label = (
                    f'{route["route_code"]} - {route["route_name"]}'
                )

                if route["status"] != "active":
                    label += f' ({route["status"]})'

                self.route_choices[label] = route["id"]

        except Exception as error:
            messagebox.showerror(
                "Route Loading Error",
                f"Could not load transport routes:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Student Transport Assignment"
            if self.assignment
            else "Student Transport Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Assign a student to a bus route and select pickup/drop-off stops.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Transportation Assignment Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # Student
        ttk.Label(
            form,
            text="Student",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.student_var = tk.StringVar(value="Select Student")

        self.student_combo = ttk.Combobox(
            form,
            textvariable=self.student_var,
            values=list(self.student_choices.keys()),
            state="readonly",
        )
        self.student_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Route
        ttk.Label(
            form,
            text="Bus Route",
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.route_var = tk.StringVar(value="Select Route")

        self.route_combo = ttk.Combobox(
            form,
            textvariable=self.route_var,
            values=list(self.route_choices.keys()),
            state="readonly",
        )
        self.route_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        self.route_combo.bind(
            "<<ComboboxSelected>>",
            self.on_route_changed,
        )

        # Pickup stop
        ttk.Label(
            form,
            text="Pickup Stop",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.pickup_var = tk.StringVar(value="Not selected")

        self.pickup_combo = ttk.Combobox(
            form,
            textvariable=self.pickup_var,
            values=["Not selected"],
            state="readonly",
        )
        self.pickup_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Drop-off stop
        ttk.Label(
            form,
            text="Drop-off Stop",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.dropoff_var = tk.StringVar(value="Not selected")

        self.dropoff_combo = ttk.Combobox(
            form,
            textvariable=self.dropoff_var,
            values=["Not selected"],
            state="readonly",
        )
        self.dropoff_combo.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Start date
        self.create_entry_field(
            form,
            "Start Date (YYYY-MM-DD)",
            "start_date",
            2,
            0,
        )

        # End date
        self.create_entry_field(
            form,
            "End Date (Optional)",
            "end_date",
            2,
            2,
        )

        # Assignment status: editable only for an existing assignment.
        ttk.Label(
            form,
            text="Assignment Status",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.variables["status"] = tk.StringVar(
            value="active"
        )

        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.variables["status"],
            values=["active", "completed", "cancelled"],
            state="readonly",
        )

        self.status_combo.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        if not self.assignment:
            self.status_combo.configure(state="disabled")

        ttk.Label(
            form,
            text="Active assignments require an active student and route.",
            font=("Segoe UI", 9),
        ).grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 5),
        )

    def create_entry_field(
        self,
        parent,
        label,
        field_name,
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
            padx=8,
            pady=10,
        )

        variable = tk.StringVar()
        self.variables[field_name] = variable

        ttk.Entry(
            parent,
            textvariable=variable,
            width=25,
        ).grid(
            row=row,
            column=column + 1,
            sticky="ew",
            padx=8,
            pady=10,
        )

    # --------------------------------------------------
    # ROUTE STOP OPTIONS
    # --------------------------------------------------

    def on_route_changed(self, event=None):
        self.load_stop_options()

    def load_stop_options(
        self,
        pickup_stop_id=None,
        dropoff_stop_id=None,
    ):
        self.pickup_choices = {"Not selected": None}
        self.dropoff_choices = {"Not selected": None}

        selected_route = self.route_var.get()
        route_id = self.route_choices.get(selected_route)

        self.stops = []

        if route_id is not None:
            try:
                self.stops = get_route_stops(route_id)

                for stop in self.stops:
                    label = (
                        f'{stop["stop_order"]}. {stop["stop_name"]}'
                    )

                    if stop.get("pickup_time"):
                        label += f' ({stop["pickup_time"]})'

                    self.pickup_choices[label] = stop["id"]
                    self.dropoff_choices[label] = stop["id"]

            except Exception as error:
                messagebox.showerror(
                    "Stop Loading Error",
                    f"Could not load route stops:\n{error}",
                    parent=self,
                )

        self.pickup_combo.configure(
            values=list(self.pickup_choices.keys())
        )

        self.dropoff_combo.configure(
            values=list(self.dropoff_choices.keys())
        )

        self.pickup_var.set("Not selected")
        self.dropoff_var.set("Not selected")

        # Restore existing stop selections during editing.
        for label, stop_id in self.pickup_choices.items():
            if stop_id == pickup_stop_id and stop_id is not None:
                self.pickup_var.set(label)
                break

        for label, stop_id in self.dropoff_choices.items():
            if stop_id == dropoff_stop_id and stop_id is not None:
                self.dropoff_var.set(label)
                break

    # --------------------------------------------------
    # LOAD EXISTING ASSIGNMENT
    # --------------------------------------------------

    def load_assignment_data(self):
        student_id = self.assignment["student_id"]

        for label, selected_id in self.student_choices.items():
            if selected_id == student_id:
                self.student_var.set(label)
                break

        route_id = self.assignment["route_id"]

        for label, selected_id in self.route_choices.items():
            if selected_id == route_id:
                self.route_var.set(label)
                break

        self.variables["start_date"].set(
            self.assignment.get("start_date") or ""
        )

        self.variables["end_date"].set(
            self.assignment.get("end_date") or ""
        )

        self.variables["status"].set(
            self.assignment.get("status") or "active"
        )

        self.load_stop_options(
            pickup_stop_id=self.assignment.get("pickup_stop_id"),
            dropoff_stop_id=self.assignment.get("dropoff_stop_id"),
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Assignment"
            if self.assignment
            else "Register Assignment"
        )

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_assignment,
        ).pack(side="right", padx=5)

        if not self.assignment:
            ttk.Button(
                buttons,
                text="Clear Form",
                command=self.clear_form,
            ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Assignments",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_assignment(self):
        student_label = self.student_var.get()
        route_label = self.route_var.get()
        pickup_label = self.pickup_var.get()
        dropoff_label = self.dropoff_var.get()

        student_id = self.student_choices.get(student_label)
        route_id = self.route_choices.get(route_label)

        if student_id is None:
            messagebox.showwarning(
                "Student Required",
                "Please select a student.",
                parent=self,
            )
            return

        if route_id is None:
            messagebox.showwarning(
                "Route Required",
                "Please select a bus route.",
                parent=self,
            )
            return

        assignment_data = {
            "student_id": student_id,
            "route_id": route_id,
            "pickup_stop_id": self.pickup_choices.get(pickup_label),
            "dropoff_stop_id": self.dropoff_choices.get(dropoff_label),
            "start_date": self.variables["start_date"].get().strip(),
            "end_date": self.variables["end_date"].get().strip() or None,
            "status": self.variables["status"].get(),
        }

        try:
            if self.assignment:
                update_student_transport_assignment(
                    self.assignment["id"],
                    assignment_data,
                )

                message = "Student transport assignment updated successfully."

            else:
                assignment_id = create_student_transport_assignment(
                    assignment_data
                )

                message = (
                    "Student transport assignment registered successfully.\n"
                    f"Assignment ID: {assignment_id}"
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
                "Invalid Assignment",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Assignment Error",
                f"Could not save transport assignment:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR / BACK
    # --------------------------------------------------

    def clear_form(self):
        self.student_var.set("Select Student")
        self.route_var.set("Select Route")

        self.pickup_choices = {"Not selected": None}
        self.dropoff_choices = {"Not selected": None}

        self.pickup_combo.configure(values=["Not selected"])
        self.dropoff_combo.configure(values=["Not selected"])

        self.pickup_var.set("Not selected")
        self.dropoff_var.set("Not selected")

        self.variables["start_date"].set("")
        self.variables["end_date"].set("")
        self.variables["status"].set("active")

    def go_back(self):
        if self.on_back:
            self.on_back()
