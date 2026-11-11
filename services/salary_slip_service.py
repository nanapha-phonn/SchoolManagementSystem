import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import date

from database.database import get_connection
from models.salary_slip import SalarySlip
from models.fee_payment import VALID_PAYMENT_METHODS
from services.permission_service import require_permission


def _validate_employee(connection, salary):
    if salary.teacher_id is not None:
        employee = connection.execute(
            "SELECT id FROM teachers WHERE id = ?",
            (salary.teacher_id,)
        ).fetchone()

        if not employee:
            raise ValueError("Selected teacher was not found.")

    else:
        employee = connection.execute(
            "SELECT id FROM transport_staff WHERE id = ?",
            (salary.transport_staff_id,)
        ).fetchone()

        if not employee:
            raise ValueError("Selected transport staff member was not found.")


def create_salary_slip(salary_data, actor_user_id):
    require_permission(actor_user_id, "payroll.manage")
    trusted_data = dict(salary_data)
    trusted_data["created_by"] = actor_user_id
    salary = SalarySlip(**trusted_data).validate()
    data = asdict(salary)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                _validate_employee(connection, salary)

                cursor = connection.execute(
                    """
                    INSERT INTO salary_slips (
                        slip_no,
                        school_id,
                        teacher_id,
                        transport_staff_id,
                        pay_period_start,
                        pay_period_end,
                        base_salary_minor,
                        allowances_minor,
                        deductions_minor,
                        net_salary_minor,
                        currency,
                        created_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PENDING-{salary.teacher_id or salary.transport_staff_id}",
                        data["school_id"],
                        data["teacher_id"],
                        data["transport_staff_id"],
                        data["pay_period_start"],
                        data["pay_period_end"],
                        data["base_salary_minor"],
                        data["allowances_minor"],
                        data["deductions_minor"],
                        data["net_salary_minor"],
                        data["currency"],
                        data["created_by"],
                    )
                )

                slip_id = cursor.lastrowid

                slip_no = (
                    f"SAL-{data['pay_period_end'][:4]}-{slip_id:06d}"
                )

                connection.execute(
                    """
                    UPDATE salary_slips
                    SET slip_no = ?
                    WHERE id = ?
                    """,
                    (slip_no, slip_id)
                )

                return slip_id

    except sqlite3.IntegrityError as error:
        message = str(error)

        if "salary_slips.teacher_id" in message or (
            "salary_slips.transport_staff_id" in message
        ):
            raise ValueError(
                "A non-voided salary slip already exists "
                "for this employee and pay period."
            )

        raise ValueError(f"Could not create salary slip: {error}")


def _salary_select():
    return """
        SELECT
            ss.*,
            CASE
                WHEN ss.teacher_id IS NOT NULL THEN 'teacher'
                ELSE 'transport_staff'
            END AS employee_type,
            COALESCE(t.employee_no, ts.employee_no) AS employee_no,
            COALESCE(t.first_name, ts.first_name) AS first_name,
            COALESCE(t.last_name, ts.last_name) AS last_name
        FROM salary_slips AS ss
        LEFT JOIN teachers AS t
            ON t.id = ss.teacher_id
        LEFT JOIN transport_staff AS ts
            ON ts.id = ss.transport_staff_id
    """


def get_salary_slip(slip_id, actor_user_id):
    require_permission(actor_user_id, "payroll.manage")
    with closing(get_connection()) as connection:
        row = connection.execute(
            _salary_select() + " WHERE ss.id = ?",
            (slip_id,)
        ).fetchone()

        return dict(row) if row else None


def get_salary_slips(
    employee_type=None,
    employee_id=None,
    status=None,
    search="",
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "payroll.manage")
    conditions = []
    parameters = []

    if employee_type:
        employee_type = employee_type.strip().lower()

        if employee_type not in {"teacher", "transport_staff"}:
            raise ValueError("Invalid employee type.")

        if employee_id is None:
            raise ValueError("Employee ID is required with employee type.")

        try:
            employee_id = int(employee_id)
        except (TypeError, ValueError):
            raise ValueError("Employee ID must be a positive integer.")

        if employee_id <= 0:
            raise ValueError("Employee ID must be a positive integer.")

        employee_column = (
            "ss.teacher_id"
            if employee_type == "teacher"
            else "ss.transport_staff_id"
        )

        conditions.append(f"{employee_column} = ?")
        parameters.append(employee_id)

    elif employee_id is not None:
        raise ValueError(
            "Employee type is required when filtering by employee ID."
        )

    if status:
        status = status.strip().lower()

        if status not in {"draft", "issued", "paid", "voided"}:
            raise ValueError("Invalid salary slip status.")

        conditions.append("ss.status = ?")
        parameters.append(status)

    search = search.strip()

    if search:
        pattern = f"%{search}%"

        conditions.append(
            """
            (
                ss.slip_no LIKE ?
                OR ss.transaction_reference LIKE ?
                OR COALESCE(t.employee_no, ts.employee_no) LIKE ?
                OR COALESCE(t.first_name, ts.first_name) LIKE ?
                OR COALESCE(t.last_name, ts.last_name) LIKE ?
            )
            """
        )

        parameters.extend([pattern] * 5)

    query = _salary_select()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY
            ss.pay_period_start DESC,
            ss.id DESC
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def issue_salary_slip(slip_id, actor_user_id):
    require_permission(actor_user_id, "payroll.manage")
    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                slip = connection.execute(
                    """
                    SELECT status
                    FROM salary_slips
                    WHERE id = ?
                    """,
                    (slip_id,)
                ).fetchone()

                if not slip:
                    raise ValueError("Salary slip was not found.")

                if slip["status"] != "draft":
                    raise ValueError(
                        "Only draft salary slips can be issued."
                    )

                connection.execute(
                    """
                    UPDATE salary_slips
                    SET status = 'issued',
                        issued_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (slip_id,)
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not issue salary slip: {error}")


def mark_salary_slip_paid(
    slip_id,
    payment_date,
    payment_method,
    transaction_reference="",
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "payroll.manage")
    payment_date = str(payment_date or "").strip()

    try:
        parsed_date = date.fromisoformat(payment_date)

        if parsed_date.isoformat() != payment_date:
            raise ValueError

    except ValueError:
        raise ValueError(
            "Payment date must use YYYY-MM-DD format."
        )

    if parsed_date > date.today():
        raise ValueError("Payment date cannot be in the future.")

    payment_method = str(payment_method or "").strip().lower()

    if payment_method not in VALID_PAYMENT_METHODS:
        raise ValueError("Invalid payment method.")

    transaction_reference = str(
        transaction_reference or ""
    ).strip()

    if len(transaction_reference) > 100:
        raise ValueError(
            "Transaction reference cannot exceed 100 characters."
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                slip = connection.execute(
                    """
                    SELECT status
                    FROM salary_slips
                    WHERE id = ?
                    """,
                    (slip_id,)
                ).fetchone()

                if not slip:
                    raise ValueError("Salary slip was not found.")

                if slip["status"] != "issued":
                    raise ValueError(
                        "Only issued salary slips can be marked as paid."
                    )

                connection.execute(
                    """
                    UPDATE salary_slips
                    SET status = 'paid',
                        payment_date = ?,
                        payment_method = ?,
                        transaction_reference = ?,
                        paid_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        payment_date,
                        payment_method,
                        transaction_reference or None,
                        slip_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not mark salary slip as paid: {error}")


def void_salary_slip(slip_id, reason, actor_user_id):
    require_permission(actor_user_id, "payroll.manage")
    reason = str(reason or "").strip()

    if not reason:
        raise ValueError("A reason is required to void a salary slip.")

    if len(reason) > 500:
        raise ValueError("Void reason cannot exceed 500 characters.")

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                slip = connection.execute(
                    """
                    SELECT status
                    FROM salary_slips
                    WHERE id = ?
                    """,
                    (slip_id,)
                ).fetchone()

                if not slip:
                    raise ValueError("Salary slip was not found.")

                if slip["status"] == "voided":
                    raise ValueError("This salary slip is already voided.")

                if slip["status"] == "paid":
                    raise ValueError(
                        "A paid salary slip cannot be voided through "
                        "this operation. Use a payroll reversal process."
                    )

                connection.execute(
                    """
                    UPDATE salary_slips
                    SET status = 'voided',
                        voided_at = CURRENT_TIMESTAMP,
                        void_reason = ?
                    WHERE id = ?
                    """,
                    (reason, slip_id)
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not void salary slip: {error}")
