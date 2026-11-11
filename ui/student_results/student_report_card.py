import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from services.student_report_card_service import (
    get_student_report_card,
)
from ui.student_results.report_card_pdf import (
    export_student_report_card_pdf,
)


class StudentReportCardFrame(ttk.Frame):

    def __init__(
        self,
        master,
        enrollment_id,
        assessment_period_id,
        on_back=None,
    ):
        super().__init__(master, padding=25)

        self.on_back = on_back

        self.report = get_student_report_card(
            enrollment_id,
            assessment_period_id,
        )

        self.create_widgets()
        self.load_report()

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 15))

        ttk.Label(
            header,
            text="Student Report Card",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="Export PDF",
            command=self.export_pdf,
        ).pack(side="right", padx=5)

        ttk.Button(
            header,
            text="Back",
            command=self.go_back,
        ).pack(side="right", padx=5)

        student_frame = ttk.LabelFrame(
            self,
            text="Student Information",
            padding=12,
        )
        student_frame.pack(fill="x", pady=(0, 10))

        self.student_labels = {}

        student_fields = [
            ("Student Name", "student_name"),
            ("Admission Number", "admission_no"),
            ("Class", "class_name"),
            ("Section", "section_name"),
            ("Academic Year", "academic_year"),
            ("Assessment Period", "assessment_period"),
            ("Period Status", "period_status"),
        ]

        for index, (label, key) in enumerate(student_fields):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(
                student_frame,
                text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=6,
                pady=6,
            )

            value_label = ttk.Label(
                student_frame,
                text="-",
            )
            value_label.grid(
                row=row,
                column=column + 1,
                sticky="w",
                padx=6,
                pady=6,
            )

            self.student_labels[key] = value_label

        results_frame = ttk.LabelFrame(
            self,
            text="Subject Results",
            padding=10,
        )
        results_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = (
            "subject_code",
            "subject_name",
            "teacher",
            "marks",
            "percentage",
            "grade",
            "grade_point",
            "remark",
        )

        self.tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "subject_code": "Code",
            "subject_name": "Subject",
            "teacher": "Teacher",
            "marks": "Marks",
            "percentage": "Percentage",
            "grade": "Grade",
            "grade_point": "Grade Point",
            "remark": "Remark",
        }

        widths = {
            "subject_code": 85,
            "subject_name": 155,
            "teacher": 145,
            "marks": 95,
            "percentage": 90,
            "grade": 65,
            "grade_point": 85,
            "remark": 140,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                minwidth=60,
                anchor="center" if column in (
                    "marks",
                    "percentage",
                    "grade",
                    "grade_point",
                ) else "w",
            )

        vertical = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        horizontal = ttk.Scrollbar(
            results_frame,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        summary_frame = ttk.LabelFrame(
            self,
            text="Overall Summary",
            padding=12,
        )
        summary_frame.pack(fill="x")

        self.summary_labels = {}

        summary_fields = [
            ("Number of Subjects", "subject_count"),
            ("Total Marks", "total_marks"),
            ("Overall Percentage", "overall_percentage"),
            ("Overall Grade", "overall_grade"),
            ("Grade Point", "grade_point"),
            ("Overall Remark", "remark"),
        ]

        for index, (label, key) in enumerate(summary_fields):
            row = index // 3
            column = (index % 3) * 2

            ttk.Label(
                summary_frame,
                text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=6,
                pady=6,
            )

            value_label = ttk.Label(
                summary_frame,
                text="-",
            )
            value_label.grid(
                row=row,
                column=column + 1,
                sticky="w",
                padx=6,
                pady=6,
            )

            self.summary_labels[key] = value_label

        self.scheme_label = ttk.Label(
            self,
            text="Grading Scheme: -",
            font=("Segoe UI", 9),
        )
        self.scheme_label.pack(anchor="w", pady=(8, 0))

    def load_report(self):
        report = self.report
        student = report["student"]
        period = report["assessment_period"]
        summary = report["summary"]

        self.student_labels["student_name"].configure(
            text=student["full_name"]
        )
        self.student_labels["admission_no"].configure(
            text=student["admission_no"]
        )
        self.student_labels["class_name"].configure(
            text=report["class"]["name"]
        )
        self.student_labels["section_name"].configure(
            text=report["section"]["name"]
        )
        self.student_labels["academic_year"].configure(
            text=report["academic_year"]["name"]
        )
        self.student_labels["assessment_period"].configure(
            text=period["name"]
        )
        self.student_labels["period_status"].configure(
            text=period["status"].title()
        )

        self.tree.delete(*self.tree.get_children())

        for index, subject in enumerate(report["subjects"], start=1):
            marks = (
                f"{subject['marks_obtained']:g} / "
                f"{subject['maximum_marks']:g}"
            )

            percentage = (
                f"{subject['percentage']:.2f}%"
            )

            grade_point = subject["grade_point"]

            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    subject["subject_code"],
                    subject["subject_name"],
                    subject["teacher_name"],
                    marks,
                    percentage,
                    subject["grade_label"] or "-",
                    (
                        f"{grade_point:g}"
                        if grade_point is not None else "-"
                    ),
                    subject["grade_remark"] or "-",
                ),
            )

        self.summary_labels["subject_count"].configure(
            text=str(summary["subject_count"])
        )

        self.summary_labels["total_marks"].configure(
            text=(
                f"{summary['total_marks_obtained']:g} / "
                f"{summary['total_maximum_marks']:g}"
            )
        )

        overall_percentage = summary["overall_percentage"]

        self.summary_labels["overall_percentage"].configure(
            text=(
                f"{overall_percentage:.2f}%"
                if overall_percentage is not None else "-"
            )
        )

        self.summary_labels["overall_grade"].configure(
            text=summary["overall_grade_label"] or "-"
        )

        overall_point = summary["overall_grade_point"]

        self.summary_labels["grade_point"].configure(
            text=(
                f"{overall_point:g}"
                if overall_point is not None else "-"
            )
        )

        self.summary_labels["remark"].configure(
            text=summary["overall_remark"] or "-"
        )

        scheme = report["grading_scheme"]

        if scheme:
            self.scheme_label.configure(
                text=(
                    f"Grading Scheme: {scheme['name']} "
                    f"| Version {scheme['version']} "
                    f"| {scheme['status'].title()}"
                )
            )
        else:
            self.scheme_label.configure(
                text="Grading Scheme: Not available"
            )

    def export_pdf(self):
        student = self.report["student"]

        filename = (
            f"Report_Card_{student['admission_no']}.pdf"
        )

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Student Report Card",
            defaultextension=".pdf",
            initialfile=filename,
            filetypes=[
                ("PDF Documents", "*.pdf"),
            ],
        )

        if not file_path:
            return

        try:
            output_path = export_student_report_card_pdf(
                Path(file_path),
                self.report,
            )

            messagebox.showinfo(
                "Export Successful",
                f"Report card saved successfully:\n{output_path}",
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "PDF Export Error",
                str(error),
                parent=self,
            )

    def go_back(self):
        if self.on_back:
            self.on_back()
