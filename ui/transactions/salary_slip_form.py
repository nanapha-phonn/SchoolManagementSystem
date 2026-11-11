import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation

from services.teacher_service import get_teachers
from services.transport_staff_service import get_transport_staff_list
from services.salary_slip_service import create_salary_slip


class SalarySlipForm(ttk.Frame):

    def __init__(
        self,
        master,
        *,
        user,
        on_back=None,
        on_saved=None,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved

        self.employee_choices = {"Select Employee": None}
        self.employees = []

        self.create_header()
        self.create_form()
        self.load_employees()
        self.create_buttons()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="Create Salary Slip",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Prepare a salary slip for a teacher or transport employee.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Employee and Payroll Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(
            form,
            text="Employee Type",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=10)

        self.employee_type_var = tk.StringVar(value="teacher")

        self.employee_type_combo = ttk.Combobox(
            form,
            textvariable=self.employee_type_var,
            values=["teacher", "transport_staff"],
            state="readonly",
        )
        self.employee_type_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )
        self.employee_type_combo.bind(
            "<<ComboboxSelected>>",
            self.on_employee_type_changed,
        )

        ttk.Label(
            form,
            text="Employee",
        ).grid(row=0, column=2, sticky="w", padx=8, pady=10)

        self.employee_var = tk.StringVar(value="Select Employee")

        self.employee_combo = ttk.Combobox(
            form,
            textvariable=self.employee_var,
            values=["Select Employee"],
            state="readonly",
        )
        self.employee_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        self.employee_info = ttk.Label(
            form,
            text="Select an employee to prepare a salary slip.",
            font=("Segoe UI", 9),
        )
        self.employee_info.grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 8),
        )

        self.pay_period_start_var = tk.StringVar()
        self.pay_period_end_var = tk.StringVar()

        self.create_entry(
            form,
            "Pay Period Start (YYYY-MM-DD)",
            self.pay_period_start_var,
            2,
            0,
        )

        self.create_entry(
            form,
            "Pay Period End (YYYY-MM-DD)",
            self.pay_period_end_var,
            2,
            2,
        )

        self.base_salary_var = tk.StringVar()
        self.allowances_var = tk.StringVar(value="0")
        self.deductions_var = tk.StringVar(value="0")

        self.create_entry(
            form,
            "Base Salary",
            self.base_salary_var,
            3,
            0,
        )

        self.create_entry(
            form,
            "Allowances",
            self.allowances_var,
            3,
            2,
        )

        self.create_entry(
            form,
            "Deductions",
            self.deductions_var,
            4,
            0,
        )

        ttk.Label(
            form,
            text="Currency",
        ).grid(row=4, column=2, sticky="w", padx=8, pady=10)

        self.currency_var = tk.StringVar(value="USD")

        ttk.Combobox(
            form,
            textvariable=self.currency_var,
            values=["USD", "KHR"],
            state="readonly",
        ).grid(
            row=4,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text=(
                "USD: up to two decimal places. "
                "KHR: whole riel only. "
                "Net salary = base salary + allowances - deductions."
            ),
            font=("Segoe UI", 9),
        ).grid(
            row=5,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(5, 5),
        )

    def create_entry(self, parent, label, variable, row, column):
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

        ttk.Entry(
            parent,
            textvariable=variable,
        ).grid(
            row=row,
            column=column + 1,
            sticky="ew",
            padx=8,
            pady=10,
        )

    # --------------------------------------------------
    # EMPLOYEE LOADING
    # --------------------------------------------------

    def load_employees(self):
        employee_type = self.employee_type_var.get()

        try:
            if employee_type == "teacher":
                self.employees = get_teachers(
                    actor_user_id=self.user["id"]
                )
            else:
                self.employees = get_transport_staff_list()

            self.employee_choices = {"Select Employee": None}

            for employee in self.employees:
                label = (
                    f'{employee["employee_no"]} - '
                    f'{employee["first_name"]} '
                    f'{employee["last_name"]}'
                )

                if employee["status"] != "active":
                    label += f' ({employee["status"]})'

                self.employee_choices[label] = employee["id"]

            self.employee_combo.configure(
                values=list(self.employee_choices.keys())
            )
            self.employee_var.set("Select Employee")

            if self.employees:
                self.employee_info.configure(
                    text=f"{len(self.employees)} employee record(s) loaded."
                )
            else:
                self.employee_info.configure(
                    text=f"No {employee_type.replace('_', ' ')} records found."
                )

        except Exception as error:
            messagebox.showerror(
                "Employee Loading Error",
                f"Could not load employee records:\n{error}",
                parent=self,
            )

    def on_employee_type_changed(self, event=None):
        self.load_employees()

    # --------------------------------------------------
    # CURRENCY CONVERSION
    # --------------------------------------------------

    def convert_amount(self, raw_value, field_name):
        raw_value = raw_value.strip()

        if not raw_value:
            raise ValueError(f"{field_name} is required.")

        try:
            amount = Decimal(raw_value)
        except InvalidOperation:
            raise ValueError(f"{field_name} must be a valid number.")

        if not amount.is_finite() or amount < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        currency = self.currency_var.get()

        if currency == "USD":
            scaled = amount * 100

            if scaled != scaled.to_integral_value():
                raise ValueError(
                    f"{field_name} can have no more than "
                    "two decimal places in USD."
                )
        elif currency == "KHR":
            if amount != amount.to_integral_value():
                raise ValueError(
                    f"{field_name} must be a whole number in KHR."
                )

            scaled = amount
        else:
            raise ValueError("Unsupported currency.")

        result = int(scaled)

        if result > 9223372036854775807:
            raise ValueError(f"{field_name} exceeds the supported range.")

        return result

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    def save_salary_slip(self):
        try:
            employee_id = self.employee_choices.get(
                self.employee_var.get()
            )

            if employee_id is None:
                raise ValueError("Please select an employee.")

            employee_type = self.employee_type_var.get()

            salary_data = {
                "pay_period_start": (
                    self.pay_period_start_var.get().strip()
                ),
                "pay_period_end": (
                    self.pay_period_end_var.get().strip()
                ),
                "base_salary_minor": self.convert_amount(
                    self.base_salary_var.get(),
                    "Base salary",
                ),
                "allowances_minor": self.convert_amount(
                    self.allowances_var.get(),
                    "Allowances",
                ),
                "deductions_minor": self.convert_amount(
                    self.deductions_var.get(),
                    "Deductions",
                ),
                "currency": self.currency_var.get(),
            }

            if employee_type == "teacher":
                salary_data["teacher_id"] = employee_id
            else:
                salary_data["transport_staff_id"] = employee_id

            slip_id = create_salary_slip(
                salary_data,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Salary Slip Created",
                (
                    "Draft salary slip created successfully.\n"
                    f"Salary Slip ID: {slip_id}"
                ),
                parent=self,
            )

            if self.on_saved:
                self.on_saved(slip_id)

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Salary Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Salary Slip Error",
                f"Could not create salary slip:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        ttk.Button(
            buttons,
            text="Create Draft Salary Slip",
            command=self.save_salary_slip,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Salary Slips",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.employee_var.set("Select Employee")
        self.pay_period_start_var.set("")
        self.pay_period_end_var.set("")
        self.base_salary_var.set("")
        self.allowances_var.set("0")
        self.deductions_var.set("0")
        self.currency_var.set("USD")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
