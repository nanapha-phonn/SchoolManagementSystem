import math
from dataclasses import dataclass
from numbers import Real


@dataclass
class StudentSubjectResult:
    enrollment_id: int
    assessment_period_id: int
    teacher_subject_assignment_id: int
    subject_id: int
    grading_scheme_id: int
    marks_obtained: float
    maximum_marks: float

    def validate(self):
        for field_name in (
            "enrollment_id",
            "assessment_period_id",
            "teacher_subject_assignment_id",
            "subject_id",
            "grading_scheme_id",
        ):
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, (int, str)):
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

        self.marks_obtained = self._validate_number(
            self.marks_obtained,
            "Marks obtained",
        )

        self.maximum_marks = self._validate_number(
            self.maximum_marks,
            "Maximum marks",
        )

        if self.maximum_marks <= 0:
            raise ValueError("Maximum marks must be greater than zero.")

        if self.marks_obtained < 0:
            raise ValueError("Marks obtained cannot be negative.")

        if self.marks_obtained > self.maximum_marks:
            raise ValueError(
                "Marks obtained cannot exceed maximum marks."
            )

        return self

    @staticmethod
    def _validate_number(value, field_name):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{field_name} must be numeric.")

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite number.")

        return value
