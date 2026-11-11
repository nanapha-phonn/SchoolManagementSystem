from dataclasses import dataclass
from datetime import date
import re


VALID_TEACHER_STATUSES = {
    "active",
    "inactive",
    "resigned",
    "terminated"
}

VALID_GENDERS = {
    "Male",
    "Female",
    "Other"
}


@dataclass
class Teacher:
    employee_no: str
    first_name: str
    last_name: str

    date_of_birth: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""

    qualification: str = ""
    specialization: str = ""
    department: str = ""

    employment_date: str = ""
    status: str = "active"

    def validate(self):

        # Normalize required fields.
        self.employee_no = self.employee_no.strip()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()

        if not self.employee_no:
            raise ValueError("Employee number is required.")

        if len(self.employee_no) > 30:
            raise ValueError(
                "Employee number cannot exceed 30 characters."
            )

        if not self.first_name or not self.last_name:
            raise ValueError(
                "First name and last name are required."
            )

        if len(self.first_name) > 100:
            raise ValueError("First name cannot exceed 100 characters.")

        if len(self.last_name) > 100:
            raise ValueError("Last name cannot exceed 100 characters.")

        # Validate dates.
        dob = self._validate_date(
            self.date_of_birth,
            "Date of birth"
        )

        employment = self._validate_date(
            self.employment_date,
            "Employment date"
        )

        if dob and employment and employment < dob:
            raise ValueError(
                "Employment date cannot be before date of birth."
            )

        # Validate gender.
        if self.gender and self.gender not in VALID_GENDERS:
            raise ValueError("Please select a valid gender.")

        # Validate email.
        if self.email:
            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

            if not re.fullmatch(pattern, self.email):
                raise ValueError(
                    "Please enter a valid email address."
                )

        # Validate phone numbers.
        for field_name, value in (
            ("Phone", self.phone),
        ):
            if value and not re.fullmatch(
                r"[0-9+\-() ]{5,25}", value
            ):
                raise ValueError(
                    f"{field_name} contains invalid characters or length."
                )

        # Validate optional text lengths.
        text_limits = {
            "address": 500,
            "qualification": 150,
            "specialization": 150,
            "department": 100,
        }

        for field_name, maximum in text_limits.items():
            value = getattr(self, field_name)

            if value and len(value.strip()) > maximum:
                raise ValueError(
                    f"{field_name.replace('_', ' ').title()} "
                    f"cannot exceed {maximum} characters."
                )

            if isinstance(value, str):
                setattr(self, field_name, value.strip())

        # Validate status.
        if self.status not in VALID_TEACHER_STATUSES:
            raise ValueError("Invalid teacher status.")

        return self

    @staticmethod
    def _validate_date(value, field_name):

        if not value:
            return None

        try:
            parsed_date = date.fromisoformat(value)

            if parsed_date.isoformat() != value:
                raise ValueError

        except ValueError:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            )

        if parsed_date > date.today():
            raise ValueError(
                f"{field_name} cannot be in the future."
            )

        return parsed_date
