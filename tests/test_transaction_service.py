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
                    ("TX-STU-001", "Transaction", "Student"),
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
                    ("TX-STU-002", "Second", "Student"),
                )
                self.second_student_id = cursor.lastrowid

                cursor = connection.execute(
                    """
                    INSERT INTO teachers (
                        employee_no,
                        first_name,
                        last_name
                    )
                    VALUES (?, ?, ?)
                    """,
                    ("TX-TEA-001", "Test", "Teacher"),
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
                    ("TX-STAFF-001", "Test", "Driver", "driver"),
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
                    ("TX-ROUTE-001", "Test Route"),
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
                    (
                        self.student_id,
                        route_id,
                        date.today().isoformat(),
                    ),
                )
                self.assignment_id = cursor.lastrowid

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def create_class_charge(self, amount=10000, **overrides):
        data = {
            "student_id": self.student_id,
            "fee_type": "class",
            "description": "Test class fee",
            "amount_minor": amount,
            "currency": "USD",
        }
        data.update(overrides)

        return create_fee_charge(data, self.admin_id)

    def create_payment(self, charge_id, amount, **overrides):
        data = {
            "charge_id": charge_id,
            "amount_minor": amount,
            "payment_date": date.today().isoformat(),
            "payment_method": "cash",
        }
        data.update(overrides)

        return create_fee_payment(data, self.admin_id)

    def create_teacher_salary(self, **overrides):
        data = {
            "teacher_id": self.teacher_id,
            "pay_period_start": "2026-11-01",
            "pay_period_end": "2026-11-30",
            "base_salary_minor": 500000,
            "allowances_minor": 50000,
            "deductions_minor": 25000,
            "currency": "USD",
        }
        data.update(overrides)

        return create_salary_slip(data, self.admin_id)

    # --------------------------------------------------
    # FEE CHARGE TESTS
    # --------------------------------------------------

    def test_01_create_fee_charge(self):
        charge_id = self.create_class_charge()

        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertIsNotNone(charge)
        self.assertTrue(charge["charge_no"].startswith("CHG-"))
        self.assertEqual(charge["amount_minor"], 10000)
        self.assertEqual(charge["balance_minor"], 10000)
        self.assertEqual(charge["payment_status"], "unpaid")

    def test_02_reject_invalid_fee_charge(self):
        invalid_cases = [
            {"fee_type": "unknown"},
            {"amount_minor": 0},
            {"amount_minor": -100},
            {"description": ""},
            {"currency": "INVALID"},
            {"student_id": 999999},
        ]

        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.create_class_charge(**overrides)

    def test_03_bus_charge_requires_correct_assignment(self):
        with self.assertRaisesRegex(
            ValueError,
            "transport assignment is required",
        ):
            create_fee_charge({
                "student_id": self.student_id,
                "fee_type": "bus",
                "description": "Bus fee",
                "amount_minor": 2000,
            }, self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "does not belong to this student",
        ):
            create_fee_charge({
                "student_id": self.second_student_id,
                "fee_type": "bus",
                "description": "Bus fee",
                "amount_minor": 2000,
                "transport_assignment_id": self.assignment_id,
            }, self.admin_id)

        bus_charge_id = create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "bus",
            "description": "Bus fee",
            "amount_minor": 2000,
            "transport_assignment_id": self.assignment_id,
            "currency": "KHR",
        }, self.admin_id)

        self.assertIsNotNone(get_fee_charge(bus_charge_id, self.admin_id))

    def test_04_fee_charge_search_and_filter(self):
        self.create_class_charge()

        create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "hostel",
            "description": "Test hostel fee",
            "amount_minor": 5000,
            "currency": "KHR",
        }, self.admin_id)

        self.assertEqual(len(get_fee_charges(actor_user_id=self.admin_id)), 2)
        self.assertEqual(
            len(get_fee_charges(fee_type="class", actor_user_id=self.admin_id)),
            1,
        )
        self.assertEqual(
            len(get_fee_charges(search="TX-STU-001", actor_user_id=self.admin_id)),
            2,
        )

    def test_05_void_fee_charge_rules(self):
        unpaid_charge = self.create_class_charge()

        void_fee_charge(unpaid_charge, "Test cancellation", self.admin_id)

        charge = get_fee_charge(unpaid_charge, self.admin_id)

        self.assertEqual(charge["status"], "voided")
        self.assertEqual(charge["payment_status"], "voided")

        paid_charge = self.create_class_charge()

        self.create_payment(paid_charge, 1000)

        with self.assertRaisesRegex(
            ValueError,
            "posted payments",
        ):
            void_fee_charge(paid_charge, "Not allowed", self.admin_id)

    def test_06_fee_charge_role_authorization(self):
        # Staff can create a charge. A submitted created_by value
        # must never override the authenticated actor.
        charge_id = create_fee_charge({
            "student_id": self.student_id,
            "fee_type": "class",
            "description": "Staff-created class fee",
            "amount_minor": 7500,
            "currency": "USD",
            "created_by": self.admin_id,
        }, self.staff_user_id)

        charge = get_fee_charge(charge_id, self.staff_user_id)

        self.assertIsNotNone(charge)
        self.assertEqual(charge["created_by"], self.staff_user_id)

        # Staff can list charges.
        charges = get_fee_charges(
            student_id=self.student_id,
            actor_user_id=self.staff_user_id,
        )
        self.assertTrue(any(item["id"] == charge_id for item in charges))

        # Staff cannot void charges.
        with self.assertRaises(PermissionError):
            void_fee_charge(
                charge_id,
                "Staff should not be allowed to void",
                self.staff_user_id,
            )

        # The failed attempt must not change the charge.
        charge = get_fee_charge(charge_id, self.admin_id)
        self.assertEqual(charge["status"], "open")

        # Missing/inactive actor IDs must not access fee charges.
        with self.assertRaises(PermissionError):
            get_fee_charge(charge_id, None)

        with self.assertRaises(PermissionError):
            get_fee_charges(actor_user_id=None)

    # --------------------------------------------------
    # FEE PAYMENT TESTS
    # --------------------------------------------------

    def test_06_partial_and_full_payment(self):
        charge_id = self.create_class_charge()

        first_id = self.create_payment(charge_id, 4000)
        second_id = self.create_payment(charge_id, 6000)

        first = get_fee_payment(first_id, self.admin_id)
        second = get_fee_payment(second_id, self.admin_id)

        self.assertNotEqual(
            first["receipt_no"],
            second["receipt_no"],
        )

        self.assertTrue(first["receipt_no"].startswith("RCPT-"))

        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertEqual(charge["amount_paid_minor"], 10000)
        self.assertEqual(charge["balance_minor"], 0)
        self.assertEqual(charge["payment_status"], "paid")

    def test_07_prevent_overpayment(self):
        charge_id = self.create_class_charge()

        self.create_payment(charge_id, 7000)

        with self.assertRaisesRegex(
            ValueError,
            "exceeds",
        ):
            self.create_payment(charge_id, 4000)

        self.assertEqual(
            get_fee_charge(charge_id, self.admin_id)["balance_minor"],
            3000,
        )

    def test_08_void_payment_restores_balance(self):
        charge_id = self.create_class_charge()

        payment_id = self.create_payment(charge_id, 4000)

        void_fee_payment(payment_id,
            "Test reversal", self.admin_id)

        payment = get_fee_payment(payment_id, self.admin_id)
        charge = get_fee_charge(charge_id, self.admin_id)

        self.assertEqual(payment["status"], "voided")
        self.assertEqual(
            payment["void_reason"],
            "Test reversal",
        )
        self.assertEqual(charge["amount_paid_minor"], 0)
        self.assertEqual(charge["balance_minor"], 10000)

    def test_09_reject_invalid_payment_and_void_reason(self):
        charge_id = self.create_class_charge()

        invalid_cases = [
            {"amount_minor": 0},
            {"amount_minor": -100},
            {"payment_method": "invalid"},
            {"payment_date": "invalid-date"},
        ]

        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.create_payment(
                        charge_id,
                        1000,
                        **overrides,
                    )

        payment_id = self.create_payment(charge_id, 1000)

        with self.assertRaisesRegex(
            ValueError,
            "reason is required",
        ):
            void_fee_payment(payment_id, "", self.admin_id)

    def test_10_payment_history_search(self):
        charge_id = self.create_class_charge()

        first_id = self.create_payment(charge_id, 2000)
        second_id = self.create_payment(charge_id, 3000)

        self.assertEqual(
            len(get_fee_payments(charge_id=charge_id, actor_user_id=self.admin_id)),
            2,
        )

        self.assertIsNotNone(get_fee_payment(first_id, self.admin_id))
        self.assertIsNotNone(get_fee_payment(second_id, self.admin_id))

        self.assertEqual(
            len(get_fee_payments(search="TX-STU-001", actor_user_id=self.admin_id)),
            2,
        )

    def test_fee_payment_role_authorization(self):
        charge_id = self.create_class_charge()

        # Staff can create a payment. A submitted received_by value
        # must never override the authenticated actor.
        payment_id = create_fee_payment({
            "charge_id": charge_id,
            "amount_minor": 2500,
            "payment_date": date.today().isoformat(),
            "payment_method": "cash",
            "received_by": self.admin_id,
        }, self.staff_user_id)

        payment = get_fee_payment(payment_id, self.staff_user_id)

        self.assertIsNotNone(payment)
        self.assertEqual(payment["received_by"], self.staff_user_id)
        self.assertEqual(payment["status"], "posted")

        # Staff can list payment history.
        payments = get_fee_payments(
            charge_id=charge_id,
            actor_user_id=self.staff_user_id,
        )
        self.assertTrue(
            any(item["id"] == payment_id for item in payments)
        )

        # Staff cannot void payments.
        with self.assertRaises(PermissionError):
            void_fee_payment(
                payment_id,
                "Staff should not be allowed to void",
                self.staff_user_id,
            )

        # The failed attempt must not change the payment.
        payment = get_fee_payment(payment_id, self.admin_id)
        self.assertEqual(payment["status"], "posted")

        # Missing actor IDs must be rejected.
        with self.assertRaises(PermissionError):
            create_fee_payment({
                "charge_id": charge_id,
                "amount_minor": 1000,
                "payment_date": date.today().isoformat(),
                "payment_method": "cash",
            }, None)

        with self.assertRaises(PermissionError):
            get_fee_payment(payment_id, None)

        with self.assertRaises(PermissionError):
            get_fee_payments(actor_user_id=None)

        with self.assertRaises(PermissionError):
            void_fee_payment(
                payment_id,
                "Missing actor",
                None,
            )

    # --------------------------------------------------
    # SALARY SLIP TESTS
    # --------------------------------------------------

    def test_11_salary_slip_calculation(self):
        slip_id = self.create_teacher_salary()

        slip = get_salary_slip(slip_id, self.admin_id)

        self.assertIsNotNone(slip)
        self.assertTrue(slip["slip_no"].startswith("SAL-"))
        self.assertEqual(slip["net_salary_minor"], 525000)
        self.assertEqual(slip["status"], "draft")

    def test_12_prevent_duplicate_salary_period(self):
        self.create_teacher_salary()

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            self.create_teacher_salary()

    def test_13_salary_status_transitions(self):
        slip_id = self.create_teacher_salary()

        issue_salary_slip(slip_id, self.admin_id)

        self.assertEqual(
            get_salary_slip(slip_id, self.admin_id)["status"],
            "issued",
        )

        mark_salary_slip_paid(
            slip_id,
            date.today().isoformat(),
            "bank_transfer",
            "TEST-PAYROLL-001",
            actor_user_id=self.admin_id,
        )

        slip = get_salary_slip(slip_id, self.admin_id)

        self.assertEqual(slip["status"], "paid")
        self.assertEqual(
            slip["payment_method"],
            "bank_transfer",
        )
        self.assertEqual(
            slip["transaction_reference"],
            "TEST-PAYROLL-001",
        )

        with self.assertRaisesRegex(
            ValueError,
            "payroll reversal",
        ):
            void_salary_slip(
                slip_id,
                "Paid slip reversal",
                self.admin_id,
            )

    def test_14_salary_slip_void_and_replacement(self):
        slip_id = self.create_teacher_salary()

        void_salary_slip(
            slip_id,
            "Test draft cancellation",
            self.admin_id,
        )

        self.assertEqual(
            get_salary_slip(slip_id, self.admin_id)["status"],
            "voided",
        )

        replacement_id = self.create_teacher_salary()

        self.assertNotEqual(slip_id, replacement_id)
        self.assertEqual(
            get_salary_slip(replacement_id, self.admin_id)["status"],
            "draft",
        )

    def test_15_transport_staff_salary_slip(self):
        slip_id = create_salary_slip({
            "transport_staff_id": self.staff_id,
            "pay_period_start": "2026-11-01",
            "pay_period_end": "2026-11-30",
            "base_salary_minor": 300000,
            "allowances_minor": 20000,
            "deductions_minor": 10000,
            "currency": "KHR",
        }, self.admin_id)

        slip = get_salary_slip(slip_id, self.admin_id)

        self.assertEqual(
            slip["employee_type"],
            "transport_staff",
        )
        self.assertEqual(slip["net_salary_minor"], 310000)

    def test_16_salary_slip_search_and_filter(self):
        self.create_teacher_salary()

        self.assertEqual(
            len(get_salary_slips(status="draft", actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_salary_slips(search="TX-TEA-001", actor_user_id=self.admin_id)),
            1,
        )

    def test_17_salary_slip_role_authorization(self):
        slip_id = self.create_teacher_salary()

        salary_data = {
            "teacher_id": self.teacher_id,
            "pay_period_start": "2026-12-01",
            "pay_period_end": "2026-12-31",
            "base_salary_minor": 500000,
            "allowances_minor": 50000,
            "deductions_minor": 25000,
            "currency": "USD",
        }

        with self.assertRaises(PermissionError):
            create_salary_slip(
                salary_data,
                self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_salary_slip(
                slip_id,
                self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            get_salary_slips(
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            issue_salary_slip(
                slip_id,
                self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            mark_salary_slip_paid(
                slip_id,
                date.today().isoformat(),
                "cash",
                actor_user_id=self.staff_user_id,
            )

        with self.assertRaises(PermissionError):
            void_salary_slip(
                slip_id,
                "Staff authorization test",
                self.staff_user_id,
            )

        self.assertEqual(
            get_salary_slip(slip_id, self.admin_id)["status"],
            "draft",
        )

        self.assertEqual(
            len(get_salary_slips(actor_user_id=self.admin_id)),
            1,
        )

    # --------------------------------------------------
    # DATABASE INTEGRITY
    # --------------------------------------------------

    def test_18_database_integrity(self):
        charge_id = self.create_class_charge()
        self.create_payment(charge_id, 2000)
        self.create_teacher_salary()

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
