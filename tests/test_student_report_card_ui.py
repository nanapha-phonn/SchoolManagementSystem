import tkinter as tk
import tempfile
import unittest
from pathlib import Path
from tkinter import TclError
from unittest.mock import Mock, patch

from ui.student_results.student_report_card import StudentReportCardFrame


class StudentReportCardUITests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except TclError as error:
            raise unittest.SkipTest(str(error))

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        self.report = {
            "student": {
                "id": 1,
                "admission_no": "ST001",
                "first_name": "Test",
                "last_name": "Student",
                "full_name": "Test Student",
            },
            "class": {"id": 1, "name": "Class A"},
            "section": {"id": 1, "name": "Section 1"},
            "academic_year": {"id": 1, "name": "2026-2027"},
            "assessment_period": {
                "id": 1,
                "name": "Semester 1",
                "type": "midterm",
                "start_date": "2026-10-01",
                "end_date": "2026-10-15",
                "status": "completed",
            },
            "grading_scheme": {
                "id": 1,
                "name": "Standard Scheme",
                "version": 1,
                "status": "archived",
            },
            "subjects": [{
                "subject_code": "MATH",
                "subject_name": "Mathematics",
                "teacher_name": "Test Teacher",
                "marks_obtained": 85.0,
                "maximum_marks": 100.0,
                "percentage": 85.0,
                "grade_label": "A",
                "grade_point": 4.0,
                "grade_remark": "Excellent",
            }],
            "summary": {
                "subject_count": 1,
                "total_marks_obtained": 85.0,
                "total_maximum_marks": 100.0,
                "overall_percentage": 85.0,
                "overall_grade_label": "A",
                "overall_grade_point": 4.0,
                "overall_remark": "Excellent",
            },
        }

        self.on_back = Mock()

        self.report_patcher = patch(
            "ui.student_results.student_report_card."
            "get_student_report_card",
            return_value=self.report,
        )
        self.report_patcher.start()
        self.addCleanup(self.report_patcher.stop)

        self.screen = StudentReportCardFrame(
            self.frame,
            enrollment_id=10,
            assessment_period_id=20,
            on_back=self.on_back,
        )
        self.screen.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        self.frame.destroy()
        self.root.update_idletasks()

    def test_01_load_report_for_selected_student_and_period(self):
        from ui.student_results import student_report_card

        student_report_card.get_student_report_card.assert_called_once_with(
            10, 20
        )

    def test_02_display_student_and_academic_details(self):
        self.assertEqual(
            self.screen.student_labels["student_name"].cget("text"),
            "Test Student",
        )
        self.assertEqual(
            self.screen.student_labels["admission_no"].cget("text"),
            "ST001",
        )
        self.assertEqual(
            self.screen.student_labels["class_name"].cget("text"),
            "Class A",
        )
        self.assertEqual(
            self.screen.student_labels["section_name"].cget("text"),
            "Section 1",
        )
        self.assertEqual(
            self.screen.student_labels["academic_year"].cget("text"),
            "2026-2027",
        )
        self.assertEqual(
            self.screen.student_labels["period_status"].cget("text"),
            "Completed",
        )

    def test_03_display_subject_results(self):
        rows = self.screen.tree.get_children()
        self.assertEqual(len(rows), 1)

        values = self.screen.tree.item(rows[0], "values")

        self.assertEqual(values[0], "MATH")
        self.assertEqual(values[1], "Mathematics")
        self.assertEqual(values[2], "Test Teacher")
        self.assertEqual(values[3], "85 / 100")
        self.assertEqual(values[4], "85.00%")
        self.assertEqual(values[5], "A")
        self.assertEqual(values[6], "4")
        self.assertEqual(values[7], "Excellent")

    def test_04_display_overall_summary(self):
        self.assertEqual(
            self.screen.summary_labels["subject_count"].cget("text"),
            "1",
        )
        self.assertEqual(
            self.screen.summary_labels["total_marks"].cget("text"),
            "85 / 100",
        )
        self.assertEqual(
            self.screen.summary_labels["overall_percentage"].cget("text"),
            "85.00%",
        )
        self.assertEqual(
            self.screen.summary_labels["overall_grade"].cget("text"),
            "A",
        )
        self.assertEqual(
            self.screen.summary_labels["grade_point"].cget("text"),
            "4",
        )

    def test_05_display_grading_scheme_version(self):
        text = self.screen.scheme_label.cget("text")

        self.assertIn("Standard Scheme", text)
        self.assertIn("Version 1", text)
        self.assertIn("Archived", text)

    def test_06_back_callback(self):
        self.screen.go_back()
        self.on_back.assert_called_once()

    def test_07_cancel_pdf_export(self):
        with patch(
            "ui.student_results.student_report_card.filedialog.asksaveasfilename",
            return_value="",
        ), patch(
            "ui.student_results.student_report_card."
            "export_student_report_card_pdf",
        ) as mock_export:
            self.screen.export_pdf()

        mock_export.assert_not_called()

    def test_08_export_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report_card.pdf"

            with patch(
                "ui.student_results.student_report_card.filedialog.asksaveasfilename",
                return_value=str(output_path),
            ), patch(
                "ui.student_results.student_report_card."
                "export_student_report_card_pdf",
                return_value=output_path,
            ) as mock_export, patch(
                "ui.student_results.student_report_card.messagebox.showinfo",
            ) as mock_info:
                self.screen.export_pdf()

            mock_export.assert_called_once_with(
                output_path,
                self.report,
            )
            mock_info.assert_called_once()

    def test_09_handle_pdf_export_error(self):
        with patch(
            "ui.student_results.student_report_card.filedialog.asksaveasfilename",
            return_value="/tmp/report_card.pdf",
        ), patch(
            "ui.student_results.student_report_card."
            "export_student_report_card_pdf",
            side_effect=RuntimeError("PDF generation failed"),
        ), patch(
            "ui.student_results.student_report_card.messagebox.showerror",
        ) as mock_error:
            self.screen.export_pdf()

        mock_error.assert_called_once()
        self.assertIn("PDF generation failed", mock_error.call_args.args[1])

    def test_10_display_empty_report_card(self):
        empty_report = dict(self.report)
        empty_report["subjects"] = []
        empty_report["grading_scheme"] = None
        empty_report["summary"] = {
            "subject_count": 0,
            "total_marks_obtained": 0,
            "total_maximum_marks": 0,
            "overall_percentage": None,
            "overall_grade_label": None,
            "overall_grade_point": None,
            "overall_remark": None,
        }

        with patch(
            "ui.student_results.student_report_card."
            "get_student_report_card",
            return_value=empty_report,
        ):
            empty_screen = StudentReportCardFrame(
                self.frame,
                enrollment_id=10,
                assessment_period_id=20,
            )
            empty_screen.pack(fill="both", expand=True)
            self.root.update_idletasks()

            self.assertEqual(
                empty_screen.tree.get_children(),
                (),
            )
            self.assertEqual(
                empty_screen.summary_labels[
                    "overall_percentage"
                ].cget("text"),
                "-",
            )
            self.assertIn(
                "Not available",
                empty_screen.scheme_label.cget("text"),
            )

            empty_screen.destroy()


if __name__ == "__main__":
    unittest.main()
