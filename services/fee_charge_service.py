import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict
from datetime import date

from database.database import get_connection
from models.fee_charge import FeeCharge, VALID_FEE_TYPES
from services.permission_service import require_permission


def _validate_references(connection, charge):
    student = connection.execute(
        "SELECT id FROM students WHERE id = ?",
        (charge.student_id,)
    ).fetchone()

    if not student:
        raise ValueError("Selected student was not found.")

    if charge.enrollment_id is not None:
        enrollment = connection.execute(
            """
            SELECT student_id
            FROM enrollments
            WHERE id = ?
            """,
            (charge.enrollment_id,)
        ).fetchone()

        if not enrollment:
            raise ValueError("Selected enrollment was not found.")

        if enrollment["student_id"] != charge.student_id:
            raise ValueError(
                "The selected enrollment does not belong to this student."
            )

    if charge.transport_assignment_id is not None:
        assignment = connection.execute(
            """
            SELECT student_id
            FROM student_transport_assignments
            WHERE id = ?
            """,
            (charge.transport_assignment_id,)
        ).fetchone()

        if not assignment:
            raise ValueError(
                "Selected transport assignment was not found."
            )

        if assignment["student_id"] != charge.student_id:
            raise ValueError(
                "The transport assignment does not belong to this student."
            )


def create_fee_charge(charge_data, actor_user_id):
    require_permission(actor_user_id, "fees.manage")

    trusted_data = dict(charge_data)
    trusted_data["created_by"] = actor_user_id

    charge = FeeCharge(**trusted_data).validate()
    data = asdict(charge)

    try:
        with closing(get_connection()) as connection:
            with connection:
                _validate_references(connection, charge)

                cursor = connection.execute(
                    """
                    INSERT INTO fee_charges (
                        school_id,
                        charge_no,
                        student_id,
                        fee_type,
                        enrollment_id,
                        transport_assignment_id,
                        description,
                        amount_minor,
                        currency,
                        due_date,
                        created_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["school_id"],
                        f"PENDING-{uuid.uuid4().hex}",
                        data["student_id"],
                        data["fee_type"],
                        data["enrollment_id"],
                        data["transport_assignment_id"],
                        data["description"],
                        data["amount_minor"],
                        data["currency"],
                        data["due_date"] or None,
                        data["created_by"],
                    )
                )

                charge_id = cursor.lastrowid
                charge_no = f"CHG-{date.today().year}-{charge_id:06d}"

                connection.execute(
                    """
                    UPDATE fee_charges
                    SET charge_no = ?
                    WHERE id = ?
                    """,
                    (charge_no, charge_id)
                )

                return charge_id

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not create fee charge: {error}")


def _charge_select():
    return """
        SELECT
            c.*,
            s.admission_no,
            s.first_name,
            s.last_name,
            COALESCE(p.total_paid_minor, 0) AS amount_paid_minor,
            c.amount_minor - COALESCE(p.total_paid_minor, 0)
                AS balance_minor,
            CASE
                WHEN c.status = 'voided' THEN 'voided'
                WHEN c.amount_minor <= COALESCE(p.total_paid_minor, 0)
                    THEN 'paid'
                WHEN c.due_date IS NOT NULL
                     AND c.due_date < date('now')
                    THEN 'overdue'
                WHEN COALESCE(p.total_paid_minor, 0) > 0
                    THEN 'partial'
                ELSE 'unpaid'
            END AS payment_status
        FROM fee_charges AS c
        JOIN students AS s
            ON s.id = c.student_id
        LEFT JOIN (
            SELECT
                charge_id,
                SUM(amount_minor) AS total_paid_minor
            FROM fee_payments
            WHERE status = 'posted'
            GROUP BY charge_id
        ) AS p
            ON p.charge_id = c.id
    """


def get_fee_charge(charge_id, actor_user_id):
    require_permission(actor_user_id, "fees.manage")

    with closing(get_connection()) as connection:
        row = connection.execute(
            _charge_select() + " WHERE c.id = ?",
            (charge_id,)
        ).fetchone()

        return dict(row) if row else None


def get_fee_charges(
    student_id=None,
    fee_type=None,
    status=None,
    search="",
    *,
    actor_user_id
):
    require_permission(actor_user_id, "fees.manage")

    conditions = []
    parameters = []

    if student_id is not None:
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            raise ValueError("Student ID must be a positive integer.")

        if student_id <= 0:
            raise ValueError("Student ID must be a positive integer.")

        conditions.append("c.student_id = ?")
        parameters.append(student_id)

    if fee_type:
        fee_type = fee_type.strip().lower()

        if fee_type not in VALID_FEE_TYPES:
            raise ValueError("Invalid fee type.")

        conditions.append("c.fee_type = ?")
        parameters.append(fee_type)

    if status:
        status = status.strip().lower()

        if status not in {"open", "voided"}:
            raise ValueError("Invalid charge status.")

        conditions.append("c.status = ?")
        parameters.append(status)

    search = search.strip()

    if search:
        pattern = f"%{search}%"
        conditions.append(
            """
            (
                c.charge_no LIKE ?
                OR c.description LIKE ?
                OR s.admission_no LIKE ?
                OR s.first_name LIKE ?
                OR s.last_name LIKE ?
            )
            """
        )
        parameters.extend([pattern] * 5)

    query = _charge_select()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY c.created_at DESC, c.id DESC"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def void_fee_charge(charge_id, reason, actor_user_id):
    require_permission(actor_user_id, "fees.void")

    reason = str(reason or "").strip()

    if not reason:
        raise ValueError("A reason is required to void a fee charge.")

    if len(reason) > 500:
        raise ValueError("Void reason cannot exceed 500 characters.")

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                charge = connection.execute(
                    """
                    SELECT status
                    FROM fee_charges
                    WHERE id = ?
                    """,
                    (charge_id,)
                ).fetchone()

                if not charge:
                    raise ValueError("Fee charge was not found.")

                if charge["status"] == "voided":
                    raise ValueError("This fee charge is already voided.")

                posted_payments = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM fee_payments
                    WHERE charge_id = ?
                      AND status = 'posted'
                    """,
                    (charge_id,)
                ).fetchone()[0]

                if posted_payments:
                    raise ValueError(
                        "Cannot void a charge with posted payments. "
                        "Void its payments first."
                    )

                connection.execute(
                    """
                    UPDATE fee_charges
                    SET status = 'voided',
                        voided_at = CURRENT_TIMESTAMP,
                        void_reason = ?
                    WHERE id = ?
                    """,
                    (reason, charge_id)
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not void fee charge: {error}")
