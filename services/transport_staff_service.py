import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.transport_staff import (
    TransportStaff,
    VALID_TRANSPORT_STAFF_STATUSES,
)


def create_transport_staff(staff_data):
    staff = TransportStaff(**staff_data).validate()
    data = asdict(staff)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO transport_staff (
                        employee_no,
                        first_name,
                        last_name,
                        phone,
                        email,
                        role,
                        license_number,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["employee_no"],
                        data["first_name"],
                        data["last_name"],
                        data["phone"] or None,
                        data["email"] or None,
                        data["role"],
                        data["license_number"] or None,
                        data["status"],
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "employee_no" in str(error):
            raise ValueError(
                "This transport employee number already exists."
            ) from error

        raise ValueError(
            f"Could not register transport staff: {error}"
        ) from error


def get_transport_staff(staff_id):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM transport_staff
            WHERE id = ?
            """,
            (staff_id,),
        ).fetchone()

        return dict(row) if row else None


def get_transport_staff_list(search=""):
    search = search.strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT *
                FROM transport_staff
                WHERE employee_no LIKE ?
                   OR first_name LIKE ?
                   OR last_name LIKE ?
                   OR phone LIKE ?
                   OR role LIKE ?
                ORDER BY last_name, first_name
                """,
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT *
                FROM transport_staff
                ORDER BY last_name, first_name
                """
            ).fetchall()

        return [dict(row) for row in rows]


def search_transport_staff(search):
    return get_transport_staff_list(search)


def update_transport_staff(staff_id, staff_data):
    staff = TransportStaff(**staff_data).validate()
    data = asdict(staff)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE transport_staff
                    SET employee_no = ?,
                        first_name = ?,
                        last_name = ?,
                        phone = ?,
                        email = ?,
                        role = ?,
                        license_number = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["employee_no"],
                        data["first_name"],
                        data["last_name"],
                        data["phone"] or None,
                        data["email"] or None,
                        data["role"],
                        data["license_number"] or None,
                        data["status"],
                        staff_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError(
                        "Transport staff record was not found."
                    )

    except sqlite3.IntegrityError as error:
        if "employee_no" in str(error):
            raise ValueError(
                "This transport employee number already exists."
            ) from error

        raise ValueError(
            f"Could not update transport staff: {error}"
        ) from error


def update_transport_staff_status(staff_id, status):
    if status not in VALID_TRANSPORT_STAFF_STATUSES:
        raise ValueError("Invalid transport staff status.")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE transport_staff
                SET status = ?
                WHERE id = ?
                """,
                (status, staff_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "Transport staff record was not found."
                )
