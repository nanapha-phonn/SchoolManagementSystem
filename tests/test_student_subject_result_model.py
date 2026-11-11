import unittest

from models.student_subject_result import StudentSubjectResult


class StudentSubjectResultModelTests(unittest.TestCase):

    def valid_data(self, **overrides):
        data = {
            "enrollment_id": 1,
            "assessment_period_id": 1,
            "teacher_subject_assignment_id": 1,
            "subject_id": 1,
            "grading_scheme_id": 1,
            "marks_obtained": 85,
            "maximum_marks": 100,
        }
        data.update(overrides)
        return StudentSubjectResult(**data)

    def test_01_valid_result(self):
        result = self.valid_data().validate()

        self.assertEqual(result.marks_obtained, 85.0)
        self.assertEqual(result.maximum_marks, 100.0)

    def test_02_accept_decimal_marks(self):
        result = self.valid_data(
            marks_obtained=78.5,
            maximum_marks=100.0,
        ).validate()

        self.assertEqual(result.marks_obtained, 78.5)

    def test_03_accept_full_marks(self):
        result = self.valid_data(
            marks_obtained=100,
            maximum_marks=100,
        ).validate()

        self.assertEqual(result.marks_obtained, 100.0)

    def test_04_accept_zero_marks(self):
        result = self.valid_data(
            marks_obtained=0,
            maximum_marks=100,
        ).validate()

        self.assertEqual(result.marks_obtained, 0.0)

    def test_05_normalize_string_ids(self):
        result = self.valid_data(
            enrollment_id="5",
            assessment_period_id="6",
        ).validate()

        self.assertEqual(result.enrollment_id, 5)
        self.assertEqual(result.assessment_period_id, 6)

    def test_06_reject_invalid_ids(self):
        for field in (
            "enrollment_id",
            "assessment_period_id",
            "teacher_subject_assignment_id",
            "subject_id",
            "grading_scheme_id",
        ):
            for value in (0, -1, True, None, "invalid"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        self.valid_data(**{field: value}).validate()

    def test_07_reject_negative_marks(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.valid_data(marks_obtained=-1).validate()

    def test_08_reject_marks_above_maximum(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            self.valid_data(
                marks_obtained=101,
                maximum_marks=100,
            ).validate()

    def test_09_reject_zero_maximum_marks(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.valid_data(maximum_marks=0).validate()

    def test_10_reject_negative_maximum_marks(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.valid_data(maximum_marks=-10).validate()

    def test_11_reject_non_numeric_marks(self):
        for value in ("abc", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.valid_data(marks_obtained=value).validate()

    def test_12_reject_non_numeric_maximum(self):
        for value in ("abc", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.valid_data(maximum_marks=value).validate()

    def test_13_reject_infinite_marks(self):
        for value in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    self.valid_data(marks_obtained=value).validate()

    def test_14_reject_infinite_maximum(self):
        for value in (float("inf"), float("nan")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    self.valid_data(maximum_marks=value).validate()


if __name__ == "__main__":
    unittest.main()
