from dataclasses import dataclass
from datetime import date
import re


VALID_STATUSES = {
    "active",
    "inactive",
    "graduated",
    "transferred"
}

VALID_GENDERS = {
    "Male",
    "Female",
    "Other"
}


@dataclass
class Student:
    admission_no: str
    first_name: str
    last_name: str
    date_of_birth: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    guardian_name: str = ""
    guardian_phone: str = ""
    status: str = "active"

    def validate(self):
        self.admission_no = self.admission_no.strip()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()

        if not self.admission_no:
            raise ValueError("Admission number is required.")

        if len(self.admission_no) > 30:
            raise ValueError(
                "Admission number cannot exceed 30 characters."
            )

        if not self.first_name or not self.last_name:
            raise ValueError(
                "First name and last name are required."
            )

        if len(self.first_name) > 100 or len(self.last_name) > 100:
            raise ValueError(
                "Student names cannot exceed 100 characters."
            )

        if self.date_of_birth:
            try:
                dob = date.fromisoformat(self.date_of_birth)

                if dob.isoformat() != self.date_of_birth:
                    raise ValueError

            except ValueError:
                raise ValueError(
                    "Date of birth must use YYYY-MM-DD format."
                )

            if dob > date.today():
                raise ValueError(
                    "Date of birth cannot be in the future."
                )

        if self.gender and self.gender not in VALID_GENDERS:
            raise ValueError("Please select a valid gender.")

        if self.email:
            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

            if not re.match(pattern, self.email):
                raise ValueError(
                    "Please enter a valid email address."
                )

        for field_name, value in (
            ("Phone", self.phone),
            ("Guardian phone", self.guardian_phone)
        ):
            if value and not re.fullmatch(
                r"[0-9+\-() ]{5,25}", value
            ):
                raise ValueError(
                    f"{field_name} contains invalid characters or length."
                )

        if self.status not in VALID_STATUSES:
            raise ValueError("Invalid student status.")

        return self
