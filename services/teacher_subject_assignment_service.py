import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.teacher_subject_assignment import (
    TeacherSubjectAssignment,
)
from services.permission_service import require_permission


def _validate_id(value, label):
    if isinstance(value, bool):
        raise ValueError(
            f"{label} must be a positive integer."
        )

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{label} must be a positive integer."
        )

    if value <= 0:
        raise ValueError(
            f"{label} must be a positive integer."
        )

    return value


def _validate_references(connection, assignment):
    teacher = connection.execute(
        """
        SELECT id, status
        FROM teachers
        WHERE id = ?
        """,
        (assignment.teacher_id,)
    ).fetchone()

    if not teacher:
        raise ValueError("Selected teacher was not found.")

    if teacher["status"] != "active":
        raise ValueError("Only active teachers can receive assignments.")

    subject = connection.execute(
        """
        SELECT id, status
        FROM subjects
        WHERE id = ?
        """,
        (assignment.subject_id,)
    ).fetchone()

    if not subject:
        raise ValueError("Selected subject was not found.")

    if subject["status"] != "active":
        raise ValueError("Only active subjects can be assigned.")

    section = connection.execute(
        """
        SELECT id
        FROM sections
        WHERE id = ?
        """,
        (assignment.section_id,)
    ).fetchone()

    if not section:
        raise ValueError("Selected section was not found.")

    academic_year = connection.execute(
        """
        SELECT id
        FROM academic_years
        WHERE id = ?
        """,
        (assignment.academic_year_id,)
    ).fetchone()

    if not academic_year:
        raise ValueError("Selected academic year was not found.")


def _insert_assignment(connection, assignment):
    data = asdict(assignment)

    cursor = connection.execute(
        """
        INSERT INTO teacher_subject_assignments (
            teacher_id,
            subject_id,
            section_id,
            academic_year_id,
            assigned_on,
            ended_on,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["teacher_id"],
            data["subject_id"],
            data["section_id"],
            data["academic_year_id"],
            data["assigned_on"],
            data["ended_on"] or None,
            data["status"],
        )
    )

    return cursor.lastrowid


def create_teacher_subject_assignment(
    assignment_data,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "teachers.manage")
    assignment = TeacherSubjectAssignment(
        **assignment_data
    ).validate()

    if assignment.status != "active":
        raise ValueError(
            "New teacher subject assignments must be active."
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                _validate_references(connection, assignment)

                return _insert_assignment(
                    connection,
                    assignment
                )

    except sqlite3.IntegrityError as error:
        error_text = str(error).lower()

        if (
            "teacher_subject_assignments.subject_id" in error_text
            and "teacher_subject_assignments.section_id" in error_text
            and "teacher_subject_assignments.academic_year_id" in error_text
        ):
            raise ValueError(
                "This subject already has an active teacher "
                "in the selected section and academic year."
            )

        raise ValueError(
            f"Could not create teacher subject assignment: {error}"
        )


def _assignment_query():
    return """
        SELECT
            a.*,
            t.employee_no,
            t.first_name || ' ' || t.last_name AS teacher_name,
            s.subject_code,
            s.name AS subject_name,
            sec.name AS section_name,
            c.name AS class_name,
            ay.name AS academic_year_name
        FROM teacher_subject_assignments AS a
        JOIN teachers AS t
            ON t.id = a.teacher_id
        JOIN subjects AS s
            ON s.id = a.subject_id
        JOIN sections AS sec
            ON sec.id = a.section_id
        JOIN classes AS c
            ON c.id = sec.class_id
        JOIN academic_years AS ay
            ON ay.id = a.academic_year_id
    """


def get_teacher_subject_assignment(
    assignment_id,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "teachers.manage")
    assignment_id = _validate_id(
        assignment_id,
        "Assignment ID"
    )

    with closing(get_connection()) as connection:
        row = connection.execute(
            _assignment_query() + " WHERE a.id = ?",
            (assignment_id,)
        ).fetchone()

        return dict(row) if row else None


def get_teacher_subject_assignments(
    search="",
    teacher_id=None,
    subject_id=None,
    section_id=None,
    academic_year_id=None,
    status=None,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "teachers.manage")
    search = str(search or "").strip()

    filters = (
        ("teacher_id", teacher_id, "a.teacher_id"),
        ("subject_id", subject_id, "a.subject_id"),
        ("section_id", section_id, "a.section_id"),
        (
            "academic_year_id",
            academic_year_id,
            "a.academic_year_id",
        ),
    )

    conditions = []
    parameters = []

    for label, value, column in filters:
        if value is not None:
            value = _validate_id(value, label.replace("_", " ").title())
            conditions.append(f"{column} = ?")
            parameters.append(value)

    if status is not None:
        if status not in ("active", "inactive"):
            raise ValueError("Invalid assignment status filter.")

        conditions.append("a.status = ?")
        parameters.append(status)

    if search:
        pattern = f"%{search}%"

        conditions.append("""
            (
                t.employee_no LIKE ?
                OR t.first_name LIKE ?
                OR t.last_name LIKE ?
                OR s.subject_code LIKE ?
                OR s.name LIKE ?
                OR sec.name LIKE ?
                OR c.name LIKE ?
                OR ay.name LIKE ?
            )
        """)

        parameters.extend([pattern] * 8)

    query = _assignment_query()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY
            ay.start_date DESC,
            c.name COLLATE NOCASE,
            sec.name COLLATE NOCASE,
            s.name COLLATE NOCASE,
            a.id DESC
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def end_teacher_subject_assignment(
    assignment_id,
    ended_on,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "teachers.manage")
    assignment_id = _validate_id(
        assignment_id,
        "Assignment ID"
    )

    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT *
                FROM teacher_subject_assignments
                WHERE id = ?
                """,
                (assignment_id,)
            ).fetchone()

            if not existing:
                raise ValueError(
                    "Teacher subject assignment was not found."
                )

            if existing["status"] != "active":
                raise ValueError(
                    "This assignment has already ended."
                )

            assignment = TeacherSubjectAssignment(
                teacher_id=existing["teacher_id"],
                subject_id=existing["subject_id"],
                section_id=existing["section_id"],
                academic_year_id=existing["academic_year_id"],
                assigned_on=existing["assigned_on"],
                ended_on=ended_on,
                status="inactive",
            ).validate()

            connection.execute(
                """
                UPDATE teacher_subject_assignments
                SET ended_on = ?,
                    status = 'inactive'
                WHERE id = ?
                """,
                (assignment.ended_on, assignment_id)
            )


def reassign_teacher_subject_assignment(
    assignment_id,
    new_teacher_id,
    ended_on,
    assigned_on,
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "teachers.manage")
    assignment_id = _validate_id(
        assignment_id,
        "Assignment ID"
    )
    new_teacher_id = _validate_id(
        new_teacher_id,
        "Teacher ID"
    )

    with closing(get_connection()) as connection:
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT *
                    FROM teacher_subject_assignments
                    WHERE id = ?
                    """,
                    (assignment_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Teacher subject assignment was not found."
                    )

                if existing["status"] != "active":
                    raise ValueError(
                        "Only active assignments can be reassigned."
                    )

                if new_teacher_id == existing["teacher_id"]:
                    raise ValueError(
                        "Select a different teacher for reassignment."
                    )

                ended_assignment = TeacherSubjectAssignment(
                    teacher_id=existing["teacher_id"],
                    subject_id=existing["subject_id"],
                    section_id=existing["section_id"],
                    academic_year_id=existing["academic_year_id"],
                    assigned_on=existing["assigned_on"],
                    ended_on=ended_on,
                    status="inactive",
                ).validate()

                new_assignment = TeacherSubjectAssignment(
                    teacher_id=new_teacher_id,
                    subject_id=existing["subject_id"],
                    section_id=existing["section_id"],
                    academic_year_id=existing["academic_year_id"],
                    assigned_on=assigned_on,
                ).validate()

                if new_assignment.assigned_on <= ended_assignment.ended_on:
                    raise ValueError(
                        "The new assignment date must be after "
                        "the previous assignment end date."
                    )

                _validate_references(
                    connection,
                    new_assignment
                )

                connection.execute(
                    """
                    UPDATE teacher_subject_assignments
                    SET ended_on = ?,
                        status = 'inactive'
                    WHERE id = ?
                    """,
                    (
                        ended_assignment.ended_on,
                        assignment_id,
                    )
                )

                return _insert_assignment(
                    connection,
                    new_assignment
                )

        except sqlite3.IntegrityError as error:
            raise ValueError(
                f"Could not reassign teacher: {error}"
            )
