import tempfile
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database

from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
from services.fee_charge_service import create_fee_charge
from services.fee_payment_service import (
    create_fee_payment,
    void_fee_payment,
)
from services.salary_slip_service import (
    create_salary_slip,
    issue_salary_slip,
    mark_salary_slip_paid,
)
from services.transaction_report_service import (
    get_outstanding_fee_report,
    get_outstanding_fee_summary,
    get_student_account_statement,
    get_fee_collection_summary,
    get_payroll_summary,
)


class TransactionReportServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temp_directory.name) / "test_reports.db"
        )

        self.db_path_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path,
        )
        self.db_path_patcher.start()

        self.addCleanup(self.db_path_patcher.stop)
        self.addCleanup(self.temp_directory.cleanup)

        initialize_database()

        create_initial_admin(
            "admin1", "AdminPass123", "Test Administrator"
        )
        self.admin_id = authenticate_user(
            "admin1", "AdminPass123"
        )["id"]
        self.staff_user_id = create_user(
            "staff1", "StaffPass123", "Test Staff", "staff",
            self.admin_id,
        )

        self.today = date.today()
        self.yesterday = (self.today - timedelta(days=2)).isoformat()
        self.tomorrow = (self.today + timedelta(days=2)).isoformat()

        with closing(database_module.get_connection()) as connection:
            with connection:
                student_cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("REPORT-001", "Report", "Student"),
                )
                self.student_id = student_cursor.lastrowid

                teacher_cursor = connection.execute(
                    """
                    INSERT INTO teachers (
                        employee_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("REPORT-T001", "Test", "Teacher"),
                )
                self.teacher_id = teacher_cursor.lastrowid

                staff_cursor = connection.execute(
                    """
                    INSERT INTO transport_staff (
                        employee_no,
                        first_name,
                        last_name,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        "REPORT-D001",
                        "Test",
                        "Driver",
                        "driver",
                    ),
                )
                self.staff_id = staff_cursor.lastrowid

                route_cursor = connection.execute(
                    """
                    INSERT INTO transport_routes (
                        route_code,
                        route_name
                    )
                    VALUES (?, ?)
                    """,
                    ("REPORT-R1", "Report Test Route"),
                )
                route_id = route_cursor.lastrowid

                assignment_cursor = connection.execute(
                    """
                    INSERT INTO student_transport_assignments (
                        student_id,
                        route_id,
                        start_date,
                        status
                    )
                    VALUES (?, ?, ?, 'active')
                    """,
                    (
                        self.student_id,
                        route_id,
                        self.today.isoformat(),
                    ),
                )
                self.assignment_id = assignment_cursor.lastrowid

        self._seed_fee_transactions()

    def _seed_fee_transactions(self):
        # Overdue class charge with a partial payment.
        self.class_charge_id = create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "class",
            "description": "Class fee report test",
            "amount_minor": 10000,
            "currency": "USD",
            "due_date": self.yesterday,
        }, self.admin_id)

        self.class_payment_id = create_fee_payment({
            "charge_id": self.class_charge_id,
            "amount_minor": 3000,
            "payment_date": self.today.isoformat(),
            "payment_method": "cash",}, self.admin_id)

        # Hostel payment will be voided.
        self.hostel_charge_id = create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "hostel",
            "description": "Hostel fee report test",
            "amount_minor": 20000,
            "currency": "USD",
            "due_date": self.tomorrow,
        }, self.admin_id)

        self.hostel_payment_id = create_fee_payment({
            "charge_id": self.hostel_charge_id,
            "amount_minor": 5000,
            "payment_date": self.today.isoformat(),
            "payment_method": "khqr",}, self.admin_id)

        void_fee_payment(self.hostel_payment_id,
            "Report test payment reversal", self.admin_id)

        # Bus fee uses KHR and an active transport assignment.
        self.bus_charge_id = create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "bus",
            "description": "Bus fee report test",
            "amount_minor": 100000,
            "currency": "KHR",
            "due_date": self.tomorrow,
            "transport_assignment_id": self.assignment_id,
        }, self.admin_id)

        self.bus_payment_id = create_fee_payment({
            "charge_id": self.bus_charge_id,
            "amount_minor": 25000,
            "payment_date": self.today.isoformat(),
            "payment_method": "bank_transfer",}, self.admin_id)

    def test_01_outstanding_fee_report(self):
        report = get_outstanding_fee_report(
            as_of_date=self.today.isoformat(),
            actor_user_id=self.admin_id,
        )

        self.assertEqual(len(report), 3)

        by_type = {
            item["fee_type"]: item
            for item in report
        }

        self.assertEqual(
            by_type["class"]["payment_status"],
            "overdue",
        )
        self.assertEqual(
            by_type["class"]["balance_minor"],
            7000,
        )

        self.assertEqual(
            by_type["hostel"]["payment_status"],
            "unpaid",
        )
        self.assertEqual(
            by_type["hostel"]["balance_minor"],
            20000,
        )

        self.assertEqual(
            by_type["bus"]["payment_status"],
            "partial",
        )
        self.assertEqual(
            by_type["bus"]["balance_minor"],
            75000,
        )

    def test_02_outstanding_fee_summary_keeps_currencies_separate(self):
        summary = get_outstanding_fee_summary(
            as_of_date=self.today.isoformat(),
            actor_user_id=self.admin_id,
        )

        by_key = {
            (item["currency"], item["fee_type"]): item
            for item in summary
        }

        self.assertEqual(
            by_key[("USD", "class")]["total_outstanding_minor"],
            7000,
        )
        self.assertEqual(
            by_key[("USD", "hostel")]["total_outstanding_minor"],
            20000,
        )
        self.assertEqual(
            by_key[("KHR", "bus")]["total_outstanding_minor"],
            75000,
        )

    def test_03_student_statement_includes_original_payment_and_reversal(self):
        statement = get_student_account_statement(
            self.student_id,
            actor_user_id=self.admin_id,
        )

        self.assertEqual(
            statement["student"]["admission_no"],
            "REPORT-001",
        )

        entries = statement["entries"]

        # Three charges, three original payments, one reversal.
        self.assertEqual(len(entries), 7)

        hostel_payment_events = [
            item
            for item in entries
            if item["reference_no"] ==
               self._get_receipt_no(self.hostel_payment_id)
        ]

        self.assertEqual(
            [item["entry_type"] for item in hostel_payment_events],
            ["payment", "payment_void"],
        )

        self.assertEqual(
            statement["closing_balances"]["USD"],
            27000,
        )
        self.assertEqual(
            statement["closing_balances"]["KHR"],
            75000,
        )

    def _get_receipt_no(self, payment_id):
        with closing(database_module.get_connection()) as connection:
            row = connection.execute(
                """
                SELECT receipt_no
                FROM fee_payments
                WHERE id = ?
                """,
                (payment_id,),
            ).fetchone()

        return row["receipt_no"]

    def test_04_fee_collection_summary_nets_voided_payments_correctly(self):
        summary = get_fee_collection_summary(
            actor_user_id=self.admin_id,
        )

        by_key = {
            (item["currency"], item["fee_type"]): item
            for item in summary
        }

        self.assertEqual(
            by_key[("USD", "class")]["net_collected_minor"],
            3000,
        )

        self.assertEqual(
            by_key[("USD", "hostel")]["posted_amount_minor"],
            5000,
        )
        self.assertEqual(
            by_key[("USD", "hostel")]["voided_amount_minor"],
            5000,
        )
        self.assertEqual(
            by_key[("USD", "hostel")]["net_collected_minor"],
            0,
        )

        self.assertEqual(
            by_key[("KHR", "bus")]["net_collected_minor"],
            25000,
        )

    def test_05_payroll_summary(self):
        period_start = self.today.replace(day=1).isoformat()
        period_end = self.today.isoformat()

        teacher_slip_id = create_salary_slip({
            "teacher_id": self.teacher_id,
            "pay_period_start": period_start,
            "pay_period_end": period_end,
            "base_salary_minor": 500000,
            "allowances_minor": 50000,
            "deductions_minor": 25000,
            "currency": "USD",
        }, self.admin_id)

        issue_salary_slip(teacher_slip_id, self.admin_id)

        mark_salary_slip_paid(
            teacher_slip_id,
            self.today.isoformat(),
            "bank_transfer",
            "REPORT-PAY-001",
            actor_user_id=self.admin_id,
        )

        create_salary_slip({
            "transport_staff_id": self.staff_id,
            "pay_period_start": period_start,
            "pay_period_end": period_end,
            "base_salary_minor": 300000,
            "allowances_minor": 20000,
            "deductions_minor": 10000,
            "currency": "KHR",
        }, self.admin_id)

        summary = get_payroll_summary(
            start_date=period_start,
            end_date=period_end,
            actor_user_id=self.admin_id,
        )

        by_key = {
            (
                item["currency"],
                item["employee_type"],
                item["status"],
            ): item
            for item in summary
        }

        self.assertEqual(
            by_key[("USD", "teacher", "paid")]["net_salary_minor"],
            525000,
        )

        self.assertEqual(
            by_key[("KHR", "transport_staff", "draft")]["net_salary_minor"],
            310000,
        )

    def test_06_invalid_report_filters_are_rejected(self):
        with self.assertRaises(ValueError):
            get_outstanding_fee_report(
                currency="US D",
                actor_user_id=self.admin_id,
            )

        with self.assertRaises(ValueError):
            get_outstanding_fee_report(
                fee_type="unknown",
                actor_user_id=self.admin_id,
            )

        with self.assertRaises(ValueError):
            get_student_account_statement(
                999999,
                actor_user_id=self.admin_id,
            )

        with self.assertRaises(ValueError):
            get_fee_collection_summary(
                start_date=self.tomorrow,
                end_date=self.yesterday,
                actor_user_id=self.admin_id,
            )

        with self.assertRaises(ValueError):
            get_payroll_summary(
                status="unknown",
                actor_user_id=self.admin_id,
            )

    def test_07_report_role_authorization(self):
        with self.assertRaises(PermissionError):
            get_outstanding_fee_report(
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_outstanding_fee_summary(
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_student_account_statement(
                self.student_id,
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_fee_collection_summary(
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_payroll_summary(
                actor_user_id=self.staff_user_id,
            )

    def test_08_temporary_database_integrity(self):
        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


if __name__ == "__main__":
    unittest.main()
