import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from services.permission_service import require_permission
from models.enrollment import (
    Enrollment,
    VALID_ENROLLMENT_STATUSES,
)


def _validate_id(value, field_name):
    if isinstance(value, bool):
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


def _validate_references(connection, enrollment, require_active_student=True):
    student = connection.execute(
        """
        SELECT id, status
        FROM students
        WHERE id = ?
        """,
        (enrollment.student_id,)
    ).fetchone()

    if not student:
        raise ValueError("Selected student was not found.")

    if require_active_student and student["status"] != "active":
        raise ValueError(
            "Only active students can receive a new enrollment."
        )

    section = connection.execute(
        """
        SELECT id
        FROM sections
        WHERE id = ?
        """,
        (enrollment.section_id,)
    ).fetchone()

    if not section:
        raise ValueError("Selected section was not found.")

    academic_year = connection.execute(
        """
        SELECT id
        FROM academic_years
        WHERE id = ?
        """,
        (enrollment.academic_year_id,)
    ).fetchone()

    if not academic_year:
        raise ValueError("Selected academic year was not found.")


def create_enrollment(enrollment_data, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    enrollment = Enrollment(**enrollment_data).validate()
    data = asdict(enrollment)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                _validate_references(
                    connection,
                    enrollment,
                    require_active_student=True
                )

                cursor = connection.execute(
                    """
                    INSERT INTO enrollments (
                        student_id,
                        section_id,
                        academic_year_id,
                        enrolled_on,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data["student_id"],
                        data["section_id"],
                        data["academic_year_id"],
                        data["enrolled_on"],
                        data["status"],
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        error_text = str(error)

        if (
            "enrollments.student_id, enrollments.academic_year_id"
            in error_text
        ):
            raise ValueError(
                "This student is already enrolled in this academic year."
            )

        raise ValueError(
            f"Could not create enrollment: {error}"
        )


def get_enrollment(enrollment_id, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    enrollment_id = _validate_id(
        enrollment_id,
        "Enrollment ID"
    )

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                e.id,
                e.student_id,
                e.section_id,
                e.academic_year_id,
                e.enrolled_on,
                e.status,
                s.admission_no,
                s.first_name,
                s.last_name,
                s.first_name || ' ' || s.last_name AS student_name,
                s.status AS student_status,
                sec.name AS section_name,
                c.id AS class_id,
                c.name AS class_name,
                ay.name AS academic_year_name,
                ay.start_date AS academic_year_start,
                ay.end_date AS academic_year_end
            FROM enrollments AS e
            JOIN students AS s
                ON s.id = e.student_id
            JOIN sections AS sec
                ON sec.id = e.section_id
            JOIN classes AS c
                ON c.id = sec.class_id
            JOIN academic_years AS ay
                ON ay.id = e.academic_year_id
            WHERE e.id = ?
            """,
            (enrollment_id,)
        ).fetchone()

        return dict(row) if row else None


def get_enrollments(
    search="",
    academic_year_id=None,
    class_id=None,
    section_id=None,
    status=None,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "academics.manage")

    conditions = []
    parameters = []

    filter_ids = (
        ("academic_year_id", academic_year_id),
        ("class_id", class_id),
        ("section_id", section_id),
    )

    for field_name, value in filter_ids:
        if value is not None:
            value = _validate_id(
                value,
                field_name.replace("_", " ").title()
            )

            conditions.append(f"e.{field_name} = ?" if field_name != "class_id"
                              else "sec.class_id = ?")
            parameters.append(value)

    if status:
        status = str(status).strip().lower()

        if status not in VALID_ENROLLMENT_STATUSES:
            raise ValueError("Invalid enrollment status.")

        conditions.append("e.status = ?")
        parameters.append(status)

    search = str(search or "").strip()

    if search:
        pattern = f"%{search}%"

        conditions.append(
            """
            (
                s.admission_no LIKE ?
                OR s.first_name LIKE ?
                OR s.last_name LIKE ?
                OR ay.name LIKE ?
                OR c.name LIKE ?
                OR sec.name LIKE ?
            )
            """
        )

        parameters.extend([pattern] * 6)

    query = """
        SELECT
            e.id,
            e.student_id,
            e.section_id,
            e.academic_year_id,
            e.enrolled_on,
            e.status,
            s.admission_no,
            s.first_name,
            s.last_name,
            s.first_name || ' ' || s.last_name AS student_name,
            s.status AS student_status,
            sec.name AS section_name,
            c.id AS class_id,
            c.name AS class_name,
            ay.name AS academic_year_name,
            ay.start_date AS academic_year_start,
            ay.end_date AS academic_year_end
        FROM enrollments AS e
        JOIN students AS s
            ON s.id = e.student_id
        JOIN sections AS sec
            ON sec.id = e.section_id
        JOIN classes AS c
            ON c.id = sec.class_id
        JOIN academic_years AS ay
            ON ay.id = e.academic_year_id
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY ay.start_date DESC,
                 c.name COLLATE NOCASE,
                 sec.name COLLATE NOCASE,
                 s.last_name COLLATE NOCASE,
                 s.first_name COLLATE NOCASE,
                 e.id DESC
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def update_enrollment(enrollment_id, enrollment_data, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    enrollment_id = _validate_id(
        enrollment_id,
        "Enrollment ID"
    )

    allowed_fields = {
        "section_id",
        "enrolled_on",
        "status",
    }

    if set(enrollment_data) != allowed_fields:
        raise ValueError(
            "Only section, enrollment date, and status "
            "can be updated. Student and academic year "
            "cannot be changed."
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT
                        student_id,
                        academic_year_id
                    FROM enrollments
                    WHERE id = ?
                    """,
                    (enrollment_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Enrollment record was not found."
                    )

                enrollment = Enrollment(
                    student_id=existing["student_id"],
                    academic_year_id=existing["academic_year_id"],
                    section_id=enrollment_data["section_id"],
                    enrolled_on=enrollment_data["enrolled_on"],
                    status=enrollment_data["status"],
                ).validate()

                _validate_references(
                    connection,
                    enrollment,
                    require_active_student=False
                )

                connection.execute(
                    """
                    UPDATE enrollments
                    SET section_id = ?,
                        enrolled_on = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        enrollment.section_id,
                        enrollment.enrolled_on,
                        enrollment.status,
                        enrollment_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        raise ValueError(
            f"Could not update enrollment: {error}"
        )
