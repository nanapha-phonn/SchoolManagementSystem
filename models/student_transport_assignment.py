from dataclasses import dataclass
from datetime import date
import re


VALID_ASSIGNMENT_STATUSES = {
    "active",
    "completed",
    "cancelled",
}


@dataclass
class StudentTransportAssignment:
    student_id: int
    route_id: int
    start_date: str

    pickup_stop_id: int = None
    dropoff_stop_id: int = None
    end_date: str = None
    status: str = "active"

    @staticmethod
    def _validate_id(value, field_name, optional=False):
        if optional and value in (None, ""):
            return None

        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        if parsed <= 0 or str(value).strip() != str(parsed):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        return parsed

    @staticmethod
    def _validate_date(value, field_name, optional=False):
        if optional and value in (None, ""):
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            )

        value = value.strip()

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            )

        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(
                f"{field_name} must be a valid calendar date."
            )

        return value

    def validate(self):
        self.student_id = self._validate_id(
            self.student_id,
            "Student ID",
        )

        self.route_id = self._validate_id(
            self.route_id,
            "Route ID",
        )

        self.pickup_stop_id = self._validate_id(
            self.pickup_stop_id,
            "Pickup stop ID",
            optional=True,
        )

        self.dropoff_stop_id = self._validate_id(
            self.dropoff_stop_id,
            "Drop-off stop ID",
            optional=True,
        )

        self.start_date = self._validate_date(
            self.start_date,
            "Start date",
        )

        self.end_date = self._validate_date(
            self.end_date,
            "End date",
            optional=True,
        )

        if self.end_date and self.end_date < self.start_date:
            raise ValueError(
                "End date cannot be earlier than start date."
            )

        if not isinstance(self.status, str):
            raise ValueError("Invalid transport assignment status.")

        self.status = self.status.strip().lower()

        if self.status not in VALID_ASSIGNMENT_STATUSES:
            raise ValueError(
                "Status must be active, completed, or cancelled."
            )

        return self
