import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.teacher import Teacher, VALID_TEACHER_STATUSES
from services.permission_service import require_permission


def create_teacher(teacher_data, *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    teacher = Teacher(**teacher_data).validate()
    data = asdict(teacher)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO teachers (
                        employee_no,
                        first_name,
                        last_name,
                        date_of_birth,
                        gender,
                        phone,
                        email,
                        address,
                        qualification,
                        specialization,
                        department,
                        employment_date,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["employee_no"],
                        data["first_name"],
                        data["last_name"],
                        data["date_of_birth"] or None,
                        data["gender"] or None,
                        data["phone"] or None,
                        data["email"] or None,
                        data["address"] or None,
                        data["qualification"] or None,
                        data["specialization"] or None,
                        data["department"] or None,
                        data["employment_date"] or None,
                        data["status"]
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "employee_no" in str(error):
            raise ValueError(
                "This employee number already exists."
            )

        raise ValueError(
            f"Could not create teacher: {error}"
        )


def get_teacher(teacher_id, *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM teachers
            WHERE id = ?
            """,
            (teacher_id,)
        ).fetchone()

        return dict(row) if row else None


def get_teachers(search="", *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    search = search.strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT *
                FROM teachers
                WHERE employee_no LIKE ?
                   OR first_name LIKE ?
                   OR last_name LIKE ?
                   OR department LIKE ?
                ORDER BY last_name, first_name
                """,
                (pattern, pattern, pattern, pattern)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT *
                FROM teachers
                ORDER BY last_name, first_name
                """
            ).fetchall()

        return [dict(row) for row in rows]


def search_teachers(search, *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    return get_teachers(search, actor_user_id=actor_user_id)


def update_teacher(teacher_id, teacher_data, *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    teacher = Teacher(**teacher_data).validate()
    data = asdict(teacher)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE teachers
                    SET employee_no = ?,
                        first_name = ?,
                        last_name = ?,
                        date_of_birth = ?,
                        gender = ?,
                        phone = ?,
                        email = ?,
                        address = ?,
                        qualification = ?,
                        specialization = ?,
                        department = ?,
                        employment_date = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["employee_no"],
                        data["first_name"],
                        data["last_name"],
                        data["date_of_birth"] or None,
                        data["gender"] or None,
                        data["phone"] or None,
                        data["email"] or None,
                        data["address"] or None,
                        data["qualification"] or None,
                        data["specialization"] or None,
                        data["department"] or None,
                        data["employment_date"] or None,
                        data["status"],
                        teacher_id
                    )
                )

                if cursor.rowcount == 0:
                    raise ValueError(
                        "Teacher record was not found."
                    )

    except sqlite3.IntegrityError as error:
        if "employee_no" in str(error):
            raise ValueError(
                "This employee number already exists."
            )

        raise ValueError(
            f"Could not update teacher: {error}"
        )


def update_teacher_status(teacher_id, status, *, actor_user_id):
    require_permission(actor_user_id, "teachers.manage")
    if status not in VALID_TEACHER_STATUSES:
        raise ValueError("Invalid teacher status.")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE teachers
                SET status = ?
                WHERE id = ?
                """,
                (status, teacher_id)
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "Teacher record was not found."
                )
