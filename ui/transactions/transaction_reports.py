import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
import csv
from ui.transactions.pdf_export import export_table_pdf

from services.student_service import get_students
from services.transaction_report_service import (
    get_outstanding_fee_report,
    get_student_account_statement,
    get_fee_collection_summary,
    get_payroll_summary,
)


def format_amount(amount_minor, currency):
    if amount_minor is None:
        return "-"

    if currency == "USD":
        return (
            f"${amount_minor // 100:,}."
            f"{amount_minor % 100:02d}"
        )

    if currency == "KHR":
        return f"៛{amount_minor:,}"

    return f"{currency} {amount_minor:,}"


def format_balances(balances):
    if not balances:
        return "None"

    return " | ".join(
        f"{currency}: {format_amount(amount, currency)}"
        for currency, amount in sorted(balances.items())
    )


class TransactionReportsFrame(ttk.Frame):

    def __init__(self, master, on_back=None, user=None):
        super().__init__(master, padding=20)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_back = on_back

        self.students = []
        self.student_choices = {"Select Student": None}

        self.report_data = {
            "outstanding": [],
            "statement": [],
            "collection": [],
            "payroll": [],
        }

        self.create_header()
        self.load_students()
        self.create_notebook()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 15))

        ttk.Label(
            header,
            text="Financial Reports",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Review outstanding fees, student accounts, "
                "fee collections and employee payroll."
            ),
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

        if self.on_back:
            ttk.Button(
                header,
                text="Back to Dashboard",
                command=self.on_back,
            ).pack(anchor="e", pady=(8, 0))

    # --------------------------------------------------
    # STUDENT REFERENCE DATA
    # --------------------------------------------------

    def load_students(self):
        try:
            self.students = get_students(actor_user_id=self.user["id"])
            self.student_choices = {"Select Student": None}

            for student in self.students:
                label = (
                    f'{student["admission_no"]} - '
                    f'{student["first_name"]} {student["last_name"]}'
                )

                self.student_choices[label] = student["id"]

        except Exception as error:
            messagebox.showerror(
                "Student Loading Error",
                f"Could not load students:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # NOTEBOOK
    # --------------------------------------------------

    def create_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.outstanding_tab = ttk.Frame(
            self.notebook,
            padding=12,
        )
        self.statement_tab = ttk.Frame(
            self.notebook,
            padding=12,
        )
        self.collection_tab = ttk.Frame(
            self.notebook,
            padding=12,
        )
        self.payroll_tab = ttk.Frame(
            self.notebook,
            padding=12,
        )

        self.notebook.add(
            self.outstanding_tab,
            text="Outstanding Fees",
        )
        self.notebook.add(
            self.statement_tab,
            text="Student Statement",
        )
        self.notebook.add(
            self.collection_tab,
            text="Fee Collection",
        )
        self.notebook.add(
            self.payroll_tab,
            text="Payroll Summary",
        )

        self.create_outstanding_tab()
        self.create_statement_tab()
        self.create_collection_tab()
        self.create_payroll_tab()

    # --------------------------------------------------
    # SHARED TREEVIEW CREATION
    # --------------------------------------------------

    def create_report_tree(self, parent, columns, headings, widths):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, pady=(10, 0))

        tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        for column in columns:
            tree.heading(
                column,
                text=headings[column],
            )

            tree.column(
                column,
                width=widths.get(column, 120),
                minwidth=65,
                anchor="center",
                stretch=False,
            )

        vertical = ttk.Scrollbar(
            container,
            orient="vertical",
            command=tree.yview,
        )
        horizontal = ttk.Scrollbar(
            container,
            orient="horizontal",
            command=tree.xview,
        )

        tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        return tree

    def clear_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    # --------------------------------------------------
    # CSV EXPORT
    # --------------------------------------------------

    def export_csv(self, report_name):
        rows = self.report_data.get(report_name, [])

        if not rows:
            messagebox.showinfo(
                "No Report Data",
                "Run the report before exporting it.",
                parent=self,
            )
            return

        filename = f"{report_name}_report_{date.today().isoformat()}.csv"

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Report",
            defaultextension=".csv",
            initialfile=filename,
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        try:
            fieldnames = list(rows[0].keys())

            with open(
                path,
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=fieldnames,
                )
                writer.writeheader()
                writer.writerows(rows)

            messagebox.showinfo(
                "Export Complete",
                f"Report exported successfully:\n{path}",
                parent=self,
            )

        except OSError as error:
            messagebox.showerror(
                "Export Error",
                f"Could not export report:\n{error}",
                parent=self,
            )


    def export_pdf(self, report_name, title):
        rows = self.report_data.get(report_name, [])

        if not rows:
            messagebox.showinfo(
                "No Report Data",
                "Generate a report with data before exporting it.",
                parent=self,
            )
            return

        filename = (
            f"{report_name}_report_{date.today().isoformat()}.pdf"
        )

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Report as PDF",
            defaultextension=".pdf",
            initialfile=filename,
            filetypes=[
                ("PDF files", "*.pdf"),
            ],
        )

        if not path:
            return

        try:
            export_table_pdf(path, title, rows)

            messagebox.showinfo(
                "PDF Export Complete",
                f"Report exported successfully:\\n{path}",
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "PDF Export Error",
                f"Could not export report PDF:\\n{error}",
                parent=self,
            )

    # ==================================================
    # 1. OUTSTANDING FEES
    # ==================================================

    def create_outstanding_tab(self):
        filters = ttk.LabelFrame(
            self.outstanding_tab,
            text="Report Filters",
            padding=10,
        )
        filters.pack(fill="x")

        self.out_as_of_var = tk.StringVar(
            value=date.today().isoformat()
        )
        self.out_type_var = tk.StringVar(value="All")
        self.out_currency_var = tk.StringVar(value="All")
        self.out_status_var = tk.StringVar(value="All")

        ttk.Label(filters, text="As of Date:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.out_as_of_var,
            width=13,
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filters, text="Fee Type:").grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.out_type_var,
            values=["All", "class", "hostel", "bus"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filters, text="Currency:").grid(
            row=0, column=4, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.out_currency_var,
            values=["All", "USD", "KHR"],
            state="readonly",
            width=8,
        ).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(filters, text="Status:").grid(
            row=0, column=6, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.out_status_var,
            values=["All", "unpaid", "partial", "overdue"],
            state="readonly",
            width=11,
        ).grid(row=0, column=7, padx=5, pady=5)

        ttk.Button(
            filters,
            text="Generate Report",
            command=self.run_outstanding_report,
        ).grid(row=0, column=8, padx=8, pady=5)

        self.outstanding_summary = ttk.Label(
            self.outstanding_tab,
            text="Generate the report to view outstanding balances.",
            font=("Segoe UI", 10, "bold"),
        )
        self.outstanding_summary.pack(
            anchor="w",
            pady=(10, 3),
        )

        columns = (
            "charge_no",
            "admission_no",
            "student",
            "fee_type",
            "description",
            "amount",
            "paid",
            "balance",
            "due_date",
            "status",
        )

        headings = {
            "charge_no": "Charge No.",
            "admission_no": "Admission No.",
            "student": "Student",
            "fee_type": "Fee Type",
            "description": "Description",
            "amount": "Amount",
            "paid": "Paid",
            "balance": "Outstanding",
            "due_date": "Due Date",
            "status": "Status",
        }

        widths = {
            "charge_no": 125,
            "admission_no": 105,
            "student": 140,
            "fee_type": 80,
            "description": 170,
            "amount": 105,
            "paid": 100,
            "balance": 110,
            "due_date": 100,
            "status": 90,
        }

        self.outstanding_tree = self.create_report_tree(
            self.outstanding_tab,
            columns,
            headings,
            widths,
        )

        export_buttons = ttk.Frame(self.outstanding_tab)
        export_buttons.pack(anchor="e", pady=(8, 0))

        ttk.Button(
            export_buttons,
            text="Export PDF",
            command=lambda: self.export_pdf(
                "outstanding",
                "Outstanding Fee Report",
            ),
        ).pack(side="right", padx=4)

        ttk.Button(
            export_buttons,
            text="Export CSV",
            command=lambda: self.export_csv("outstanding"),
        ).pack(side="right", padx=4)

    def run_outstanding_report(self):
        self.clear_tree(self.outstanding_tree)

        try:
            fee_type = self.out_type_var.get()
            currency = self.out_currency_var.get()
            status = self.out_status_var.get()

            rows = get_outstanding_fee_report(
                as_of_date=self.out_as_of_var.get().strip(),
                fee_type=None if fee_type == "All" else fee_type,
                currency=None if currency == "All" else currency,
                payment_status=None if status == "All" else status,
                actor_user_id=self.user["id"],
            )

            self.report_data["outstanding"] = rows

            totals = {}

            for row in rows:
                key = row["currency"]
                totals[key] = (
                    totals.get(key, 0) + row["balance_minor"]
                )

                self.outstanding_tree.insert(
                    "",
                    "end",
                    values=(
                        row["charge_no"],
                        row["admission_no"],
                        f'{row["first_name"]} {row["last_name"]}',
                        row["fee_type"].title(),
                        row["description"],
                        format_amount(row["amount_minor"], row["currency"]),
                        format_amount(
                            row["amount_paid_minor"],
                            row["currency"],
                        ),
                        format_amount(row["balance_minor"], row["currency"]),
                        row["due_date"] or "-",
                        row["payment_status"].title(),
                    ),
                )

            if not totals:
                summary_text = "No outstanding fee charges found."
            else:
                summary_text = (
                    f"{len(rows)} outstanding charge(s) | "
                    + " | ".join(
                        f"{currency}: {format_amount(amount, currency)}"
                        for currency, amount in sorted(totals.items())
                    )
                )

            self.outstanding_summary.configure(text=summary_text)

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Filters",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Report Error",
                f"Could not generate outstanding fee report:\n{error}",
                parent=self,
            )

    # ==================================================
    # 2. STUDENT ACCOUNT STATEMENT
    # ==================================================

    def create_statement_tab(self):
        filters = ttk.LabelFrame(
            self.statement_tab,
            text="Student and Date Filters",
            padding=10,
        )
        filters.pack(fill="x")

        self.statement_student_var = tk.StringVar(
            value="Select Student"
        )
        self.statement_start_var = tk.StringVar()
        self.statement_end_var = tk.StringVar()
        self.statement_currency_var = tk.StringVar(value="All")

        ttk.Label(filters, text="Student:").grid(
            row=0, column=0, padx=5, pady=5
        )

        self.statement_student_combo = ttk.Combobox(
            filters,
            textvariable=self.statement_student_var,
            values=list(self.student_choices.keys()),
            state="readonly",
            width=30,
        )
        self.statement_student_combo.grid(
            row=0,
            column=1,
            padx=5,
            pady=5,
        )

        ttk.Label(filters, text="Start Date:").grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.statement_start_var,
            width=13,
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filters, text="End Date:").grid(
            row=0, column=4, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.statement_end_var,
            width=13,
        ).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(filters, text="Currency:").grid(
            row=0, column=6, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.statement_currency_var,
            values=["All", "USD", "KHR"],
            state="readonly",
            width=8,
        ).grid(row=0, column=7, padx=5, pady=5)

        ttk.Button(
            filters,
            text="Generate",
            command=self.run_student_statement,
        ).grid(row=0, column=8, padx=8, pady=5)

        self.statement_summary = ttk.Label(
            self.statement_tab,
            text="Select a student to view the account statement.",
            font=("Segoe UI", 10, "bold"),
        )
        self.statement_summary.pack(
            anchor="w",
            pady=(10, 3),
        )

        columns = (
            "date",
            "type",
            "reference",
            "description",
            "debit",
            "credit",
            "balance",
            "currency",
        )

        headings = {
            "date": "Date",
            "type": "Entry Type",
            "reference": "Reference",
            "description": "Description",
            "debit": "Debit",
            "credit": "Credit",
            "balance": "Running Balance",
            "currency": "Currency",
        }

        widths = {
            "date": 100,
            "type": 105,
            "reference": 145,
            "description": 190,
            "debit": 105,
            "credit": 105,
            "balance": 115,
            "currency": 80,
        }

        self.statement_tree = self.create_report_tree(
            self.statement_tab,
            columns,
            headings,
            widths,
        )

        export_buttons = ttk.Frame(self.statement_tab)
        export_buttons.pack(anchor="e", pady=(8, 0))

        ttk.Button(
            export_buttons,
            text="Export PDF",
            command=lambda: self.export_pdf(
                "statement",
                "Student Account Statement",
            ),
        ).pack(side="right", padx=4)

        ttk.Button(
            export_buttons,
            text="Export CSV",
            command=lambda: self.export_csv("statement"),
        ).pack(side="right", padx=4)

    def run_student_statement(self):
        self.clear_tree(self.statement_tree)

        try:
            student_id = self.student_choices.get(
                self.statement_student_var.get()
            )

            if student_id is None:
                raise ValueError("Please select a student.")

            currency = self.statement_currency_var.get()

            statement = get_student_account_statement(
                student_id=student_id,
                start_date=self.statement_start_var.get().strip() or None,
                end_date=self.statement_end_var.get().strip() or None,
                currency=None if currency == "All" else currency,
                actor_user_id=self.user["id"],
            )

            rows = statement["entries"]
            self.report_data["statement"] = rows

            for row in rows:
                self.statement_tree.insert(
                    "",
                    "end",
                    values=(
                        row["event_date"],
                        row["entry_type"].replace("_", " ").title(),
                        row["reference_no"],
                        row["description"],
                        format_amount(row["debit_minor"], row["currency"]),
                        format_amount(row["credit_minor"], row["currency"]),
                        format_amount(row["balance_minor"], row["currency"]),
                        row["currency"],
                    ),
                )

            student = statement["student"]
            opening = format_balances(statement["opening_balances"])
            closing = format_balances(statement["closing_balances"])

            self.statement_summary.configure(
                text=(
                    f'{student["admission_no"]} - '
                    f'{student["first_name"]} {student["last_name"]} | '
                    f"Opening: {opening} | Closing: {closing}"
                )
            )

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Filters",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Statement Error",
                f"Could not generate student statement:\n{error}",
                parent=self,
            )

    # ==================================================
    # 3. FEE COLLECTION SUMMARY
    # ==================================================

    def create_collection_tab(self):
        filters = ttk.LabelFrame(
            self.collection_tab,
            text="Collection Filters",
            padding=10,
        )
        filters.pack(fill="x")

        self.collection_start_var = tk.StringVar()
        self.collection_end_var = tk.StringVar()
        self.collection_type_var = tk.StringVar(value="All")

        ttk.Label(filters, text="Start Date:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.collection_start_var,
            width=14,
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filters, text="End Date:").grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.collection_end_var,
            width=14,
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filters, text="Fee Type:").grid(
            row=0, column=4, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.collection_type_var,
            values=["All", "class", "hostel", "bus"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, padx=5, pady=5)

        ttk.Button(
            filters,
            text="Generate Report",
            command=self.run_collection_report,
        ).grid(row=0, column=6, padx=8, pady=5)

        columns = (
            "fee_type",
            "currency",
            "posted",
            "voided",
            "net",
            "posted_count",
            "voided_count",
        )

        headings = {
            "fee_type": "Fee Type",
            "currency": "Currency",
            "posted": "Posted Collections",
            "voided": "Voided Payments",
            "net": "Net Collection",
            "posted_count": "Posted Count",
            "voided_count": "Voided Count",
        }

        widths = {
            "fee_type": 115,
            "currency": 85,
            "posted": 150,
            "voided": 150,
            "net": 150,
            "posted_count": 110,
            "voided_count": 110,
        }

        self.collection_tree = self.create_report_tree(
            self.collection_tab,
            columns,
            headings,
            widths,
        )

        export_buttons = ttk.Frame(self.collection_tab)
        export_buttons.pack(anchor="e", pady=(8, 0))

        ttk.Button(
            export_buttons,
            text="Export PDF",
            command=lambda: self.export_pdf(
                "collection",
                "Fee Collection Summary",
            ),
        ).pack(side="right", padx=4)

        ttk.Button(
            export_buttons,
            text="Export CSV",
            command=lambda: self.export_csv("collection"),
        ).pack(side="right", padx=4)

    def run_collection_report(self):
        self.clear_tree(self.collection_tree)

        try:
            fee_type = self.collection_type_var.get()

            rows = get_fee_collection_summary(
                start_date=self.collection_start_var.get().strip() or None,
                end_date=self.collection_end_var.get().strip() or None,
                fee_type=None if fee_type == "All" else fee_type,
                actor_user_id=self.user["id"],
            )

            self.report_data["collection"] = rows

            for row in rows:
                self.collection_tree.insert(
                    "",
                    "end",
                    values=(
                        row["fee_type"].title(),
                        row["currency"],
                        format_amount(
                            row["posted_amount_minor"],
                            row["currency"],
                        ),
                        format_amount(
                            row["voided_amount_minor"],
                            row["currency"],
                        ),
                        format_amount(
                            row["net_collected_minor"],
                            row["currency"],
                        ),
                        row["posted_count"],
                        row["voided_count"],
                    ),
                )

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Filters",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Report Error",
                f"Could not generate fee collection report:\n{error}",
                parent=self,
            )

    # ==================================================
    # 4. PAYROLL SUMMARY
    # ==================================================

    def create_payroll_tab(self):
        filters = ttk.LabelFrame(
            self.payroll_tab,
            text="Payroll Filters",
            padding=10,
        )
        filters.pack(fill="x")

        self.payroll_start_var = tk.StringVar()
        self.payroll_end_var = tk.StringVar()
        self.payroll_status_var = tk.StringVar(value="All")
        self.payroll_type_var = tk.StringVar(value="All")
        self.payroll_currency_var = tk.StringVar(value="All")

        ttk.Label(filters, text="Start Date:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.payroll_start_var,
            width=13,
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filters, text="End Date:").grid(
            row=0, column=2, padx=5, pady=5
        )
        ttk.Entry(
            filters,
            textvariable=self.payroll_end_var,
            width=13,
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filters, text="Status:").grid(
            row=0, column=4, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.payroll_status_var,
            values=["All", "draft", "issued", "paid", "voided"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(filters, text="Employee:").grid(
            row=0, column=6, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.payroll_type_var,
            values=["All", "teacher", "transport_staff"],
            state="readonly",
            width=14,
        ).grid(row=0, column=7, padx=5, pady=5)

        ttk.Label(filters, text="Currency:").grid(
            row=1, column=0, padx=5, pady=5
        )
        ttk.Combobox(
            filters,
            textvariable=self.payroll_currency_var,
            values=["All", "USD", "KHR"],
            state="readonly",
            width=10,
        ).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(
            filters,
            text="Generate Report",
            command=self.run_payroll_report,
        ).grid(row=1, column=2, padx=8, pady=5)

        columns = (
            "status",
            "employee_type",
            "currency",
            "count",
            "base",
            "allowances",
            "deductions",
            "net",
        )

        headings = {
            "status": "Status",
            "employee_type": "Employee Type",
            "currency": "Currency",
            "count": "Slip Count",
            "base": "Base Salary Total",
            "allowances": "Allowances",
            "deductions": "Deductions",
            "net": "Net Salary Total",
        }

        widths = {
            "status": 95,
            "employee_type": 130,
            "currency": 85,
            "count": 90,
            "base": 135,
            "allowances": 120,
            "deductions": 120,
            "net": 135,
        }

        self.payroll_tree = self.create_report_tree(
            self.payroll_tab,
            columns,
            headings,
            widths,
        )

        export_buttons = ttk.Frame(self.payroll_tab)
        export_buttons.pack(anchor="e", pady=(8, 0))

        ttk.Button(
            export_buttons,
            text="Export PDF",
            command=lambda: self.export_pdf(
                "payroll",
                "Payroll Summary",
            ),
        ).pack(side="right", padx=4)

        ttk.Button(
            export_buttons,
            text="Export CSV",
            command=lambda: self.export_csv("payroll"),
        ).pack(side="right", padx=4)

    def run_payroll_report(self):
        self.clear_tree(self.payroll_tree)

        try:
            status = self.payroll_status_var.get()
            employee_type = self.payroll_type_var.get()
            currency = self.payroll_currency_var.get()

            rows = get_payroll_summary(
                start_date=self.payroll_start_var.get().strip() or None,
                end_date=self.payroll_end_var.get().strip() or None,
                status=None if status == "All" else status,
                employee_type=(
                    None if employee_type == "All" else employee_type
                ),
                currency=None if currency == "All" else currency,
                actor_user_id=self.user["id"],
            )

            self.report_data["payroll"] = rows

            for row in rows:
                self.payroll_tree.insert(
                    "",
                    "end",
                    values=(
                        row["status"].title(),
                        row["employee_type"].replace("_", " ").title(),
                        row["currency"],
                        row["slip_count"],
                        format_amount(
                            row["base_salary_minor"],
                            row["currency"],
                        ),
                        format_amount(
                            row["allowances_minor"],
                            row["currency"],
                        ),
                        format_amount(
                            row["deductions_minor"],
                            row["currency"],
                        ),
                        format_amount(
                            row["net_salary_minor"],
                            row["currency"],
                        ),
                    ),
                )

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Filters",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Payroll Report Error",
                f"Could not generate payroll report:\n{error}",
                parent=self,
            )


def format_balances(balances):
    if not balances:
        return "None"

    return " | ".join(
        f"{currency}: {format_amount(amount, currency)}"
        for currency, amount in sorted(balances.items())
    )
