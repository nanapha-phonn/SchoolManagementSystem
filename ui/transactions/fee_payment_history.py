import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.fee_payment_service import (
    get_fee_payments,
    get_fee_payment,
    void_fee_payment,
)
from ui.transactions.fee_receipt_window import FeeReceiptWindow


def format_amount(amount_minor, currency):
    if currency == "USD":
        return (
            f"${amount_minor // 100:,}."
            f"{amount_minor % 100:02d}"
        )

    if currency == "KHR":
        return f"៛{amount_minor:,}"

    return f"{currency} {amount_minor:,}"


class FeePaymentHistoryFrame(ttk.Frame):

    def __init__(self, master, user=None, on_back=None):
        super().__init__(master, padding=25)

        self.user = user or {}
        self.on_back = on_back

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="All")

        self.create_header()
        self.create_filters()
        self.create_table()
        self.create_actions()

        self.load_payments()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="Payment History",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Search receipts and review posted or voided payments.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 18))

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    def create_filters(self):
        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 15))

        ttk.Label(
            filters,
            text="Search:",
        ).pack(side="left", padx=(0, 5))

        entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=30,
        )
        entry.pack(side="left", padx=5)

        entry.bind(
            "<Return>",
            lambda event: self.load_payments(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_payments,
        ).pack(side="left", padx=4)

        ttk.Label(
            filters,
            text="Status:",
        ).pack(side="left", padx=(15, 5))

        status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=["All", "posted", "voided"],
            state="readonly",
            width=12,
        )
        status_combo.pack(side="left", padx=4)

        status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_payments(),
        )

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "receipt_no",
            "student",
            "charge_no",
            "payment_date",
            "amount",
            "method",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "receipt_no": "Receipt Number",
            "student": "Student",
            "charge_no": "Charge Number",
            "payment_date": "Payment Date",
            "amount": "Amount",
            "method": "Payment Method",
            "status": "Status",
        }

        widths = {
            "receipt_no": 150,
            "student": 170,
            "charge_no": 140,
            "payment_date": 110,
            "amount": 120,
            "method": 125,
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
                minwidth=75,
                anchor="center",
                stretch=False,
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
            self.on_selection_changed,
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self.view_receipt(),
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="View Receipt",
            command=self.view_receipt,
        ).pack(side="left", padx=4)

        self.void_button = ttk.Button(
            actions,
            text="Void Receipt",
            command=self.void_receipt,
            state="disabled",
        )
        self.void_button.pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_payments,
        ).pack(side="right", padx=4)

        ttk.Button(
            actions,
            text="Back to Fee Charges",
            command=self.go_back,
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD PAYMENTS
    # --------------------------------------------------

    def load_payments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_status = self.status_var.get()

        try:
            payments = get_fee_payments(
                status=(
                    None
                    if selected_status == "All"
                    else selected_status
                ),
                search=self.search_var.get(),
                actor_user_id=self.user["id"],
            )

            for payment in payments:
                student_name = (
                    f'{payment["first_name"]} '
                    f'{payment["last_name"]}'
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=str(payment["id"]),
                    values=(
                        payment["receipt_no"],
                        student_name,
                        payment["charge_no"],
                        payment["payment_date"],
                        format_amount(
                            payment["amount_minor"],
                            payment["currency"],
                        ),
                        payment["payment_method"].replace(
                            "_", " "
                        ).title(),
                        payment["status"].title(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load payment history:\n{error}",
                parent=self,
            )

        self.on_selection_changed()

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_payment_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a payment record first.",
                parent=self,
            )
            return None

        return int(selection[0])

    def on_selection_changed(self, event=None):
        selection = self.tree.selection()

        if not selection:
            self.void_button.configure(state="disabled")
            return

        values = self.tree.item(selection[0], "values")
        status = values[-1].lower()

        can_void = self.user.get("role") == "admin"
        self.void_button.configure(
            state=(
                "normal"
                if status == "posted" and can_void
                else "disabled"
            )
        )

    # --------------------------------------------------
    # VIEW RECEIPT
    # --------------------------------------------------

    def view_receipt(self):
        payment_id = self.get_selected_payment_id()

        if payment_id is None:
            return

        try:
            payment = get_fee_payment(
                payment_id, actor_user_id=self.user["id"]
            )

            if not payment:
                messagebox.showerror(
                    "Not Found",
                    "Payment record was not found.",
                    parent=self,
                )
                self.load_payments()
                return

            FeeReceiptWindow(self, payment)

        except Exception as error:
            messagebox.showerror(
                "Receipt Error",
                f"Could not open receipt:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # VOID RECEIPT
    # --------------------------------------------------

    def void_receipt(self):
        payment_id = self.get_selected_payment_id()

        if payment_id is None:
            return

        payment = get_fee_payment(
            payment_id, actor_user_id=self.user["id"]
        )

        if not payment:
            messagebox.showerror(
                "Not Found",
                "Payment record was not found.",
                parent=self,
            )
            self.load_payments()
            return

        if payment["status"] != "posted":
            messagebox.showwarning(
                "Invalid Operation",
                "Only posted payments can be voided.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Receipt Void",
            (
                f'Void receipt {payment["receipt_no"]}?\n\n'
                "The payment will no longer count toward the "
                "student's outstanding balance."
            ),
            parent=self,
        )

        if not confirmed:
            return

        reason = simpledialog.askstring(
            "Void Reason",
            "Enter the reason for voiding this receipt:",
            parent=self,
        )

        if reason is None:
            return

        try:
            void_fee_payment(
                payment_id, reason, actor_user_id=self.user["id"]
            )

            messagebox.showinfo(
                "Receipt Voided",
                "The payment receipt has been voided.",
                parent=self,
            )

            self.load_payments()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Void Receipt",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not void receipt:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
