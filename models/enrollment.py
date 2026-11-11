from dataclasses import dataclass
from datetime import date


VALID_ENROLLMENT_STATUSES = {
    "enrolled",
    "completed",
    "withdrawn",
    "transferred",
}


@dataclass
class Enrollment:
    student_id: int
    section_id: int
    academic_year_id: int
    enrolled_on: str
    status: str = "enrolled"

    def validate(self):
        for field_name in (
            "student_id",
            "section_id",
            "academic_year_id",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool):
                raise ValueError(
                    f"{field_name.replace('_', ' ').title()} "
                    "must be a positive integer."
                )

            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{field_name.replace('_', ' ').title()} "
                    "must be a positive integer."
                )

            if value <= 0:
                raise ValueError(
                    f"{field_name.replace('_', ' ').title()} "
                    "must be a positive integer."
                )

            setattr(self, field_name, value)

        if not isinstance(self.enrolled_on, str):
            raise ValueError(
                "Enrollment date must use YYYY-MM-DD format."
            )

        self.enrolled_on = self.enrolled_on.strip()

        try:
            parsed_date = date.fromisoformat(self.enrolled_on)

            if parsed_date.isoformat() != self.enrolled_on:
                raise ValueError

        except ValueError:
            raise ValueError(
                "Enrollment date must use YYYY-MM-DD format."
            )

        if not isinstance(self.status, str):
            raise ValueError("Invalid enrollment status.")

        self.status = self.status.strip().lower()

        if self.status not in VALID_ENROLLMENT_STATUSES:
            raise ValueError("Invalid enrollment status.")

        return self
