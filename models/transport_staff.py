from dataclasses import dataclass
import re


VALID_TRANSPORT_ROLES = {
    "driver",
    "attendant",
}

VALID_TRANSPORT_STAFF_STATUSES = {
    "active",
    "inactive",
    "resigned",
    "terminated",
}


@dataclass
class TransportStaff:
    employee_no: str
    first_name: str
    last_name: str

    phone: str = ""
    email: str = ""
    role: str = "attendant"
    license_number: str = ""
    status: str = "active"

    def validate(self):
        self.employee_no = self.employee_no.strip().upper()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.phone = self.phone.strip()
        self.email = self.email.strip().lower()
        self.role = self.role.strip().lower()
        self.license_number = self.license_number.strip()
        self.status = self.status.strip().lower()

        if not self.employee_no:
            raise ValueError("Employee number is required.")

        if len(self.employee_no) > 30:
            raise ValueError(
                "Employee number cannot exceed 30 characters."
            )

        if not re.fullmatch(r"[A-Z0-9\-\s]+", self.employee_no):
            raise ValueError(
                "Employee number contains invalid characters."
            )

        if not self.first_name:
            raise ValueError("First name is required.")

        if len(self.first_name) > 50:
            raise ValueError("First name cannot exceed 50 characters.")

        if not self.last_name:
            raise ValueError("Last name is required.")

        if len(self.last_name) > 50:
            raise ValueError("Last name cannot exceed 50 characters.")

        if self.phone:
            if len(self.phone) > 20:
                raise ValueError("Phone number cannot exceed 20 characters.")

            if not re.fullmatch(r"[0-9+\-\s()]+", self.phone):
                raise ValueError("Phone number contains invalid characters.")

        if self.email:
            if len(self.email) > 100:
                raise ValueError("Email cannot exceed 100 characters.")

            if not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                self.email
            ):
                raise ValueError("Please enter a valid email address.")

        if self.role not in VALID_TRANSPORT_ROLES:
            raise ValueError("Role must be driver or attendant.")

        if len(self.license_number) > 50:
            raise ValueError(
                "License number cannot exceed 50 characters."
            )

        if self.status not in VALID_TRANSPORT_STAFF_STATUSES:
            raise ValueError("Invalid transport staff status.")

        return self
