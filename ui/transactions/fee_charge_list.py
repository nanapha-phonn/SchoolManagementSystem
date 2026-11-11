import tkinter as tk
from tkinter import ttk, messagebox

from services.fee_charge_service import get_fee_charges


def format_amount(amount_minor, currency):
    if currency == "USD":
        return f"${amount_minor / 100:,.2f}"

    if currency == "KHR":
        return f"៛{amount_minor:,.0f}"

    return f"{currency} {amount_minor:,}"


class FeeChargeListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create,
        on_record_payment=None,
        on_view_payments=None,
        user=None,
    ):
        super().__init__(master, padding=25)

        self.user = user or {}
        self.on_create = on_create
        self.on_record_payment = on_record_payment
        self.on_view_payments = on_view_payments

        self.search_var = tk.StringVar()
        self.fee_type_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")

        self.create_header()
        self.create_filters()
        self.create_table()
        self.create_actions()

        self.load_charges()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 18))

        ttk.Label(
            header,
            text="Fee Charge Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register student fees and review outstanding balances.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    def create_filters(self):
        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 15))

        ttk.Label(filters, text="Search:").pack(side="left", padx=(0, 5))

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=22,
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_charges(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_charges,
        ).pack(side="left", padx=3)

        ttk.Label(
            filters,
            text="Fee Type:",
        ).pack(side="left", padx=(12, 5))

        fee_type_combo = ttk.Combobox(
            filters,
            textvariable=self.fee_type_var,
            values=["All", "class", "hostel", "bus"],
            state="readonly",
            width=10,
        )
        fee_type_combo.pack(side="left", padx=4)
        fee_type_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_charges(),
        )

        ttk.Label(
            filters,
            text="Status:",
        ).pack(side="left", padx=(12, 5))

        status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=["All", "open", "voided"],
            state="readonly",
            width=10,
        )
        status_combo.pack(side="left", padx=4)
        status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_charges(),
        )

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "charge_no",
            "student",
            "fee_type",
            "description",
            "amount",
            "paid",
            "balance",
            "due_date",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "charge_no": "Charge No.",
            "student": "Student",
            "fee_type": "Fee Type",
            "description": "Description",
            "amount": "Charge Amount",
            "paid": "Paid",
            "balance": "Balance",
            "due_date": "Due Date",
            "status": "Status",
        }

        widths = {
            "charge_no": 135,
            "student": 150,
            "fee_type": 80,
            "description": 180,
            "amount": 110,
            "paid": 100,
            "balance": 100,
            "due_date": 100,
            "status": 95,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=70,
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

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Fee Charge",
            command=self.on_create,
        ).pack(side="left", padx=4)

        if self.on_view_payments:
            ttk.Button(
                actions,
                text="Payment History",
                command=self.on_view_payments,
            ).pack(side="left", padx=4)

        self.payment_button = ttk.Button(
            actions,
            text="Record Payment",
            command=self.record_payment,
            state="disabled" if not self.on_record_payment else "normal",
        )
        self.payment_button.pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_charges,
        ).pack(side="right", padx=4)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_selection_changed,
        )

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    def load_charges(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        fee_type = self.fee_type_var.get()
        status = self.status_var.get()

        try:
            charges = get_fee_charges(
                fee_type=None if fee_type == "All" else fee_type,
                status=None if status == "All" else status,
                search=self.search_var.get(),
                actor_user_id=self.user["id"],
            )

            for charge in charges:
                student_name = (
                    f'{charge["first_name"]} {charge["last_name"]}'
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=str(charge["id"]),
                    values=(
                        charge["charge_no"],
                        student_name,
                        charge["fee_type"].title(),
                        charge["description"],
                        format_amount(
                            charge["amount_minor"],
                            charge["currency"],
                        ),
                        format_amount(
                            charge["amount_paid_minor"],
                            charge["currency"],
                        ),
                        format_amount(
                            charge["balance_minor"],
                            charge["currency"],
                        ),
                        charge["due_date"] or "-",
                        charge["payment_status"].title(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load fee charges:\n{error}",
                parent=self,
            )

        self.on_selection_changed()

    # --------------------------------------------------
    # SELECTION AND PAYMENT
    # --------------------------------------------------

    def get_selected_charge_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a fee charge first.",
                parent=self,
            )
            return None

        return int(selection[0])

    def on_selection_changed(self, event=None):
        if not self.on_record_payment:
            return

        selection = self.tree.selection()

        if not selection:
            self.payment_button.configure(state="disabled")
            return

        values = self.tree.item(selection[0], "values")
        status = values[-1].lower()

        self.payment_button.configure(
            state="normal" if status in {"unpaid", "partial", "overdue"} else "disabled"
        )

    def record_payment(self):
        charge_id = self.get_selected_charge_id()

        if charge_id is not None and self.on_record_payment:
            self.on_record_payment(charge_id)
