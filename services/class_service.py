import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from services.permission_service import require_permission
from models.school_class import SchoolClass


def _validate_class_id(class_id):
    if isinstance(class_id, bool):
        raise ValueError("Class ID must be a positive integer.")

    try:
        class_id = int(class_id)
    except (TypeError, ValueError):
        raise ValueError("Class ID must be a positive integer.")

    if class_id <= 0:
        raise ValueError("Class ID must be a positive integer.")

    return class_id


def create_class(class_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    school_class = SchoolClass(**class_data).validate()
    data = asdict(school_class)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO classes (
                        name,
                        description
                    )
                    VALUES (?, ?)
                    """,
                    (
                        data["name"],
                        data["description"] or None,
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "classes.name" in str(error):
            raise ValueError(
                "A class with this name already exists."
            )

        raise ValueError(
            f"Could not create class: {error}"
        )


def get_class(class_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    class_id = _validate_class_id(class_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM classes
            WHERE id = ?
            """,
            (class_id,)
        ).fetchone()

        return dict(row) if row else None


def get_classes(search="", *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    search = str(search or "").strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT *
                FROM classes
                WHERE name LIKE ?
                   OR description LIKE ?
                ORDER BY name COLLATE NOCASE, id
                """,
                (pattern, pattern)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT *
                FROM classes
                ORDER BY name COLLATE NOCASE, id
                """
            ).fetchall()

        return [dict(row) for row in rows]


def update_class(class_id, class_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    class_id = _validate_class_id(class_id)

    school_class = SchoolClass(**class_data).validate()
    data = asdict(school_class)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE classes
                    SET name = ?,
                        description = ?
                    WHERE id = ?
                    """,
                    (
                        data["name"],
                        data["description"] or None,
                        class_id,
                    )
                )

                if cursor.rowcount == 0:
                    raise ValueError(
                        "Class record was not found."
                    )

    except sqlite3.IntegrityError as error:
        if "classes.name" in str(error):
            raise ValueError(
                "A class with this name already exists."
            )

        raise ValueError(
            f"Could not update class: {error}"
        )
