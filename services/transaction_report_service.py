from contextlib import closing
from datetime import date

from database.database import get_connection
from models.fee_charge import VALID_FEE_TYPES
from services.permission_service import require_permission


def _parse_date(value, field_name):
    if value is None or value == "":
        return None

    value = str(value).strip()

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        )

    if parsed.isoformat() != value:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        )

    return value


def _validate_date_range(start_date=None, end_date=None):
    start_date = _parse_date(start_date, "Start date")
    end_date = _parse_date(end_date, "End date")

    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    return start_date, end_date


def _validate_currency(currency):
    if currency is None:
        return None

    currency = str(currency).strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        raise ValueError(
            "Currency must be a three-letter currency code."
        )

    return currency


# ============================================================
# 1. OUTSTANDING FEE REPORT
# ============================================================

def get_outstanding_fee_report(
    as_of_date=None,
    fee_type=None,
    currency=None,
    payment_status=None,
    student_id=None,
    *,
    actor_user_id,
):
    """
    Return open fee charges with an outstanding balance.

    payment_status can be:
        unpaid, partial, overdue

    An overdue charge can also be partially paid.
    """

    require_permission(actor_user_id, "fees.reports.view")

    as_of_date = _parse_date(
        as_of_date or date.today().isoformat(),
        "As-of date",
    )

    if fee_type:
        fee_type = str(fee_type).strip().lower()

        if fee_type not in VALID_FEE_TYPES:
            raise ValueError("Invalid fee type.")

    currency = _validate_currency(currency)

    if payment_status:
        payment_status = str(payment_status).strip().lower()

        if payment_status not in {
            "unpaid",
            "partial",
            "overdue",
        }:
            raise ValueError("Invalid outstanding payment status.")

    if student_id is not None:
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            raise ValueError("Student ID must be a positive integer.")

        if student_id <= 0:
            raise ValueError("Student ID must be a positive integer.")

    query = """
        SELECT
            c.id,
            c.charge_no,
            c.student_id,
            s.admission_no,
            s.first_name,
            s.last_name,
            c.fee_type,
            c.description,
            c.amount_minor,
            c.currency,
            c.due_date,
            COALESCE(p.amount_paid_minor, 0) AS amount_paid_minor,
            c.amount_minor - COALESCE(p.amount_paid_minor, 0)
                AS balance_minor,
            CASE
                WHEN c.due_date IS NOT NULL
                     AND c.due_date < ?
                    THEN 'overdue'
                WHEN COALESCE(p.amount_paid_minor, 0) > 0
                    THEN 'partial'
                ELSE 'unpaid'
            END AS payment_status
        FROM fee_charges AS c
        JOIN students AS s
            ON s.id = c.student_id
        LEFT JOIN (
            SELECT
                charge_id,
                SUM(amount_minor) AS amount_paid_minor
            FROM fee_payments
            WHERE status = 'posted'
            GROUP BY charge_id
        ) AS p
            ON p.charge_id = c.id
        WHERE c.status = 'open'
          AND c.amount_minor > COALESCE(p.amount_paid_minor, 0)
    """

    parameters = [as_of_date]

    if fee_type:
        query += " AND c.fee_type = ?"
        parameters.append(fee_type)

    if currency:
        query += " AND c.currency = ?"
        parameters.append(currency)

    if student_id is not None:
        query += " AND c.student_id = ?"
        parameters.append(student_id)

    if payment_status == "overdue":
        query += " AND c.due_date IS NOT NULL AND c.due_date < ?"
        parameters.append(as_of_date)

    elif payment_status == "partial":
        query += """
            AND COALESCE(p.amount_paid_minor, 0) > 0
            AND (c.due_date IS NULL OR c.due_date >= ?)
        """
        parameters.append(as_of_date)

    elif payment_status == "unpaid":
        query += """
            AND COALESCE(p.amount_paid_minor, 0) = 0
            AND (c.due_date IS NULL OR c.due_date >= ?)
        """
        parameters.append(as_of_date)

    query += " ORDER BY c.due_date, s.last_name, s.first_name"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]


def get_outstanding_fee_summary(
    as_of_date=None,
    fee_type=None,
    *,
    actor_user_id,
):
    """Group outstanding amounts by currency and fee type."""
    require_permission(actor_user_id, "fees.reports.view")

    charges = get_outstanding_fee_report(
        as_of_date=as_of_date,
        fee_type=fee_type,
        actor_user_id=actor_user_id,
    )

    summary = {}

    for charge in charges:
        key = (charge["currency"], charge["fee_type"])

        if key not in summary:
            summary[key] = {
                "currency": charge["currency"],
                "fee_type": charge["fee_type"],
                "charge_count": 0,
                "total_amount_minor": 0,
                "total_paid_minor": 0,
                "total_outstanding_minor": 0,
            }

        item = summary[key]
        item["charge_count"] += 1
        item["total_amount_minor"] += charge["amount_minor"]
        item["total_paid_minor"] += charge["amount_paid_minor"]
        item["total_outstanding_minor"] += charge["balance_minor"]

    return sorted(
        summary.values(),
        key=lambda item: (item["currency"], item["fee_type"]),
    )


# ============================================================
# 2. STUDENT ACCOUNT STATEMENT
# ============================================================

def get_student_account_statement(
    student_id,
    start_date=None,
    end_date=None,
    currency=None,
    *,
    actor_user_id,
):
    """
    Build a student account ledger.

    Debits:
        Fee charges
        Voided payment reversals

    Credits:
        Posted fee payments
        Voided fee charges

    Running balances are calculated separately for each currency.
    The opening balance includes all events before start_date.
    """

    require_permission(actor_user_id, "student_accounts.view")

    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        raise ValueError("Student ID must be a positive integer.")

    if student_id <= 0:
        raise ValueError("Student ID must be a positive integer.")

    start_date, end_date = _validate_date_range(
        start_date,
        end_date,
    )

    currency = _validate_currency(currency)

    with closing(get_connection()) as connection:
        student = connection.execute(
            """
            SELECT id, admission_no, first_name, last_name, status
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()

        if not student:
            raise ValueError("Student record was not found.")

        query = """
            SELECT *
            FROM (
                -- Fee charge: debit.
                SELECT
                    date(c.created_at) AS event_date,
                    c.created_at AS sort_timestamp,
                    10 AS event_order,
                    'charge' AS entry_type,
                    c.charge_no AS reference_no,
                    c.description AS description,
                    c.currency AS currency,
                    c.amount_minor AS debit_minor,
                    0 AS credit_minor,
                    c.id AS source_id
                FROM fee_charges AS c
                WHERE c.student_id = ?

                UNION ALL

                -- Original payment: credit.
                -- Keep this event even when the receipt is later voided.
                -- The separate reversal event records the void.
                SELECT
                    p.payment_date AS event_date,
                    p.payment_date || ' 00:00:00' AS sort_timestamp,
                    20 AS event_order,
                    'payment' AS entry_type,
                    p.receipt_no AS reference_no,
                    'Fee payment - ' || c.description AS description,
                    c.currency AS currency,
                    0 AS debit_minor,
                    p.amount_minor AS credit_minor,
                    p.id AS source_id
                FROM fee_payments AS p
                JOIN fee_charges AS c
                    ON c.id = p.charge_id
                WHERE c.student_id = ?

                UNION ALL

                -- Voided payment: debit reversal.
                SELECT
                    date(p.voided_at, 'localtime') AS event_date,
                    p.voided_at AS sort_timestamp,
                    30 AS event_order,
                    'payment_void' AS entry_type,
                    p.receipt_no AS reference_no,
                    'Payment reversal: ' || c.description
                        AS description,
                    c.currency AS currency,
                    p.amount_minor AS debit_minor,
                    0 AS credit_minor,
                    p.id AS source_id
                FROM fee_payments AS p
                JOIN fee_charges AS c
                    ON c.id = p.charge_id
                WHERE c.student_id = ?
                  AND p.status = 'voided'

                UNION ALL

                -- Voided charge: credit reversal.
                SELECT
                    date(c.voided_at, 'localtime') AS event_date,
                    c.voided_at AS sort_timestamp,
                    40 AS event_order,
                    'charge_void' AS entry_type,
                    c.charge_no AS reference_no,
                    'Charge void: ' || c.description
                        AS description,
                    c.currency AS currency,
                    0 AS debit_minor,
                    c.amount_minor AS credit_minor,
                    c.id AS source_id
                FROM fee_charges AS c
                WHERE c.student_id = ?
                  AND c.status = 'voided'
            )
            WHERE (? IS NULL OR event_date <= ?)
              AND (? IS NULL OR currency = ?)
            ORDER BY event_date, event_order, sort_timestamp, source_id
        """

        rows = connection.execute(
            query,
            (
                student_id,
                student_id,
                student_id,
                student_id,
                end_date,
                end_date,
                currency,
                currency,
            ),
        ).fetchall()

    opening_balances = {}
    closing_balances = {}
    entries = []

    for row in rows:
        item = dict(row)
        event_date = item["event_date"]
        item_currency = item["currency"]

        balance = closing_balances.get(item_currency, 0)

        if start_date and event_date < start_date:
            balance += item["debit_minor"] - item["credit_minor"]

            opening_balances[item_currency] = (
                opening_balances.get(item_currency, 0)
                + item["debit_minor"]
                - item["credit_minor"]
            )

            closing_balances[item_currency] = balance
            continue

        balance += item["debit_minor"] - item["credit_minor"]

        item["balance_minor"] = balance

        entries.append(item)
        closing_balances[item_currency] = balance

    return {
        "student": dict(student),
        "start_date": start_date,
        "end_date": end_date,
        "currency": currency,
        "opening_balances": opening_balances,
        "entries": entries,
        "closing_balances": closing_balances,
    }


# ============================================================
# 3. FEE COLLECTION SUMMARY
# ============================================================

def get_fee_collection_summary(
    start_date=None,
    end_date=None,
    fee_type=None,
    *,
    actor_user_id,
):
    """
    Summarize posted collections and voided-payment reversals.

    Net collection = posted amount - voided amount.
    Results are grouped by fee type and currency.
    """

    require_permission(actor_user_id, "fees.reports.view")

    start_date, end_date = _validate_date_range(
        start_date,
        end_date,
    )

    if fee_type:
        fee_type = str(fee_type).strip().lower()

        if fee_type not in VALID_FEE_TYPES:
            raise ValueError("Invalid fee type.")

    query = """
        SELECT
            fee_type,
            currency,
            SUM(posted_amount_minor) AS posted_amount_minor,
            SUM(voided_amount_minor) AS voided_amount_minor,
            SUM(posted_amount_minor) - SUM(voided_amount_minor)
                AS net_collected_minor,
            SUM(posted_count) AS posted_count,
            SUM(voided_count) AS voided_count
        FROM (
            SELECT
                c.fee_type AS fee_type,
                c.currency AS currency,
                p.amount_minor AS posted_amount_minor,
                0 AS voided_amount_minor,
                1 AS posted_count,
                0 AS voided_count
            FROM fee_payments AS p
            JOIN fee_charges AS c
                ON c.id = p.charge_id
            WHERE (? IS NULL OR p.payment_date >= ?)
              AND (? IS NULL OR p.payment_date <= ?)

            UNION ALL

            SELECT
                c.fee_type AS fee_type,
                c.currency AS currency,
                0 AS posted_amount_minor,
                p.amount_minor AS voided_amount_minor,
                0 AS posted_count,
                1 AS voided_count
            FROM fee_payments AS p
            JOIN fee_charges AS c
                ON c.id = p.charge_id
            WHERE p.status = 'voided'
              AND (? IS NULL OR date(p.voided_at, 'localtime') >= ?)
              AND (? IS NULL OR date(p.voided_at, 'localtime') <= ?)
        ) AS transactions
        WHERE (? IS NULL OR fee_type = ?)
        GROUP BY fee_type, currency
        ORDER BY currency, fee_type
    """

    parameters = (
        start_date, start_date,
        end_date, end_date,
        start_date, start_date,
        end_date, end_date,
        fee_type, fee_type,
    )

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]


# ============================================================
# 4. PAYROLL SUMMARY
# ============================================================

def get_payroll_summary(
    start_date=None,
    end_date=None,
    status=None,
    employee_type=None,
    currency=None,
    *,
    actor_user_id,
):
    """
    Summarize salary slips by status, employee type, and currency.

    The date filters select payroll periods that overlap the
    requested date range.
    """

    require_permission(actor_user_id, "payroll.reports.view")

    start_date, end_date = _validate_date_range(
        start_date,
        end_date,
    )

    if status:
        status = str(status).strip().lower()

        if status not in {"draft", "issued", "paid", "voided"}:
            raise ValueError("Invalid salary slip status.")

    if employee_type:
        employee_type = str(employee_type).strip().lower()

        if employee_type not in {"teacher", "transport_staff"}:
            raise ValueError("Invalid employee type.")

    currency = _validate_currency(currency)

    query = """
        SELECT
            ss.status,
            CASE
                WHEN ss.teacher_id IS NOT NULL THEN 'teacher'
                ELSE 'transport_staff'
            END AS employee_type,
            ss.currency,
            COUNT(*) AS slip_count,
            SUM(ss.base_salary_minor) AS base_salary_minor,
            SUM(ss.allowances_minor) AS allowances_minor,
            SUM(ss.deductions_minor) AS deductions_minor,
            SUM(ss.net_salary_minor) AS net_salary_minor
        FROM salary_slips AS ss
        WHERE (? IS NULL OR ss.pay_period_end >= ?)
          AND (? IS NULL OR ss.pay_period_start <= ?)
          AND (? IS NULL OR ss.status = ?)
          AND (
                ? IS NULL
                OR (
                    ? = 'teacher'
                    AND ss.teacher_id IS NOT NULL
                )
                OR (
                    ? = 'transport_staff'
                    AND ss.transport_staff_id IS NOT NULL
                )
          )
          AND (? IS NULL OR ss.currency = ?)
        GROUP BY
            ss.status,
            employee_type,
            ss.currency
        ORDER BY
            ss.currency,
            employee_type,
            ss.status
    """

    parameters = (
        start_date, start_date,
        end_date, end_date,
        status, status,
        employee_type, employee_type, employee_type,
        currency, currency,
    )

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]
