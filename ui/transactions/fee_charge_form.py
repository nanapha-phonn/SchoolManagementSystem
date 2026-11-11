import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation

from services.student_service import get_students
from services.student_transport_assignment_service import (
    get_student_transport_assignments,
)
from services.fee_charge_service import (
    create_fee_charge,
    get_fee_charge,
)


class FeeChargeForm(ttk.Frame):

    def __init__(
        self,
        master,
        user,
        on_back=None,
        on_saved=None,
    ):
        super().__init__(master, padding=25)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved

        self.students = []
        self.assignments = []

        self.student_choices = {"Select Student": None}
        self.assignment_choices = {"Not selected": None}

        self.create_header()
        self.load_reference_data()
        self.create_form()
        self.create_buttons()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="Register Fee Charge",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Create a class, hostel or bus fee charge for a student.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # REFERENCE DATA
    # --------------------------------------------------

    def load_reference_data(self):
        try:
            self.students = get_students(actor_user_id=self.user["id"])

            self.student_choices = {"Select Student": None}

            for student in self.students:
                label = (
                    f'{student["admission_no"]} - '
                    f'{student["first_name"]} {student["last_name"]}'
                )

                if student["status"] != "active":
                    label += f' ({student["status"]})'

                self.student_choices[label] = student["id"]

            self.assignments = get_student_transport_assignments()

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load student or transport records:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Fee Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # Student
        ttk.Label(
            form,
            text="Student",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=10)

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

        # Fee type
        ttk.Label(
            form,
            text="Fee Type",
        ).grid(row=0, column=2, sticky="w", padx=8, pady=10)

        self.fee_type_var = tk.StringVar(value="class")

        self.fee_type_combo = ttk.Combobox(
            form,
            textvariable=self.fee_type_var,
            values=["class", "hostel", "bus"],
            state="readonly",
        )
        self.fee_type_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        self.student_combo.bind(
            "<<ComboboxSelected>>",
            self.on_student_changed,
        )

        self.fee_type_combo.bind(
            "<<ComboboxSelected>>",
            self.on_fee_type_changed,
        )

        # Description
        ttk.Label(
            form,
            text="Description",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=10)

        self.description_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=self.description_var,
        ).grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Amount
        ttk.Label(
            form,
            text="Amount",
        ).grid(row=2, column=0, sticky="w", padx=8, pady=10)

        self.amount_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=self.amount_var,
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Currency
        ttk.Label(
            form,
            text="Currency",
        ).grid(row=2, column=2, sticky="w", padx=8, pady=10)

        self.currency_var = tk.StringVar(value="USD")

        ttk.Combobox(
            form,
            textvariable=self.currency_var,
            values=["USD", "KHR"],
            state="readonly",
        ).grid(
            row=2,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Due date
        ttk.Label(
            form,
            text="Due Date (YYYY-MM-DD)",
        ).grid(row=3, column=0, sticky="w", padx=8, pady=10)

        self.due_date_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=self.due_date_var,
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Transport assignment
        ttk.Label(
            form,
            text="Transport Assignment",
        ).grid(row=3, column=2, sticky="w", padx=8, pady=10)

        self.assignment_var = tk.StringVar(value="Not selected")

        self.assignment_combo = ttk.Combobox(
            form,
            textvariable=self.assignment_var,
            values=["Not selected"],
            state="disabled",
        )
        self.assignment_combo.grid(
            row=3,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Information
        self.assignment_info = ttk.Label(
            form,
            text="Only required for bus fees.",
            font=("Segoe UI", 9),
        )
        self.assignment_info.grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 5),
        )

        self.update_assignment_state()

    # --------------------------------------------------
    # TRANSPORT ASSIGNMENTS
    # --------------------------------------------------

    def refresh_assignment_choices(self):
        student_id = self.student_choices.get(
            self.student_var.get()
        )

        self.assignment_choices = {"Select Assignment": None}

        if student_id is not None:
            for assignment in self.assignments:
                if (
                    assignment["student_id"] == student_id
                    and assignment["status"] == "active"
                ):
                    label = (
                        f'{assignment["route_code"]} - '
                        f'{assignment["route_name"]} | '
                        f'Start: {assignment["start_date"]} | '
                        f'Assignment #{assignment["id"]}'
                    )

                    self.assignment_choices[label] = assignment["id"]

        self.assignment_combo.configure(
            values=list(self.assignment_choices.keys())
        )

        self.assignment_var.set(
            "Select Assignment"
            if len(self.assignment_choices) > 1
            else "No active assignment available"
        )

    def update_assignment_state(self):
        if self.fee_type_var.get() == "bus":
            self.refresh_assignment_choices()

            self.assignment_combo.configure(state="readonly")

            if len(self.assignment_choices) <= 1:
                self.assignment_info.configure(
                    text="No active transport assignment exists for this student."
                )
            else:
                self.assignment_info.configure(
                    text="Select the student's active transport assignment."
                )
        else:
            self.assignment_var.set("Not required")
            self.assignment_combo.configure(state="disabled")

            self.assignment_info.configure(
                text=(
                    "Class fees are linked directly to the student. "
                    "Hostel fees are also student-level charges."
                )
            )

    def on_student_changed(self, event=None):
        self.update_assignment_state()

    def on_fee_type_changed(self, event=None):
        self.update_assignment_state()

    # --------------------------------------------------
    # AMOUNT CONVERSION
    # --------------------------------------------------

    def convert_amount_to_minor_units(self):
        raw_amount = self.amount_var.get().strip()

        if not raw_amount:
            raise ValueError("Fee amount is required.")

        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            raise ValueError("Enter a valid fee amount.")

        if not amount.is_finite() or amount <= 0:
            raise ValueError("Fee amount must be greater than zero.")

        currency = self.currency_var.get()

        if currency == "USD":
            scaled_amount = amount * 100

            if scaled_amount != scaled_amount.to_integral_value():
                raise ValueError(
                    "USD amounts can have no more than two decimal places."
                )

        elif currency == "KHR":
            if amount != amount.to_integral_value():
                raise ValueError(
                    "KHR amounts must be entered as whole riel."
                )

            scaled_amount = amount

        else:
            raise ValueError("Unsupported currency.")

        amount_minor = int(scaled_amount)

        if amount_minor > 9223372036854775807:
            raise ValueError("Fee amount exceeds the supported range.")

        return amount_minor

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    def save_charge(self):
        try:
            student_id = self.student_choices.get(
                self.student_var.get()
            )

            if student_id is None:
                raise ValueError("Please select a student.")

            fee_type = self.fee_type_var.get()

            charge_data = {
                "student_id": student_id,
                "fee_type": fee_type,
                "description": self.description_var.get(),
                "amount_minor": self.convert_amount_to_minor_units(),
                "currency": self.currency_var.get(),
                "due_date": self.due_date_var.get().strip(),
            }

            if fee_type == "bus":
                assignment_id = self.assignment_choices.get(
                    self.assignment_var.get()
                )

                if assignment_id is None:
                    raise ValueError(
                        "Select an active transport assignment "
                        "for this bus fee."
                    )

                charge_data["transport_assignment_id"] = assignment_id

            charge_id = create_fee_charge(
                charge_data,
                actor_user_id=self.user["id"],
            )
            charge = get_fee_charge(
                charge_id,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Fee Charge Created",
                (
                    "Fee charge created successfully.\n\n"
                    f'Charge Number: {charge["charge_no"]}\n'
                    f'Student: {charge["first_name"]} '
                    f'{charge["last_name"]}'
                ),
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Fee Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not create fee charge:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        ttk.Button(
            button_frame,
            text="Save Fee Charge",
            command=self.save_charge,
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Fee Records",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.student_var.set("Select Student")
        self.fee_type_var.set("class")
        self.description_var.set("")
        self.amount_var.set("")
        self.currency_var.set("USD")
        self.due_date_var.set("")

        self.update_assignment_state()

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
