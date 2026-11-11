from dataclasses import dataclass
from datetime import date
import re


VALID_FEE_TYPES = {
    "class",
    "hostel",
    "bus",
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
        raise ValueError("Fee amount must be a positive integer.")

    if isinstance(value, str):
        value = value.strip()

        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError("Fee amount must be a positive integer.")

    if not isinstance(value, (int, str)):
        raise ValueError("Fee amount must be a positive integer.")

    try:
        amount = int(value)
    except (TypeError, ValueError):
        raise ValueError("Fee amount must be a positive integer.")

    if amount <= 0 or amount > MAX_SQLITE_INTEGER:
        raise ValueError("Fee amount is outside the supported range.")

    return amount


def _validate_date(value, field_name):
    if not value:
        return ""

    value = value.strip()

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")

    if parsed.isoformat() != value:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")

    return value


@dataclass
class FeeCharge:
    student_id: int
    fee_type: str
    description: str
    amount_minor: int

    charge_no: str = ""
    school_id: int | None = None
    enrollment_id: int | None = None
    transport_assignment_id: int | None = None
    currency: str = "USD"
    due_date: str = ""
    created_by: int | None = None

    def validate(self):
        self.student_id = _positive_id(
            self.student_id,
            "Student ID",
            optional=False
        )

        self.school_id = _positive_id(self.school_id, "School ID")
        self.enrollment_id = _positive_id(
            self.enrollment_id,
            "Enrollment ID"
        )
        self.transport_assignment_id = _positive_id(
            self.transport_assignment_id,
            "Transport assignment ID"
        )
        self.created_by = _positive_id(self.created_by, "Created by")

        self.fee_type = self.fee_type.strip().lower()

        if self.fee_type not in VALID_FEE_TYPES:
            raise ValueError("Invalid fee type.")

        self.description = self.description.strip()

        if not self.description:
            raise ValueError("Fee description is required.")

        if len(self.description) > 500:
            raise ValueError(
                "Fee description cannot exceed 500 characters."
            )

        self.amount_minor = _positive_amount(self.amount_minor)

        self.currency = self.currency.strip().upper()

        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError(
                "Currency must be a three-letter currency code."
            )

        self.charge_no = self.charge_no.strip()

        if len(self.charge_no) > 50:
            raise ValueError("Charge number cannot exceed 50 characters.")

        self.due_date = _validate_date(self.due_date, "Due date")

        if self.fee_type == "bus":
            if self.transport_assignment_id is None:
                raise ValueError(
                    "A transport assignment is required for bus fees."
                )

            if self.enrollment_id is not None:
                raise ValueError(
                    "Bus fees cannot reference a class enrollment."
                )

        elif self.fee_type == "class":
            if self.transport_assignment_id is not None:
                raise ValueError(
                    "Class fees cannot reference a transport assignment."
                )

        elif self.fee_type == "hostel":
            if self.transport_assignment_id is not None:
                raise ValueError(
                    "Hostel fees cannot reference a transport assignment."
                )

            if self.enrollment_id is not None:
                raise ValueError(
                    "Hostel fees cannot reference a class enrollment."
                )

        return self
