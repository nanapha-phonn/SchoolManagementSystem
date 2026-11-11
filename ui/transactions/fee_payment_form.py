import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation
from datetime import date

from services.fee_payment_service import create_fee_payment


def format_amount(amount_minor, currency):
    if currency == "USD":
        return (
            f"${amount_minor // 100:,}."
            f"{amount_minor % 100:02d}"
        )

    if currency == "KHR":
        return f"៛{amount_minor:,}"

    return f"{currency} {amount_minor:,}"


class FeePaymentForm(ttk.Frame):

    def __init__(
        self,
        master,
        charge,
        user=None,
        on_back=None,
        on_saved=None,
    ):
        super().__init__(master, padding=25)

        self.charge = charge
        self.user = user or {}
        self.on_back = on_back
        self.on_saved = on_saved

        self.create_header()
        self.create_charge_summary()
        self.create_form()
        self.create_buttons()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="Record Fee Payment",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Record a full or partial payment and generate a receipt.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 18))

    # --------------------------------------------------
    # CHARGE SUMMARY
    # --------------------------------------------------

    def create_charge_summary(self):
        summary = ttk.LabelFrame(
            self,
            text="Selected Fee Charge",
            padding=15,
        )
        summary.pack(fill="x", pady=(0, 18))

        student_name = (
            f'{self.charge["first_name"]} '
            f'{self.charge["last_name"]}'
        )

        details = [
            ("Charge Number", self.charge["charge_no"]),
            ("Student", student_name),
            ("Admission Number", self.charge["admission_no"]),
            ("Fee Type", self.charge["fee_type"].title()),
            ("Description", self.charge["description"]),
            (
                "Original Amount",
                format_amount(
                    self.charge["amount_minor"],
                    self.charge["currency"],
                ),
            ),
            (
                "Previously Paid",
                format_amount(
                    self.charge["amount_paid_minor"],
                    self.charge["currency"],
                ),
            ),
            (
                "Outstanding Balance",
                format_amount(
                    self.charge["balance_minor"],
                    self.charge["currency"],
                ),
            ),
        ]

        for row, (label, value) in enumerate(details):
            ttk.Label(
                summary,
                text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=8,
                pady=4,
            )

            ttk.Label(
                summary,
                text=str(value),
            ).grid(
                row=row,
                column=1,
                sticky="w",
                padx=8,
                pady=4,
            )

        summary.columnconfigure(1, weight=1)

    # --------------------------------------------------
    # PAYMENT FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Payment Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(
            form,
            text=f"Payment Amount ({self.charge['currency']})",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=10)

        self.amount_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=self.amount_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text="Payment Date (YYYY-MM-DD)",
        ).grid(row=0, column=2, sticky="w", padx=8, pady=10)

        self.payment_date_var = tk.StringVar(
            value=date.today().isoformat()
        )

        ttk.Entry(
            form,
            textvariable=self.payment_date_var,
        ).grid(
            row=0,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text="Payment Method",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=10)

        self.method_var = tk.StringVar(value="cash")

        ttk.Combobox(
            form,
            textvariable=self.method_var,
            values=[
                "cash",
                "bank_transfer",
                "card",
                "cheque",
                "mobile_money",
                "khqr",
                "other",
            ],
            state="readonly",
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text="Transaction Reference",
        ).grid(row=1, column=2, sticky="w", padx=8, pady=10)

        self.reference_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=self.reference_var,
        ).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text=(
                "USD: enter dollars with up to 2 decimal places. "
                "KHR: enter whole riel."
            ),
            font=("Segoe UI", 9),
        ).grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 5),
        )

    # --------------------------------------------------
    # AMOUNT CONVERSION
    # --------------------------------------------------

    def convert_amount_to_minor_units(self):
        raw_amount = self.amount_var.get().strip()

        if not raw_amount:
            raise ValueError("Payment amount is required.")

        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            raise ValueError("Enter a valid payment amount.")

        if not amount.is_finite() or amount <= 0:
            raise ValueError(
                "Payment amount must be greater than zero."
            )

        currency = self.charge["currency"]

        if currency == "USD":
            scaled = amount * 100

            if scaled != scaled.to_integral_value():
                raise ValueError(
                    "USD payments can have no more than "
                    "two decimal places."
                )

        elif currency == "KHR":
            if amount != amount.to_integral_value():
                raise ValueError(
                    "KHR payments must be entered as whole riel."
                )

            scaled = amount

        else:
            raise ValueError(
                f"Payment entry does not support {currency} yet."
            )

        amount_minor = int(scaled)

        if amount_minor > 9223372036854775807:
            raise ValueError(
                "Payment amount exceeds the supported range."
            )

        return amount_minor

    # --------------------------------------------------
    # SAVE PAYMENT
    # --------------------------------------------------

    def save_payment(self):
        try:
            if self.charge["status"] != "open":
                raise ValueError(
                    "This fee charge is not open for payment."
                )

            if self.charge["balance_minor"] <= 0:
                raise ValueError(
                    "This fee charge has no outstanding balance."
                )

            payment_data = {
                "charge_id": self.charge["id"],
                "amount_minor": self.convert_amount_to_minor_units(),
                "payment_date": self.payment_date_var.get().strip(),
                "payment_method": self.method_var.get(),
                "transaction_reference": (
                    self.reference_var.get().strip()
                ),
            }

            payment_id = create_fee_payment(
                payment_data, actor_user_id=self.user["id"]
            )

            messagebox.showinfo(
                "Payment Recorded",
                (
                    "Payment recorded successfully.\n"
                    "A receipt number has been generated."
                ),
                parent=self,
            )

            if self.on_saved:
                self.on_saved(payment_id)

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Payment",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Payment Error",
                f"Could not record payment:\n{error}",
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
            text="Save Payment",
            command=self.save_payment,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Fee Charges",
            command=self.go_back,
        ).pack(side="left", padx=5)

    def go_back(self):
        if self.on_back:
            self.on_back()
