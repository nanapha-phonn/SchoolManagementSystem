import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.student import Student, VALID_STATUSES
from services.permission_service import require_permission


def create_student(student_data, actor_user_id):
    require_permission(actor_user_id, "students.manage")
    student = Student(**student_data).validate()
    data = asdict(student)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name,
                        date_of_birth,
                        gender,
                        phone,
                        email,
                        address,
                        guardian_name,
                        guardian_phone,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["admission_no"],
                        data["first_name"],
                        data["last_name"],
                        data["date_of_birth"] or None,
                        data["gender"] or None,
                        data["phone"] or None,
                        data["email"] or None,
                        data["address"] or None,
                        data["guardian_name"] or None,
                        data["guardian_phone"] or None,
                        data["status"]
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "admission_no" in str(error):
            raise ValueError("This admission number already exists.")
        raise ValueError(f"Could not create student: {error}")


def get_student(student_id, actor_user_id):
    require_permission(actor_user_id, "students.manage")
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        return dict(row) if row else None


def get_students(search="", *, actor_user_id):
    require_permission(actor_user_id, "students.manage")
    search = search.strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT *
                FROM students
                WHERE admission_no LIKE ?
                   OR first_name LIKE ?
                   OR last_name LIKE ?
                ORDER BY last_name, first_name
                """,
                (pattern, pattern, pattern)
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM students
                ORDER BY last_name, first_name
                """
            ).fetchall()

        return [dict(row) for row in rows]


def update_student(student_id, student_data, actor_user_id):
    require_permission(actor_user_id, "students.manage")
    student = Student(**student_data).validate()
    data = asdict(student)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE students
                    SET admission_no = ?,
                        first_name = ?,
                        last_name = ?,
                        date_of_birth = ?,
                        gender = ?,
                        phone = ?,
                        email = ?,
                        address = ?,
                        guardian_name = ?,
                        guardian_phone = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["admission_no"],
                        data["first_name"],
                        data["last_name"],
                        data["date_of_birth"] or None,
                        data["gender"] or None,
                        data["phone"] or None,
                        data["email"] or None,
                        data["address"] or None,
                        data["guardian_name"] or None,
                        data["guardian_phone"] or None,
                        data["status"],
                        student_id
                    )
                )

                if cursor.rowcount == 0:
                    raise ValueError("Student record was not found.")

    except sqlite3.IntegrityError as error:
        if "admission_no" in str(error):
            raise ValueError("This admission number already exists.")
        raise ValueError(f"Could not update student: {error}")


def update_student_status(student_id, status, actor_user_id):
    require_permission(actor_user_id, "students.manage")
    if status not in VALID_STATUSES:
        raise ValueError("Invalid student status.")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE students
                SET status = ?
                WHERE id = ?
                """,
                (status, student_id)
            )

            if cursor.rowcount == 0:
                raise ValueError("Student record was not found.")
