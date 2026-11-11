from dataclasses import dataclass


GRADING_SCHEME_STATUSES = {
    "draft",
    "active",
    "archived",
}


@dataclass
class GradingScheme:
    class_id: int
    academic_year_id: int
    name: str
    version_no: int = 1
    status: str = "draft"

    def validate(self):
        self.class_id = self._validate_id(
            self.class_id,
            "Class ID",
        )

        self.academic_year_id = self._validate_id(
            self.academic_year_id,
            "Academic year ID",
        )

        self.version_no = self._validate_id(
            self.version_no,
            "Grading scheme version",
        )

        if not isinstance(self.name, str):
            raise ValueError("Grading scheme name must be text.")

        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Grading scheme name is required.")

        if len(self.name) > 150:
            raise ValueError(
                "Grading scheme name cannot exceed 150 characters."
            )

        if not isinstance(self.status, str):
            raise ValueError("Invalid grading scheme status.")

        self.status = self.status.strip().lower()

        if self.status not in GRADING_SCHEME_STATUSES:
            raise ValueError("Invalid grading scheme status.")

        return self

    @staticmethod
    def _validate_id(value, field_name):
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        return value
