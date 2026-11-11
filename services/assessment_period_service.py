import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.assessment_period import AssessmentPeriod
from services.permission_service import require_permission


def _validate_id(value, field_name="Assessment period ID"):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    return value


def _translate_integrity_error(error):
    message = str(error)

    known_errors = {
        "Assessment dates must fall within the academic year.":
            "Assessment dates must fall within the academic year.",

        "Assessment periods cannot overlap within an academic year.":
            "Assessment periods cannot overlap within the academic year.",

        "Assessment period history cannot be deleted.":
            "Assessment period history cannot be deleted.",

        "Completed assessment periods cannot be changed.":
            "Completed assessment periods cannot be changed.",

        "An assessment period cannot be moved to another academic year.":
            "An assessment period cannot be moved to another academic year.",

        "New assessment periods must start as planned.":
            "New assessment periods must start as planned.",

        "Invalid assessment-period status transition.":
            "Invalid assessment-period status transition.",

        "Academic-year dates cannot invalidate existing assessment periods.":
            "Academic-year dates cannot invalidate existing assessment periods.",
    }

    for database_message, user_message in known_errors.items():
        if database_message in message:
            return ValueError(user_message)

    if (
        "UNIQUE constraint failed: assessment_periods.academic_year_id, "
        "assessment_periods.name"
    ) in message:
        return ValueError(
            "An assessment period with this name already exists "
            "in the selected academic year."
        )

    if "FOREIGN KEY constraint failed" in message:
        return ValueError("Academic year was not found.")

    return ValueError(
        f"Could not save assessment period: {message}"
    )


def create_assessment_period(period_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    period = AssessmentPeriod(**period_data).validate()
    data = asdict(period)

    if data["status"] != "planned":
        raise ValueError(
            "New assessment periods must start as planned."
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                academic_year = connection.execute(
                    """
                    SELECT id
                    FROM academic_years
                    WHERE id = ?
                    """,
                    (data["academic_year_id"],)
                ).fetchone()

                if not academic_year:
                    raise ValueError("Academic year was not found.")

                cursor = connection.execute(
                    """
                    INSERT INTO assessment_periods (
                        academic_year_id,
                        name,
                        period_type,
                        start_date,
                        end_date,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, 'planned')
                    """,
                    (
                        data["academic_year_id"],
                        data["name"],
                        data["period_type"],
                        data["start_date"],
                        data["end_date"],
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def get_assessment_period(assessment_period_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    assessment_period_id = _validate_id(assessment_period_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                ap.*,
                ay.name AS academic_year_name
            FROM assessment_periods AS ap
            JOIN academic_years AS ay
                ON ay.id = ap.academic_year_id
            WHERE ap.id = ?
            """,
            (assessment_period_id,)
        ).fetchone()

        return dict(row) if row else None


def get_assessment_periods(
    academic_year_id=None,
    status=None,
    search="",
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "academics.manage")
    conditions = []
    parameters = []

    if academic_year_id is not None:
        academic_year_id = _validate_id(
            academic_year_id,
            "Academic year ID"
        )
        conditions.append("ap.academic_year_id = ?")
        parameters.append(academic_year_id)

    if status is not None:
        status = str(status).strip().lower()

        if status not in {"planned", "active", "completed"}:
            raise ValueError("Invalid assessment period status.")

        conditions.append("ap.status = ?")
        parameters.append(status)

    search = str(search or "").strip()

    if search:
        pattern = f"%{search}%"
        conditions.append("""
            (
                ap.name LIKE ?
                OR ap.period_type LIKE ?
                OR ay.name LIKE ?
                OR ap.start_date LIKE ?
                OR ap.end_date LIKE ?
            )
        """)
        parameters.extend([pattern] * 5)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with closing(get_connection()) as connection:
        rows = connection.execute(
            f"""
            SELECT
                ap.*,
                ay.name AS academic_year_name
            FROM assessment_periods AS ap
            JOIN academic_years AS ay
                ON ay.id = ap.academic_year_id
            {where_clause}
            ORDER BY
                ap.start_date DESC,
                ap.end_date DESC,
                ap.id DESC
            """,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def update_assessment_period(
    assessment_period_id, period_data, *, actor_user_id
):
    require_permission(actor_user_id, "academics.configure")
    assessment_period_id = _validate_id(assessment_period_id)

    period = AssessmentPeriod(**period_data).validate()
    data = asdict(period)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT id, academic_year_id, status
                    FROM assessment_periods
                    WHERE id = ?
                    """,
                    (assessment_period_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Assessment period record was not found."
                    )

                if existing["status"] == "completed":
                    raise ValueError(
                        "Completed assessment periods cannot be changed."
                    )

                if data["academic_year_id"] != existing["academic_year_id"]:
                    raise ValueError(
                        "An assessment period cannot be moved "
                        "to another academic year."
                    )

                connection.execute(
                    """
                    UPDATE assessment_periods
                    SET name = ?,
                        period_type = ?,
                        start_date = ?,
                        end_date = ?
                    WHERE id = ?
                    """,
                    (
                        data["name"],
                        data["period_type"],
                        data["start_date"],
                        data["end_date"],
                        assessment_period_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def update_assessment_period_status(
    assessment_period_id,
    new_status,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "academics.configure")
    assessment_period_id = _validate_id(assessment_period_id)

    new_status = str(new_status or "").strip().lower()

    if new_status not in {"planned", "active", "completed"}:
        raise ValueError("Invalid assessment period status.")

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT id, status
                    FROM assessment_periods
                    WHERE id = ?
                    """,
                    (assessment_period_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Assessment period record was not found."
                    )

                current_status = existing["status"]

                if new_status == current_status:
                    return

                allowed_transitions = {
                    "planned": "active",
                    "active": "completed",
                }

                if allowed_transitions.get(current_status) != new_status:
                    raise ValueError(
                        f"Invalid status transition: "
                        f"{current_status} to {new_status}."
                    )

                connection.execute(
                    """
                    UPDATE assessment_periods
                    SET status = ?
                    WHERE id = ?
                    """,
                    (new_status, assessment_period_id)
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)
