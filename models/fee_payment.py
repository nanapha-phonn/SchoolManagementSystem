from dataclasses import dataclass
from datetime import date
import re


VALID_PAYMENT_METHODS = {
    "cash",
    "bank_transfer",
    "card",
    "cheque",
    "mobile_money",
    "khqr",
    "other",
}

MAX_SQLITE_INTEGER = 9223372036854775807


def _positive_id(value, field_name, optional=True):
    if value is None or value == "":
        if optional:
            return None
        raise ValueError(f"{field_name} is required.")

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer.")

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a positive integer.")

    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return parsed


def _positive_amount(value):
    if isinstance(value, bool):
        raise ValueError("Payment amount must be a positive integer.")

    if isinstance(value, str):
        value = value.strip()

        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError(
                "Payment amount must be a positive integer."
            )

    if not isinstance(value, (int, str)):
        raise ValueError("Payment amount must be a positive integer.")

    try:
        amount = int(value)
    except (TypeError, ValueError):
        raise ValueError("Payment amount must be a positive integer.")

    if amount <= 0 or amount > MAX_SQLITE_INTEGER:
        raise ValueError(
            "Payment amount is outside the supported range."
        )

    return amount


def _validate_payment_date(value):
    if not value:
        raise ValueError("Payment date is required.")

    value = value.strip()

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            "Payment date must use YYYY-MM-DD format."
        )

    if parsed.isoformat() != value:
        raise ValueError(
            "Payment date must use YYYY-MM-DD format."
        )

    if parsed > date.today():
        raise ValueError("Payment date cannot be in the future.")

    return value


@dataclass
class FeePayment:
    charge_id: int
    amount_minor: int
    payment_date: str
    payment_method: str

    receipt_no: str = ""
    transaction_reference: str = ""
    received_by: int | None = None

    def validate(self):
        self.charge_id = _positive_id(
            self.charge_id,
            "Charge ID",
            optional=False
        )

        self.received_by = _positive_id(
            self.received_by,
            "Received by"
        )

        self.amount_minor = _positive_amount(self.amount_minor)
        self.payment_date = _validate_payment_date(self.payment_date)

        self.payment_method = self.payment_method.strip().lower()

        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError("Invalid payment method.")

        self.receipt_no = self.receipt_no.strip()

        if len(self.receipt_no) > 50:
            raise ValueError(
                "Receipt number cannot exceed 50 characters."
            )

        self.transaction_reference = (
            self.transaction_reference.strip()
        )

        if len(self.transaction_reference) > 100:
            raise ValueError(
                "Transaction reference cannot exceed 100 characters."
            )

        return self
