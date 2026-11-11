from dataclasses import dataclass
from datetime import date


VALID_ASSIGNMENT_STATUSES = {
    "active",
    "inactive",
}


@dataclass
class TeacherSubjectAssignment:
    teacher_id: int
    subject_id: int
    section_id: int
    academic_year_id: int
    assigned_on: str
    ended_on: str = ""
    status: str = "active"

    def validate(self):
        for field_name in (
            "teacher_id",
            "subject_id",
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

        self.assigned_on = self._validate_date(
            self.assigned_on,
            "Assignment date"
        )

        if self.ended_on:
            self.ended_on = self._validate_date(
                self.ended_on,
                "End date"
            )

            if self.ended_on < self.assigned_on:
                raise ValueError(
                    "End date cannot be earlier than assignment date."
                )
        else:
            self.ended_on = ""

        if not isinstance(self.status, str):
            raise ValueError("Invalid assignment status.")

        self.status = self.status.strip().lower()

        if self.status not in VALID_ASSIGNMENT_STATUSES:
            raise ValueError("Invalid assignment status.")

        if self.status == "active" and self.ended_on:
            raise ValueError(
                "An active assignment cannot have an end date."
            )

        if self.status == "inactive" and not self.ended_on:
            raise ValueError(
                "An inactive assignment must have an end date."
            )

        return self

    @staticmethod
    def _validate_date(value, field_name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD format."
            )

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
