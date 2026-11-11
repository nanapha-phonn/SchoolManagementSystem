from dataclasses import dataclass
from datetime import date


@dataclass
class AcademicYear:
    name: str
    start_date: str
    end_date: str
    is_current: bool = False

    def validate(self):
        self.name = str(self.name or "").strip()

        if not self.name:
            raise ValueError("Academic year name is required.")

        if len(self.name) > 100:
            raise ValueError(
                "Academic year name cannot exceed 100 characters."
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

        if isinstance(self.is_current, bool):
            pass
        elif self.is_current in (0, 1):
            self.is_current = bool(self.is_current)
        else:
            raise ValueError(
                "Current academic year flag must be true or false."
            )

        return self

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
