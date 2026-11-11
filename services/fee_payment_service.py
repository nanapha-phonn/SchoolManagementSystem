import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from services.permission_service import require_permission
from models.fee_payment import FeePayment


def create_fee_payment(payment_data, actor_user_id):
    require_permission(actor_user_id, "fees.manage")
    trusted_data = dict(payment_data)
    trusted_data["received_by"] = actor_user_id
    payment = FeePayment(**trusted_data).validate()
    data = asdict(payment)

    try:
        with closing(get_connection()) as connection:
            with connection:
                # Acquire the write lock before checking the balance.
                connection.execute("BEGIN IMMEDIATE")

                charge = connection.execute(
                    """
                    SELECT id, amount_minor, status
                    FROM fee_charges
                    WHERE id = ?
                    """,
                    (data["charge_id"],)
                ).fetchone()

                if not charge:
                    raise ValueError("Fee charge was not found.")

                if charge["status"] != "open":
                    raise ValueError(
                        "Payment cannot be recorded against a voided charge."
                    )

                amount_paid = connection.execute(
                    """
                    SELECT COALESCE(SUM(amount_minor), 0)
                    FROM fee_payments
                    WHERE charge_id = ?
                      AND status = 'posted'
                    """,
                    (data["charge_id"],)
                ).fetchone()[0]

                balance = charge["amount_minor"] - amount_paid

                if balance <= 0:
                    raise ValueError(
                        "This fee charge has already been fully paid."
                    )

                if data["amount_minor"] > balance:
                    raise ValueError(
                        f"Payment exceeds the outstanding balance "
                        f"of {balance} minor units."
                    )

                cursor = connection.execute(
                    """
                    INSERT INTO fee_payments (
                        receipt_no,
                        charge_id,
                        amount_minor,
                        payment_date,
                        payment_method,
                        transaction_reference,
                        received_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PENDING-{uuid.uuid4().hex}",
                        data["charge_id"],
                        data["amount_minor"],
                        data["payment_date"],
                        data["payment_method"],
                        data["transaction_reference"] or None,
                        data["received_by"],
                    )
                )

                payment_id = cursor.lastrowid
                receipt_no = (
                    f"RCPT-{data['payment_date'][:4]}-{payment_id:06d}"
                )

                connection.execute(
                    """
                    UPDATE fee_payments
                    SET receipt_no = ?
                    WHERE id = ?
                    """,
                    (receipt_no, payment_id)
                )

                return payment_id

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not record fee payment: {error}")


def _payment_select():
    return """
        SELECT
            p.*,
            c.charge_no,
            c.fee_type,
            c.description AS charge_description,
            c.currency,
            c.student_id,
            s.admission_no,
            s.first_name,
            s.last_name
        FROM fee_payments AS p
        JOIN fee_charges AS c
            ON c.id = p.charge_id
        JOIN students AS s
            ON s.id = c.student_id
    """


def get_fee_payment(payment_id, actor_user_id):
    require_permission(actor_user_id, "fees.manage")
    with closing(get_connection()) as connection:
        row = connection.execute(
            _payment_select() + " WHERE p.id = ?",
            (payment_id,)
        ).fetchone()

        return dict(row) if row else None


def get_fee_payments(
    charge_id=None,
    student_id=None,
    status=None,
    search="",
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "fees.manage")
    conditions = []
    parameters = []

    if charge_id is not None:
        try:
            charge_id = int(charge_id)
        except (TypeError, ValueError):
            raise ValueError("Charge ID must be a positive integer.")

        if charge_id <= 0:
            raise ValueError("Charge ID must be a positive integer.")

        conditions.append("p.charge_id = ?")
        parameters.append(charge_id)

    if student_id is not None:
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            raise ValueError("Student ID must be a positive integer.")

        if student_id <= 0:
            raise ValueError("Student ID must be a positive integer.")

        conditions.append("c.student_id = ?")
        parameters.append(student_id)

    if status:
        status = status.strip().lower()

        if status not in {"posted", "voided"}:
            raise ValueError("Invalid payment status.")

        conditions.append("p.status = ?")
        parameters.append(status)

    search = search.strip()

    if search:
        pattern = f"%{search}%"
        conditions.append(
            """
            (
                p.receipt_no LIKE ?
                OR p.transaction_reference LIKE ?
                OR c.charge_no LIKE ?
                OR s.admission_no LIKE ?
                OR s.first_name LIKE ?
                OR s.last_name LIKE ?
            )
            """
        )
        parameters.extend([pattern] * 6)

    query = _payment_select()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.payment_date DESC, p.id DESC"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def void_fee_payment(payment_id, reason, actor_user_id):
    require_permission(actor_user_id, "fees.void")
    reason = str(reason or "").strip()

    if not reason:
        raise ValueError("A reason is required to void a payment.")

    if len(reason) > 500:
        raise ValueError("Void reason cannot exceed 500 characters.")

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                payment = connection.execute(
                    """
                    SELECT id, status
                    FROM fee_payments
                    WHERE id = ?
                    """,
                    (payment_id,)
                ).fetchone()

                if not payment:
                    raise ValueError("Fee payment was not found.")

                if payment["status"] == "voided":
                    raise ValueError("This payment is already voided.")

                connection.execute(
                    """
                    UPDATE fee_payments
                    SET status = 'voided',
                        voided_at = CURRENT_TIMESTAMP,
                        void_reason = ?
                    WHERE id = ?
                    """,
                    (reason, payment_id)
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(f"Could not void fee payment: {error}")
