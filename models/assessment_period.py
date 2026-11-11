from dataclasses import dataclass
from datetime import date


PERIOD_TYPES = {
    "midterm",
    "final",
    "term",
    "semester",
    "other",
}

PERIOD_STATUSES = {
    "planned",
    "active",
    "completed",
}


@dataclass
class AssessmentPeriod:
    academic_year_id: int
    name: str
    period_type: str
    start_date: str
    end_date: str
    status: str = "planned"

    def validate(self):
        self.academic_year_id = self._validate_id(
            self.academic_year_id
        )

        self.name = str(self.name or "").strip()

        if not self.name:
            raise ValueError("Assessment period name is required.")

        if len(self.name) > 150:
            raise ValueError(
                "Assessment period name cannot exceed 150 characters."
            )

        self.period_type = str(
            self.period_type or ""
        ).strip().lower()

        if self.period_type not in PERIOD_TYPES:
            raise ValueError(
                "Assessment period type must be Midterm, Final, "
                "Term, Semester, or Other."
            )

        self.start_date = self._validate_date(
            self.start_date,
            "Start date"
        )

        self.end_date = self._validate_date(
            self.end_date,
            "End date"
        )

        if self.end_date < self.start_date:
            raise ValueError(
                "End date cannot be earlier than start date."
            )

        self.status = str(
            self.status or ""
        ).strip().lower()

        if self.status not in PERIOD_STATUSES:
            raise ValueError(
                "Assessment period status must be Planned, "
                "Active, or Completed."
            )

        return self

    @staticmethod
    def _validate_id(value):
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError(
                "Academic year ID must be a positive integer."
            )

        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Academic year ID must be a positive integer."
            )

        if value <= 0:
            raise ValueError(
                "Academic year ID must be a positive integer."
            )

        return value

    @staticmethod
    def _validate_date(value, field_name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} is required.")

        value = value.strip()

        try:
            parsed_date = date.fromisoformat(value)

            if parsed_date.isoformat() != value:
                raise ValueError

        except ValueError:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            )

        return value
