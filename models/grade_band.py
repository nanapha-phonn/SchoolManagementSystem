import math
from dataclasses import dataclass
from numbers import Real


@dataclass
class GradeBand:
    grading_scheme_id: int
    grade_label: str
    min_percentage: float
    grade_point: float = None
    remark: str = ""

    def validate(self):
        self.grading_scheme_id = self._validate_id(
            self.grading_scheme_id,
            "Grading scheme ID",
        )

        if not isinstance(self.grade_label, str):
            raise ValueError("Grade label must be text.")

        self.grade_label = self.grade_label.strip()

        if not self.grade_label:
            raise ValueError("Grade label is required.")

        if len(self.grade_label) > 20:
            raise ValueError(
                "Grade label cannot exceed 20 characters."
            )

        self.min_percentage = self._validate_number(
            self.min_percentage,
            "Minimum percentage",
        )

        if not 0 <= self.min_percentage <= 100:
            raise ValueError(
                "Minimum percentage must be between 0 and 100."
            )

        if self.grade_point is not None:
            self.grade_point = self._validate_number(
                self.grade_point,
                "Grade point",
            )

            if self.grade_point < 0:
                raise ValueError(
                    "Grade point cannot be negative."
                )

        if not isinstance(self.remark, str):
            raise ValueError("Grade remark must be text.")

        self.remark = self.remark.strip()

        if len(self.remark) > 300:
            raise ValueError(
                "Grade remark cannot exceed 300 characters."
            )

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

    @staticmethod
    def _validate_number(value, field_name):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{field_name} must be numeric.")

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite number.")

        return value
