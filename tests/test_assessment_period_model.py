import unittest

from models.assessment_period import AssessmentPeriod


def sample_period(**overrides):
    data = {
        "academic_year_id": 1,
        "name": "Semester 1 Midterm",
        "period_type": "midterm",
        "start_date": "2026-10-01",
        "end_date": "2026-10-15",
        "status": "planned",
    }

    data.update(overrides)
    return data


class AssessmentPeriodModelTests(unittest.TestCase):

    def test_valid_assessment_period(self):
        period = AssessmentPeriod(**sample_period()).validate()

        self.assertEqual(period.name, "Semester 1 Midterm")
        self.assertEqual(period.period_type, "midterm")
        self.assertEqual(period.status, "planned")

    def test_normalize_name_type_and_status(self):
        period = AssessmentPeriod(
            **sample_period(
                name="  Semester 1  ",
                period_type=" MIDTERM ",
                status=" PLANNED ",
            )
        ).validate()

        self.assertEqual(period.name, "Semester 1")
        self.assertEqual(period.period_type, "midterm")
        self.assertEqual(period.status, "planned")

    def test_accept_all_period_types(self):
        for period_type in (
            "midterm", "final", "term", "semester", "other"
        ):
            with self.subTest(period_type=period_type):
                period = AssessmentPeriod(
                    **sample_period(period_type=period_type)
                ).validate()

                self.assertEqual(period.period_type, period_type)

    def test_accept_all_valid_statuses(self):
        for status in ("planned", "active", "completed"):
            with self.subTest(status=status):
                period = AssessmentPeriod(
                    **sample_period(status=status)
                ).validate()

                self.assertEqual(period.status, status)

    def test_normalize_numeric_academic_year_id(self):
        period = AssessmentPeriod(
            **sample_period(academic_year_id="1")
        ).validate()

        self.assertEqual(period.academic_year_id, 1)
        self.assertIsInstance(period.academic_year_id, int)

    def test_reject_invalid_academic_year_ids(self):
        invalid_ids = [0, -1, True, False, None, "abc", 1.5]

        for value in invalid_ids:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    AssessmentPeriod(
                        **sample_period(academic_year_id=value)
                    ).validate()

    def test_reject_invalid_names(self):
        invalid_names = ["", "   ", "A" * 151]

        for value in invalid_names:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    AssessmentPeriod(
                        **sample_period(name=value)
                    ).validate()

    def test_reject_invalid_period_types(self):
        invalid_types = ["", "   ", "quiz", "MIDTERM EXAM"]

        for value in invalid_types:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    AssessmentPeriod(
                        **sample_period(period_type=value)
                    ).validate()

    def test_reject_invalid_dates(self):
        invalid_cases = [
            ("empty start", {"start_date": ""}),
            ("empty end", {"end_date": ""}),
            ("invalid start", {"start_date": "not-a-date"}),
            ("invalid end", {"end_date": "not-a-date"}),
            ("non-padded start", {"start_date": "2026-9-01"}),
            ("invalid calendar date", {"start_date": "2026-02-30"}),
            ("datetime instead of date", {
                "start_date": "2026-10-01T00:00:00"
            }),
            ("end before start", {
                "start_date": "2026-10-15",
                "end_date": "2026-10-01",
            }),
        ]

        for description, overrides in invalid_cases:
            with self.subTest(case=description):
                with self.assertRaises(ValueError):
                    AssessmentPeriod(
                        **sample_period(**overrides)
                    ).validate()

    def test_reject_invalid_statuses(self):
        invalid_statuses = ["", "   ", "pending", "archived"]

        for value in invalid_statuses:
            with self.subTest(status=value):
                with self.assertRaises(ValueError):
                    AssessmentPeriod(
                        **sample_period(status=value)
                    ).validate()


if __name__ == "__main__":
    unittest.main()
