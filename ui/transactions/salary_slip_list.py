import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date

from services.salary_slip_service import (
    get_salary_slips,
    get_salary_slip,
    issue_salary_slip,
    mark_salary_slip_paid,
    void_salary_slip,
)
from ui.transactions.salary_slip_window import SalarySlipWindow


def format_amount(amount_minor, currency):
    if currency == "USD":
        return (
            f"${amount_minor // 100:,}."
            f"{amount_minor % 100:02d}"
        )

    if currency == "KHR":
        return f"៛{amount_minor:,}"

    return f"{currency} {amount_minor:,}"


class SalarySlipListFrame(ttk.Frame):

    def __init__(self, master, on_create, on_back=None, user=None):
        super().__init__(master, padding=25)

        self.on_create = on_create
        self.on_back = on_back
        self.user = user or {}

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="All")

        self.create_header()
        self.create_filters()
        self.create_table()
        self.create_actions()

        self.load_salary_slips()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="Salary Slip Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Prepare payroll, issue salary slips and record employee payments.",
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
            lambda event: self.load_salary_slips(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_salary_slips,
        ).pack(side="left", padx=4)

        ttk.Label(
            filters,
            text="Status:",
        ).pack(side="left", padx=(15, 5))

        status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=["All", "draft", "issued", "paid", "voided"],
            state="readonly",
            width=12,
        )
        status_combo.pack(side="left", padx=4)

        status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_salary_slips(),
        )

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "slip_no",
            "employee_no",
            "employee",
            "employee_type",
            "period",
            "net_salary",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "slip_no": "Slip Number",
            "employee_no": "Employee No.",
            "employee": "Employee Name",
            "employee_type": "Employee Type",
            "period": "Pay Period",
            "net_salary": "Net Salary",
            "status": "Status",
        }

        widths = {
            "slip_no": 145,
            "employee_no": 120,
            "employee": 160,
            "employee_type": 125,
            "period": 190,
            "net_salary": 120,
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
            lambda event: self.view_salary_slip(),
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Create Salary Slip",
            command=self.on_create,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="View Slip",
            command=self.view_salary_slip,
        ).pack(side="left", padx=3)

        self.issue_button = ttk.Button(
            actions,
            text="Issue Slip",
            command=self.issue_selected,
            state="disabled",
        )
        self.issue_button.pack(side="left", padx=3)

        self.paid_button = ttk.Button(
            actions,
            text="Mark as Paid",
            command=self.open_payment_dialog,
            state="disabled",
        )
        self.paid_button.pack(side="left", padx=3)

        self.void_button = ttk.Button(
            actions,
            text="Void Slip",
            command=self.void_selected,
            state="disabled",
        )
        self.void_button.pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_salary_slips,
        ).pack(side="right", padx=3)

        ttk.Button(
            actions,
            text="Back",
            command=self.go_back,
        ).pack(side="right", padx=3)

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    def load_salary_slips(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_status = self.status_var.get()

        try:
            slips = get_salary_slips(
                status=(
                    None
                    if selected_status == "All"
                    else selected_status
                ),
                search=self.search_var.get(),
                actor_user_id=self.user["id"],
            )

            for slip in slips:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(slip["id"]),
                    values=(
                        slip["slip_no"],
                        slip["employee_no"],
                        (
                            f'{slip["first_name"]} '
                            f'{slip["last_name"]}'
                        ),
                        slip["employee_type"].replace(
                            "_", " "
                        ).title(),
                        (
                            f'{slip["pay_period_start"]} '
                            f'to {slip["pay_period_end"]}'
                        ),
                        format_amount(
                            slip["net_salary_minor"],
                            slip["currency"],
                        ),
                        slip["status"].title(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load salary slips:\n{error}",
                parent=self,
            )

        self.on_selection_changed()

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_slip_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a salary slip first.",
                parent=self,
            )
            return None

        return int(selection[0])

    def on_selection_changed(self, event=None):
        selection = self.tree.selection()

        if not selection:
            self.issue_button.configure(state="disabled")
            self.paid_button.configure(state="disabled")
            self.void_button.configure(state="disabled")
            return

        values = self.tree.item(selection[0], "values")
        status = values[-1].lower()

        self.issue_button.configure(
            state="normal" if status == "draft" else "disabled"
        )

        self.paid_button.configure(
            state="normal" if status == "issued" else "disabled"
        )

        self.void_button.configure(
            state=(
                "normal"
                if status in {"draft", "issued"}
                else "disabled"
            )
        )

    # --------------------------------------------------
    # VIEW SLIP
    # --------------------------------------------------

    def view_salary_slip(self):
        slip_id = self.get_selected_slip_id()

        if slip_id is None:
            return

        try:
            slip = get_salary_slip(slip_id, actor_user_id=self.user["id"])

            if not slip:
                messagebox.showerror(
                    "Not Found",
                    "Salary slip was not found.",
                    parent=self,
                )
                self.load_salary_slips()
                return

            SalarySlipWindow(self, slip)

        except Exception as error:
            messagebox.showerror(
                "Salary Slip Error",
                f"Could not open salary slip:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # ISSUE SLIP
    # --------------------------------------------------

    def issue_selected(self):
        slip_id = self.get_selected_slip_id()

        if slip_id is None:
            return

        if not messagebox.askyesno(
            "Confirm Issue",
            "Issue the selected draft salary slip?",
            parent=self,
        ):
            return

        try:
            issue_salary_slip(slip_id, actor_user_id=self.user["id"])

            messagebox.showinfo(
                "Salary Slip Issued",
                "The salary slip has been issued successfully.",
                parent=self,
            )

            self.load_salary_slips()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Issue Salary Slip",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not issue salary slip:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # PAYMENT DIALOG
    # --------------------------------------------------

    def open_payment_dialog(self):
        slip_id = self.get_selected_slip_id()

        if slip_id is None:
            return

        slip = get_salary_slip(slip_id, actor_user_id=self.user["id"])

        if not slip:
            messagebox.showerror(
                "Not Found",
                "Salary slip was not found.",
                parent=self,
            )
            self.load_salary_slips()
            return

        if slip["status"] != "issued":
            messagebox.showwarning(
                "Invalid Status",
                "Only issued salary slips can be marked as paid.",
                parent=self,
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Record Salary Payment")
        dialog.geometry("430x280")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f'Salary Slip: {slip["slip_no"]}',
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 8))

        ttk.Label(
            dialog,
            text=(
                "Net Salary: "
                f'{format_amount(slip["net_salary_minor"], slip["currency"])}'
            ),
        ).pack(anchor="w", padx=20, pady=5)

        form = ttk.Frame(dialog, padding=20)
        form.pack(fill="x")

        ttk.Label(
            form,
            text="Payment Date (YYYY-MM-DD)",
        ).grid(row=0, column=0, sticky="w", pady=8)

        date_var = tk.StringVar(value=date.today().isoformat())

        ttk.Entry(
            form,
            textvariable=date_var,
            width=25,
        ).grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(
            form,
            text="Payment Method",
        ).grid(row=1, column=0, sticky="w", pady=8)

        method_var = tk.StringVar(value="bank_transfer")

        ttk.Combobox(
            form,
            textvariable=method_var,
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
            width=22,
        ).grid(row=1, column=1, padx=8, pady=8)

        ttk.Label(
            form,
            text="Transaction Reference",
        ).grid(row=2, column=0, sticky="w", pady=8)

        reference_var = tk.StringVar()

        ttk.Entry(
            form,
            textvariable=reference_var,
            width=25,
        ).grid(row=2, column=1, padx=8, pady=8)

        def save_payment():
            try:
                mark_salary_slip_paid(
                    slip_id,
                    date_var.get().strip(),
                    method_var.get(),
                    reference_var.get().strip(),
                    actor_user_id=self.user["id"],
                )

                dialog.destroy()

                messagebox.showinfo(
                    "Salary Paid",
                    "Salary payment has been recorded.",
                    parent=self,
                )

                self.load_salary_slips()

            except ValueError as error:
                messagebox.showwarning(
                    "Invalid Payment",
                    str(error),
                    parent=dialog,
                )

            except Exception as error:
                messagebox.showerror(
                    "Payment Error",
                    f"Could not record salary payment:\n{error}",
                    parent=dialog,
                )

        buttons = ttk.Frame(dialog, padding=(15, 0, 15, 15))
        buttons.pack(fill="x")

        ttk.Button(
            buttons,
            text="Confirm Payment",
            command=save_payment,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy,
        ).pack(side="right", padx=5)

    # --------------------------------------------------
    # VOID SLIP
    # --------------------------------------------------

    def void_selected(self):
        slip_id = self.get_selected_slip_id()

        if slip_id is None:
            return

        slip = get_salary_slip(slip_id, actor_user_id=self.user["id"])

        if not slip:
            messagebox.showerror(
                "Not Found",
                "Salary slip was not found.",
                parent=self,
            )
            self.load_salary_slips()
            return

        if slip["status"] not in {"draft", "issued"}:
            messagebox.showwarning(
                "Cannot Void",
                "Only draft or issued salary slips can be voided.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Void",
            (
                f'Void salary slip {slip["slip_no"]}?\n\n'
                "This action will be preserved in the payroll history."
            ),
            parent=self,
        )

        if not confirmed:
            return

        reason = simpledialog.askstring(
            "Void Reason",
            "Enter the reason for voiding this salary slip:",
            parent=self,
        )

        if reason is None:
            return

        try:
            void_salary_slip(
                slip_id,
                reason,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Salary Slip Voided",
                "The salary slip has been voided.",
                parent=self,
            )

            self.load_salary_slips()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Void Salary Slip",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not void salary slip:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
