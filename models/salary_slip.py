from dataclasses import dataclass, field
from datetime import date
import re


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


def _nonnegative_amount(value, field_name):
    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a non-negative integer."
        )

    if isinstance(value, str):
        value = value.strip()

        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError(
                f"{field_name} must be a non-negative integer."
            )

    if not isinstance(value, (int, str)):
        raise ValueError(
            f"{field_name} must be a non-negative integer."
        )

    try:
        amount = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a non-negative integer."
        )

    if amount < 0 or amount > MAX_SQLITE_INTEGER:
        raise ValueError(
            f"{field_name} is outside the supported range."
        )

    return amount


def _validate_date(value, field_name):
    if not value:
        raise ValueError(f"{field_name} is required.")

    value = value.strip()

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        )

    if parsed.isoformat() != value:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        )

    return parsed


@dataclass
class SalarySlip:
    pay_period_start: str
    pay_period_end: str
    base_salary_minor: int

    teacher_id: int | None = None
    transport_staff_id: int | None = None
    slip_no: str = ""
    school_id: int | None = None
    allowances_minor: int = 0
    deductions_minor: int = 0
    currency: str = "USD"
    created_by: int | None = None

    net_salary_minor: int = field(init=False)

    def validate(self):
        self.teacher_id = _positive_id(
            self.teacher_id,
            "Teacher ID"
        )

        self.transport_staff_id = _positive_id(
            self.transport_staff_id,
            "Transport staff ID"
        )

        self.school_id = _positive_id(self.school_id, "School ID")
        self.created_by = _positive_id(self.created_by, "Created by")

        # Exactly one employee record must be selected.
        if (self.teacher_id is None) == (
            self.transport_staff_id is None
        ):
            raise ValueError(
                "Select exactly one employee: teacher or transport staff."
            )

        start_date = _validate_date(
            self.pay_period_start,
            "Pay period start"
        )

        end_date = _validate_date(
            self.pay_period_end,
            "Pay period end"
        )

        if end_date < start_date:
            raise ValueError(
                "Pay period end cannot be before pay period start."
            )

        self.pay_period_start = start_date.isoformat()
        self.pay_period_end = end_date.isoformat()

        self.base_salary_minor = _nonnegative_amount(
            self.base_salary_minor,
            "Base salary"
        )

        self.allowances_minor = _nonnegative_amount(
            self.allowances_minor,
            "Allowances"
        )

        self.deductions_minor = _nonnegative_amount(
            self.deductions_minor,
            "Deductions"
        )

        gross_salary = (
            self.base_salary_minor + self.allowances_minor
        )

        if gross_salary > MAX_SQLITE_INTEGER:
            raise ValueError("Gross salary exceeds the supported range.")

        self.net_salary_minor = (
            gross_salary - self.deductions_minor
        )

        if self.net_salary_minor < 0:
            raise ValueError(
                "Deductions cannot exceed base salary plus allowances."
            )

        self.currency = self.currency.strip().upper()

        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError(
                "Currency must be a three-letter currency code."
            )

        self.slip_no = self.slip_no.strip()

        if len(self.slip_no) > 50:
            raise ValueError(
                "Salary slip number cannot exceed 50 characters."
            )

        return self
