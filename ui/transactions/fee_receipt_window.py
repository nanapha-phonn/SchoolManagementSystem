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


class FeeReceiptWindow(tk.Toplevel):

    def __init__(self, master, payment):
        super().__init__(master)

        self.payment = payment

        self.title(f"Receipt - {payment['receipt_no']}")
        self.geometry("600x680")
        self.minsize(500, 550)
        self.transient(master)

        self.create_header()
        self.create_receipt()
        self.create_buttons()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="PAYMENT RECEIPT",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(20, 5))

        ttk.Label(
            self,
            text="SCHOOL MANAGEMENT SYSTEM",
            font=("Segoe UI", 10),
        ).pack(pady=(0, 15))

    # --------------------------------------------------
    # RECEIPT CONTENT
    # --------------------------------------------------

    def build_receipt_text(self):
        p = self.payment
        currency = p["currency"]

        lines = [
            "=" * 52,
            "                    PAYMENT RECEIPT",
            "=" * 52,
            "",
            f"Receipt Number : {p['receipt_no']}",
            f"Payment Date   : {p['payment_date']}",
            f"Payment Status : {p['status'].upper()}",
            "",
            "-" * 52,
            "STUDENT INFORMATION",
            "-" * 52,
            f"Admission No.  : {p['admission_no']}",
            f"Student Name   : {p['first_name']} {p['last_name']}",
            "",
            "-" * 52,
            "FEE INFORMATION",
            "-" * 52,
            f"Charge Number  : {p['charge_no']}",
            f"Fee Type       : {p['fee_type'].title()}",
            f"Description    : {p['charge_description']}",
            "",
            "-" * 52,
            "PAYMENT INFORMATION",
            "-" * 52,
            f"Amount Paid    : {format_amount(p['amount_minor'], currency)}",
            f"Payment Method : {p['payment_method'].replace('_', ' ').title()}",
            f"Reference      : {p['transaction_reference'] or '-'}",
            f"Received By ID : {p['received_by'] or '-'}",
            "",
        ]

        if p["status"] == "voided":
            lines.extend([
                "VOID INFORMATION",
                "-" * 52,
                f"Voided At      : {p['voided_at'] or '-'}",
                f"Void Reason    : {p['void_reason'] or '-'}",
                "",
            ])

        lines.extend([
            "=" * 52,
            "       This is a computer-generated receipt.",
            "=" * 52,
        ])

        return "\n".join(lines)

    def create_receipt(self):
        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        self.receipt_text = tk.Text(
            container,
            wrap="none",
            font=("Courier New", 10),
            height=25,
            width=65,
            padx=15,
            pady=15,
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.receipt_text.yview,
        )

        self.receipt_text.configure(
            yscrollcommand=scrollbar.set,
        )

        self.receipt_text.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(side="right", fill="y")

        self.receipt_text.insert(
            "1.0",
            self.build_receipt_text(),
        )

        self.receipt_text.configure(state="disabled")

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
            command=self.save_receipt,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Close",
            command=self.destroy,
        ).pack(side="right", padx=5)

    def save_receipt(self):
        default_name = f"{self.payment['receipt_no']}.txt"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Payment Receipt",
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
                file.write(self.build_receipt_text())

            messagebox.showinfo(
                "Receipt Saved",
                f"Receipt saved successfully:\n{file_path}",
                parent=self,
            )

        except OSError as error:
            messagebox.showerror(
                "Save Error",
                f"Could not save receipt:\n{error}",
                parent=self,
            )

    def save_pdf(self):
        default_name = f"{self.payment['receipt_no']}.pdf"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Payment Receipt as PDF",
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
                "Payment Receipt",
                self.build_receipt_text(),
            )

            messagebox.showinfo(
                "Receipt Saved",
                f"PDF receipt saved successfully:\n{file_path}",
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "PDF Export Error",
                f"Could not export receipt PDF:\n{error}",
                parent=self,
            )
