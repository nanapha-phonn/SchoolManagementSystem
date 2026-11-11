import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ui.transactions.pdf_export import export_text_pdf


def format_amount(amount_minor, currency):
    if currency == "USD":
        return (
            f"${amount_minor // 100:,}."
            f"{amount_minor % 100:02d}"
        )

    if currency == "KHR":
        return f"៛{amount_minor:,}"

    return f"{currency} {amount_minor:,}"


class SalarySlipWindow(tk.Toplevel):

    def __init__(self, master, slip):
        super().__init__(master)

        self.slip = slip

        self.title(f"Salary Slip - {slip['slip_no']}")
        self.geometry("620x720")
        self.minsize(520, 570)
        self.transient(master)

        self.create_header()
        self.create_document()
        self.create_buttons()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="SALARY SLIP",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(20, 5))

        ttk.Label(
            self,
            text="SCHOOL MANAGEMENT SYSTEM",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 15))

    # --------------------------------------------------
    # DOCUMENT CONTENT
    # --------------------------------------------------

    def build_document_text(self):
        slip = self.slip
        currency = slip["currency"]

        employee_name = (
            f'{slip["first_name"]} {slip["last_name"]}'
        )

        employee_type = (
            slip["employee_type"]
            .replace("_", " ")
            .title()
        )

        lines = [
            "=" * 54,
            "                       SALARY SLIP",
            "=" * 54,
            "",
            f"Slip Number       : {slip['slip_no']}",
            f"Status            : {slip['status'].upper()}",
            f"Employee Type     : {employee_type}",
            f"Employee Number   : {slip['employee_no']}",
            f"Employee Name     : {employee_name}",
            f"Pay Period Start  : {slip['pay_period_start']}",
            f"Pay Period End    : {slip['pay_period_end']}",
            "",
            "-" * 54,
            "EARNINGS",
            "-" * 54,
            (
                f"Base Salary       : "
                f"{format_amount(slip['base_salary_minor'], currency)}"
            ),
            (
                f"Allowances        : "
                f"{format_amount(slip['allowances_minor'], currency)}"
            ),
            "",
            "-" * 54,
            "DEDUCTIONS",
            "-" * 54,
            (
                f"Total Deductions  : "
                f"{format_amount(slip['deductions_minor'], currency)}"
            ),
            "",
            "=" * 54,
            (
                f"NET SALARY        : "
                f"{format_amount(slip['net_salary_minor'], currency)}"
            ),
            "=" * 54,
            "",
            "PAYMENT INFORMATION",
            "-" * 54,
            f"Payment Date      : {slip['payment_date'] or '-'}",
            f"Payment Method    : {slip['payment_method'] or '-'}",
            f"Reference         : {slip['transaction_reference'] or '-'}",
            f"Issued At         : {slip['issued_at'] or '-'}",
            f"Paid At           : {slip['paid_at'] or '-'}",
            "",
        ]

        if slip["status"] == "voided":
            lines.extend([
                "VOID INFORMATION",
                "-" * 54,
                f"Voided At         : {slip['voided_at'] or '-'}",
                f"Void Reason       : {slip['void_reason'] or '-'}",
                "",
            ])

        lines.extend([
            "=" * 54,
            "       This is a computer-generated salary slip.",
            "=" * 54,
        ])

        return "\n".join(lines)

    def create_document(self):
        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        self.document_text = tk.Text(
            container,
            wrap="none",
            font=("Courier New", 10),
            padx=15,
            pady=15,
        )

        vertical = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.document_text.yview,
        )

        horizontal = ttk.Scrollbar(
            container,
            orient="horizontal",
            command=self.document_text.xview,
        )

        self.document_text.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.document_text.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.document_text.insert(
            "1.0",
            self.build_document_text(),
        )

        self.document_text.configure(state="disabled")

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self, padding=(15, 0, 15, 15))
        buttons.pack(fill="x")

        ttk.Button(
            buttons,
            text="Save as PDF",
            command=self.save_pdf,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Save as TXT",
            command=self.save_document,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Close",
            command=self.destroy,
        ).pack(side="right", padx=5)

    def save_document(self):
        default_name = f"{self.slip['slip_no']}.txt"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Salary Slip",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(self.build_document_text())

            messagebox.showinfo(
                "Salary Slip Saved",
                f"Salary slip saved successfully:\n{file_path}",
                parent=self,
            )

        except OSError as error:
            messagebox.showerror(
                "Save Error",
                f"Could not save salary slip:\n{error}",
                parent=self,
            )

    def save_pdf(self):
        default_name = f"{self.slip['slip_no']}.pdf"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Salary Slip as PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[
                ("PDF files", "*.pdf"),
            ],
        )

        if not file_path:
            return

        try:
            export_text_pdf(
                file_path,
                "Salary Slip",
                self.build_document_text(),
            )

            messagebox.showinfo(
                "Salary Slip Saved",
                f"PDF salary slip saved successfully:\n{file_path}",
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "PDF Export Error",
                f"Could not export salary slip PDF:\n{error}",
                parent=self,
            )
