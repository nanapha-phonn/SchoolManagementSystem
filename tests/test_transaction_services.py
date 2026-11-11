import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from database.database import initialize_database

from services.auth_service import create_initial_admin, authenticate_user
from services.user_service import create_user
from services.fee_charge_service import (
    create_fee_charge,
    get_fee_charge,
    get_fee_charges,
    void_fee_charge,
)
from services.fee_payment_service import (
    create_fee_payment,
    get_fee_payment,
    get_fee_payments,
    void_fee_payment,
)
from services.salary_slip_service import (
    create_salary_slip,
    get_salary_slip,
    get_salary_slips,
    issue_salary_slip,
    mark_salary_slip_paid,
    void_salary_slip,
)


class TransactionServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temp_directory.name) / "test_transactions.db"
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

        self.today = date.today().isoformat()

        # Create test records in the temporary database.
        with closing(database_module.get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("TX-STU-001", "Test", "Student"),
                )
                self.student_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("TX-STU-002", "Other", "Student"),
                )
                self.other_student_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO teachers (
                        employee_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("TX-TEACH-001", "Test", "Teacher"),
                )
                self.teacher_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO transport_staff (
                        employee_no,
                        first_name,
                        last_name,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    ("TX-DRIVER-001", "Test", "Driver", "driver"),
                )
                self.staff_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO transport_routes (
                        route_code,
                        route_name
                    )
                    VALUES (?, ?)
                    """,
                    ("TX-ROUTE-001", "Transaction Test Route"),
                )
                route_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO student_transport_assignments (
                        student_id,
                        route_id,
                        start_date,
                        status
                    )
                    VALUES (?, ?, ?, 'active')
                    """,
                    (self.student_id, route_id, self.today),
                )
                self.assignment_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO student_transport_assignments (
                        student_id,
                        route_id,
                        start_date,
                        status
                    )
                    VALUES (?, ?, ?, 'active')
                    """,
                    (self.other_student_id, route_id, self.today),
                )
                self.other_assignment_id = cursor.lastrowid

    # --------------------------------------------------
    # TEST HELPERS
    # --------------------------------------------------

    def make_charge(self, **overrides):
        data = {
            "student_id": self.student_id,
            "fee_type": "class",
            "description": "Transaction test fee",
            "amount_minor": 10000,
            "currency": "USD",
        }
        data.update(overrides)

        if data["fee_type"] == "bus":
            data.setdefault(
                "transport_assignment_id",
                self.assignment_id,
            )

        return create_fee_charge(data, self.admin_id)

    def make_payment(self, charge_id, default_amount_minor, **overrides):
        data = {
            "charge_id": charge_id,
            "amount_minor": default_amount_minor,
            "payment_date": self.today,
            "payment_method": "cash",
        }
        data.update(overrides)

        return create_fee_payment(data, self.admin_id)

    def make_salary(self, **overrides):
        data = {
            "teacher_id": self.teacher_id,
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-31",
            "base_salary_minor": 500000,
            "allowances_minor": 50000,
            "deductions_minor": 25000,
            "currency": "USD",
        }
        data.update(overrides)

        return create_salary_slip(data, self.admin_id)

    # ==================================================
    # FEE CHARGE TESTS
    # ==================================================

    def test_01_create_and_retrieve_fee_charge(self):
        charge_id = self.make_charge()

        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertIsNotNone(charge)
        self.assertTrue(charge["charge_no"].startswith("CHG-"))
        self.assertEqual(charge["student_id"], self.student_id)
        self.assertEqual(charge["amount_minor"], 10000)
        self.assertEqual(charge["amount_paid_minor"], 0)
        self.assertEqual(charge["balance_minor"], 10000)
        self.assertEqual(charge["payment_status"], "unpaid")

    def test_02_reject_invalid_fee_charge(self):
        invalid_cases = [
            {"amount_minor": 0},
            {"amount_minor": -100},
            {"fee_type": "unknown"},
            {"description": ""},
            {"currency": "US"},
            {"due_date": "03-11-2026"},
        ]

        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.make_charge(**overrides)

        self.assertEqual(len(get_fee_charges(actor_user_id=self.admin_id)), 0)

    def test_03_bus_charge_requires_transport_assignment(self):
        with self.assertRaisesRegex(
            ValueError,
            "transport assignment",
        ):
            create_fee_charge({
                "student_id": self.student_id,
                "fee_type": "bus",
                "description": "Bus fee",
                "amount_minor": 2000,
            }, self.admin_id)

    def test_04_reject_assignment_belonging_to_another_student(self):
        with self.assertRaisesRegex(
            ValueError,
            "does not belong",
        ):
            self.make_charge(
                fee_type="bus",
                transport_assignment_id=self.other_assignment_id,
            )

    def test_05_search_and_filter_fee_charges(self):
        self.make_charge(description="Class November")
        self.make_charge(
            fee_type="hostel",
            description="Hostel November",
            amount_minor=5000,
        )

        self.assertEqual(len(get_fee_charges(actor_user_id=self.admin_id)), 2)

        self.assertEqual(
            len(get_fee_charges(fee_type="class", actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_fee_charges(fee_type="hostel", actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_fee_charges(search="Hostel", actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_fee_charges(student_id=self.student_id, actor_user_id=self.admin_id)),
            2,
        )

    def test_06_void_unpaid_charge(self):
        charge_id = self.make_charge()

        void_fee_charge(charge_id, "Test cancellation", self.admin_id)

        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertEqual(charge["status"], "voided")
        self.assertEqual(charge["payment_status"], "voided")
        self.assertEqual(charge["void_reason"], "Test cancellation")

    def test_07_cannot_void_charge_with_posted_payment(self):
        charge_id = self.make_charge()
        self.make_payment(charge_id, 2000)

        with self.assertRaisesRegex(ValueError, "posted payments"):
            void_fee_charge(charge_id, "Cancellation attempt", self.admin_id)

        self.assertEqual(
            get_fee_charge(charge_id, self.admin_id)["status"],
            "open",
        )

    # ==================================================
    # FEE PAYMENT TESTS
    # ==================================================

    def test_08_create_partial_and_full_payments(self):
        charge_id = self.make_charge()

        first_id = self.make_payment(charge_id, 4000)
        second_id = self.make_payment(
            charge_id,
            6000,
            payment_method="khqr",
        )

        first = get_fee_payment(first_id, self.admin_id)
        second = get_fee_payment(second_id, self.admin_id)
        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertTrue(first["receipt_no"].startswith("RCPT-"))
        self.assertNotEqual(first["receipt_no"], second["receipt_no"])

        self.assertEqual(first["status"], "posted")
        self.assertEqual(second["status"], "posted")

        self.assertEqual(charge["amount_paid_minor"], 10000)
        self.assertEqual(charge["balance_minor"], 0)
        self.assertEqual(charge["payment_status"], "paid")

    def test_09_reject_overpayment(self):
        charge_id = self.make_charge()

        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.make_payment(charge_id, 11000)

        self.assertEqual(len(get_fee_payments(actor_user_id=self.admin_id)), 0)

    def test_10_reject_payment_after_full_payment(self):
        charge_id = self.make_charge()
        self.make_payment(charge_id, 10000)

        with self.assertRaisesRegex(ValueError, "fully paid"):
            self.make_payment(charge_id, 100)

    def test_11_void_payment_restores_balance(self):
        charge_id = self.make_charge()
        payment_id = self.make_payment(charge_id, 4000)

        void_fee_payment(payment_id, "Test reversal", self.admin_id)

        payment = get_fee_payment(payment_id, self.admin_id)
        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertEqual(payment["status"], "voided")
        self.assertEqual(payment["void_reason"], "Test reversal")
        self.assertEqual(charge["amount_paid_minor"], 0)
        self.assertEqual(charge["balance_minor"], 10000)

    def test_12_prevent_duplicate_payment_void(self):
        charge_id = self.make_charge()
        payment_id = self.make_payment(charge_id, 2000)

        void_fee_payment(payment_id, "First void", self.admin_id)

        with self.assertRaisesRegex(ValueError, "already voided"):
            void_fee_payment(payment_id, "Second void", self.admin_id)

    def test_13_reject_invalid_payment_data(self):
        charge_id = self.make_charge()

        invalid_cases = [
            {"amount_minor": 0},
            {"amount_minor": -500},
            {"payment_method": "bitcoin"},
            {"payment_date": "03-11-2026"},
            {"payment_date": "2999-01-01"},
        ]

        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.make_payment(
                        charge_id,
                        1000,
                        **overrides,
                    )

        self.assertEqual(len(get_fee_payments(actor_user_id=self.admin_id)), 0)

    # ==================================================
    # SALARY SLIP TESTS
    # ==================================================

    def test_14_create_and_calculate_teacher_salary(self):
        slip_id = self.make_salary()

        slip = get_salary_slip(slip_id, self.admin_id)

        self.assertTrue(slip["slip_no"].startswith("SAL-"))
        self.assertEqual(slip["employee_type"], "teacher")
        self.assertEqual(slip["employee_no"], "TX-TEACH-001")
        self.assertEqual(slip["base_salary_minor"], 500000)
        self.assertEqual(slip["net_salary_minor"], 525000)
        self.assertEqual(slip["status"], "draft")

    def test_15_prevent_duplicate_employee_pay_period(self):
        self.make_salary()

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.make_salary()

    def test_16_salary_draft_issued_paid_workflow(self):
        slip_id = self.make_salary()

        issue_salary_slip(slip_id, self.admin_id)
        issued = get_salary_slip(slip_id, self.admin_id)

        self.assertEqual(issued["status"], "issued")
        self.assertIsNotNone(issued["issued_at"])

        mark_salary_slip_paid(
            slip_id,
            self.today,
            "bank_transfer",
            "TX-PAYROLL-001",
            actor_user_id=self.admin_id,
        )

        paid = get_salary_slip(slip_id, self.admin_id)

        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["payment_date"], self.today)
        self.assertEqual(paid["payment_method"], "bank_transfer")
        self.assertEqual(
            paid["transaction_reference"],
            "TX-PAYROLL-001",
        )
        self.assertIsNotNone(paid["paid_at"])

    def test_17_cannot_mark_draft_salary_as_paid(self):
        slip_id = self.make_salary()

        with self.assertRaisesRegex(ValueError, "Only issued"):
            mark_salary_slip_paid(
                slip_id,
                self.today,
                "cash",
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_salary_slip(slip_id, self.admin_id)["status"],
            "draft",
        )

    def test_18_paid_salary_cannot_be_voided(self):
        slip_id = self.make_salary()
        issue_salary_slip(slip_id, self.admin_id)

        mark_salary_slip_paid(
            slip_id,
            self.today,
            "cash",
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "payroll reversal"):
            void_salary_slip(slip_id, "Test void", self.admin_id)

        self.assertEqual(
            get_salary_slip(slip_id, self.admin_id)["status"],
            "paid",
        )

    def test_19_transport_staff_salary_and_replacement(self):
        slip_id = self.make_salary(
            teacher_id=None,
            transport_staff_id=self.staff_id,
            base_salary_minor=300000,
            allowances_minor=20000,
            deductions_minor=10000,
            currency="KHR",
        )

        slip = get_salary_slip(slip_id, self.admin_id)

        self.assertEqual(slip["employee_type"], "transport_staff")
        self.assertEqual(slip["employee_no"], "TX-DRIVER-001")
        self.assertEqual(slip["net_salary_minor"], 310000)

        void_salary_slip(slip_id, "Test draft cancellation", self.admin_id)

        replacement_id = self.make_salary(
            teacher_id=None,
            transport_staff_id=self.staff_id,
            base_salary_minor=310000,
            allowances_minor=0,
            deductions_minor=0,
            currency="KHR",
        )

        self.assertNotEqual(slip_id, replacement_id)
        self.assertEqual(
            get_salary_slip(replacement_id, self.admin_id)["status"],
            "draft",
        )

    def test_20_reject_nonexistent_salary_employee(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.make_salary(
                teacher_id=999999,
            )

    def test_21_search_and_filter_salary_slips(self):
        teacher_slip = self.make_salary()

        staff_slip = self.make_salary(
            teacher_id=None,
            transport_staff_id=self.staff_id,
            pay_period_start="2026-02-01",
            pay_period_end="2026-02-28",
            currency="KHR",
        )

        teacher_results = get_salary_slips(
            employee_type="teacher",
            employee_id=self.teacher_id,
            actor_user_id=self.admin_id,
        )

        staff_results = get_salary_slips(
            employee_type="transport_staff",
            employee_id=self.staff_id,
            actor_user_id=self.admin_id,
        )

        searched = get_salary_slips(
            search="TX-TEACH-001",
            actor_user_id=self.admin_id,
        )

        drafts = get_salary_slips(status="draft", actor_user_id=self.admin_id)

        self.assertEqual(len(teacher_results), 1)
        self.assertEqual(teacher_results[0]["id"], teacher_slip)
        self.assertEqual(len(staff_results), 1)
        self.assertEqual(staff_results[0]["id"], staff_slip)
        self.assertEqual(len(searched), 1)
        self.assertEqual(len(drafts), 2)

    # ==================================================
    # DATABASE INTEGRITY
    # ==================================================

    def test_22_temporary_database_integrity(self):
        charge_id = self.make_charge()
        self.make_payment(charge_id, 1000)
        self.make_salary()

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
