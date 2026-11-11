import unittest

from models.grading_scheme import GradingScheme
from models.grade_band import GradeBand


class GradingSchemeModelTests(unittest.TestCase):

    def valid_scheme(self, **overrides):
        data = {
            "class_id": 1,
            "academic_year_id": 1,
            "name": "Standard Grading",
            "version_no": 1,
            "status": "draft",
        }
        data.update(overrides)
        return GradingScheme(**data)

    def test_01_valid_grading_scheme(self):
        scheme = self.valid_scheme().validate()

        self.assertEqual(scheme.class_id, 1)
        self.assertEqual(scheme.academic_year_id, 1)
        self.assertEqual(scheme.version_no, 1)
        self.assertEqual(scheme.status, "draft")

    def test_02_trim_scheme_name(self):
        scheme = self.valid_scheme(
            name="  Standard Grading  "
        ).validate()

        self.assertEqual(scheme.name, "Standard Grading")

    def test_03_normalize_scheme_status(self):
        scheme = self.valid_scheme(
            status=" DRAFT "
        ).validate()

        self.assertEqual(scheme.status, "draft")

    def test_04_accept_active_status(self):
        self.assertEqual(
            self.valid_scheme(status="active").validate().status,
            "active",
        )

    def test_05_accept_archived_status(self):
        self.assertEqual(
            self.valid_scheme(status="archived").validate().status,
            "archived",
        )

    def test_06_reject_empty_name(self):
        with self.assertRaisesRegex(ValueError, "name is required"):
            self.valid_scheme(name="  ").validate()

    def test_07_reject_non_text_name(self):
        with self.assertRaisesRegex(ValueError, "must be text"):
            self.valid_scheme(name=123).validate()

    def test_08_reject_name_over_150_characters(self):
        with self.assertRaisesRegex(ValueError, "150 characters"):
            self.valid_scheme(name="A" * 151).validate()

    def test_09_reject_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "Invalid grading scheme status"):
            self.valid_scheme(status="published").validate()

    def test_10_reject_invalid_ids(self):
        for field in ("class_id", "academic_year_id", "version_no"):
            for value in (0, -1, True, 1.5, None, "invalid"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        self.valid_scheme(**{field: value}).validate()

    def test_11_accept_positive_integer_strings(self):
        scheme = self.valid_scheme(
            class_id="2",
            academic_year_id="3",
            version_no="4",
        ).validate()

        self.assertEqual(scheme.class_id, 2)
        self.assertEqual(scheme.academic_year_id, 3)
        self.assertEqual(scheme.version_no, 4)


class GradeBandModelTests(unittest.TestCase):

    def valid_band(self, **overrides):
        data = {
            "grading_scheme_id": 1,
            "grade_label": "A",
            "min_percentage": 85,
            "grade_point": 4.0,
            "remark": "Excellent",
        }
        data.update(overrides)
        return GradeBand(**data)

    def test_01_valid_grade_band(self):
        band = self.valid_band().validate()

        self.assertEqual(band.grading_scheme_id, 1)
        self.assertEqual(band.grade_label, "A")
        self.assertEqual(band.min_percentage, 85.0)
        self.assertEqual(band.grade_point, 4.0)

    def test_02_trim_grade_label_and_remark(self):
        band = self.valid_band(
            grade_label=" A ",
            remark=" Excellent ",
        ).validate()

        self.assertEqual(band.grade_label, "A")
        self.assertEqual(band.remark, "Excellent")

    def test_03_accept_zero_minimum_percentage(self):
        band = self.valid_band(
            grade_label="F",
            min_percentage=0,
            grade_point=None,
            remark="Needs improvement",
        ).validate()

        self.assertEqual(band.min_percentage, 0.0)

    def test_04_accept_100_percent_threshold(self):
        band = self.valid_band(
            min_percentage=100
        ).validate()

        self.assertEqual(band.min_percentage, 100.0)

    def test_05_accept_decimal_percentage(self):
        band = self.valid_band(
            min_percentage=87.5
        ).validate()

        self.assertEqual(band.min_percentage, 87.5)

    def test_06_accept_missing_grade_point(self):
        band = self.valid_band(
            grade_point=None
        ).validate()

        self.assertIsNone(band.grade_point)

    def test_07_accept_zero_grade_point(self):
        band = self.valid_band(
            grade_point=0
        ).validate()

        self.assertEqual(band.grade_point, 0.0)

    def test_08_accept_empty_remark(self):
        band = self.valid_band(
            remark=""
        ).validate()

        self.assertEqual(band.remark, "")

    def test_09_reject_invalid_scheme_id(self):
        for value in (0, -1, True, 1.5, None, "invalid"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.valid_band(
                        grading_scheme_id=value
                    ).validate()

    def test_10_reject_non_text_grade_label(self):
        with self.assertRaisesRegex(ValueError, "must be text"):
            self.valid_band(grade_label=123).validate()

    def test_11_reject_empty_grade_label(self):
        with self.assertRaisesRegex(ValueError, "label is required"):
            self.valid_band(grade_label="  ").validate()

    def test_12_reject_grade_label_over_20_characters(self):
        with self.assertRaisesRegex(ValueError, "20 characters"):
            self.valid_band(grade_label="A" * 21).validate()

    def test_13_reject_percentage_below_zero(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            self.valid_band(min_percentage=-0.01).validate()

    def test_14_reject_percentage_above_100(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            self.valid_band(min_percentage=100.01).validate()

    def test_15_reject_non_numeric_percentage(self):
        for value in ("85", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.valid_band(
                        min_percentage=value
                    ).validate()

    def test_16_reject_non_finite_percentage(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite number"):
                    self.valid_band(
                        min_percentage=value
                    ).validate()

    def test_17_reject_negative_grade_point(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.valid_band(grade_point=-0.01).validate()

    def test_18_reject_non_finite_grade_point(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite number"):
                    self.valid_band(
                        grade_point=value
                    ).validate()

    def test_19_reject_non_text_remark(self):
        with self.assertRaisesRegex(ValueError, "must be text"):
            self.valid_band(remark=123).validate()

    def test_20_reject_remark_over_300_characters(self):
        with self.assertRaisesRegex(ValueError, "300 characters"):
            self.valid_band(remark="A" * 301).validate()


if __name__ == "__main__":
    unittest.main()
