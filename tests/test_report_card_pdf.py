import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ui.student_results.report_card_pdf import (
    export_student_report_card_pdf,
)


class ReportCardPDFTests(unittest.TestCase):

    def sample_report(self, subjects=None):
        subjects = subjects if subjects is not None else [{
            "subject_name": "Mathematics",
            "subject_code": "MATH",
            "teacher_name": "Test Teacher",
            "marks_obtained": 85,
            "maximum_marks": 100,
            "percentage": 85,
            "grade_label": "A",
            "grade_point": 4.0,
            "grade_remark": "Excellent",
        }]

        return {
            "student": {
                "full_name": "Test Student",
                "admission_no": "ST001",
            },
            "class": {"name": "Class A"},
            "section": {"name": "Section 1"},
            "academic_year": {"name": "2026-2027"},
            "assessment_period": {
                "name": "Semester 1",
                "type": "midterm",
                "start_date": "2026-10-01",
                "end_date": "2026-10-15",
            },
            "subjects": subjects,
            "summary": {
                "subject_count": len(subjects),
                "total_marks_obtained": 85,
                "total_maximum_marks": 100,
                "overall_percentage": 85,
                "overall_grade_label": "A",
                "overall_grade_point": 4.0,
                "overall_remark": "Excellent",
            },
            "grading_scheme": {
                "name": "Standard Scheme",
                "version": 1,
            },
        }

    def test_01_generate_report_card_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report_card.pdf"

            result = export_student_report_card_pdf(
                path,
                self.sample_report(),
            )

            self.assertTrue(result.is_file())
            self.assertGreater(result.stat().st_size, 1000)

            with result.open("rb") as file:
                self.assertEqual(file.read(5), b"%PDF-")

    def test_02_generate_empty_report_card(self):
        report = self.sample_report(subjects=[])
        report["summary"].update({
            "total_marks_obtained": 0,
            "total_maximum_marks": 0,
            "overall_percentage": None,
            "overall_grade_label": None,
            "overall_grade_point": None,
            "overall_remark": None,
        })

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty_report.pdf"

            result = export_student_report_card_pdf(path, report)

            self.assertTrue(result.is_file())
            self.assertGreater(result.stat().st_size, 1000)

    def test_03_reject_invalid_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Invalid"):
                export_student_report_card_pdf(
                    Path(temp_dir) / "invalid.pdf",
                    None,
                )

    def test_04_reject_missing_student_information(self):
        report = self.sample_report()
        report["student"]["admission_no"] = ""

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Student"):
                export_student_report_card_pdf(
                    Path(temp_dir) / "invalid.pdf",
                    report,
                )

    def test_05_include_school_profile_in_pdf_content(self):
        report = self.sample_report()
        report["school"] = {
            "name": "Demo International School",
            "address": "Phnom Penh, Cambodia",
            "phone": "+855 12 345 678",
            "email": "info@demo-school.example",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "school_report.pdf"
            with patch(
                "ui.student_results.report_card_pdf.export_text_pdf"
            ) as mock_export:
                export_student_report_card_pdf(path, report)

            content = mock_export.call_args.args[2]
            self.assertIn("Demo International School", content)
            self.assertIn("Phnom Penh, Cambodia", content)
            self.assertIn("+855 12 345 678", content)
            self.assertIn("info@demo-school.example", content)
            self.assertIn("Test Student", content)


if __name__ == "__main__":
    unittest.main()
