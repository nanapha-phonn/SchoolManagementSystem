import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.academic_year import AcademicYear
from services.permission_service import require_permission


def _validate_id(academic_year_id):
    if isinstance(academic_year_id, bool):
        raise ValueError("Academic year ID must be a positive integer.")

    try:
        academic_year_id = int(academic_year_id)
    except (TypeError, ValueError):
        raise ValueError(
            "Academic year ID must be a positive integer."
        )

    if academic_year_id <= 0:
        raise ValueError(
            "Academic year ID must be a positive integer."
        )

    return academic_year_id


def create_academic_year(year_data, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    year = AcademicYear(**year_data).validate()
    data = asdict(year)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                # Insert as non-current first. This allows the previous
                # current year to be unset before the new one is activated.
                cursor = connection.execute(
                    """
                    INSERT INTO academic_years (
                        name,
                        start_date,
                        end_date,
                        is_current
                    )
                    VALUES (?, ?, ?, 0)
                    """,
                    (
                        data["name"],
                        data["start_date"],
                        data["end_date"],
                    )
                )

                academic_year_id = cursor.lastrowid

                if data["is_current"]:
                    connection.execute(
                        """
                        UPDATE academic_years
                        SET is_current = 0
                        WHERE is_current = 1
                        """
                    )

                    connection.execute(
                        """
                        UPDATE academic_years
                        SET is_current = 1
                        WHERE id = ?
                        """,
                        (academic_year_id,)
                    )

                return academic_year_id

    except sqlite3.IntegrityError as error:
        if "academic_years.name" in str(error):
            raise ValueError(
                "An academic year with this name already exists."
            )

        raise ValueError(
            f"Could not create academic year: {error}"
        )


def get_academic_year(academic_year_id, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    academic_year_id = _validate_id(academic_year_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM academic_years
            WHERE id = ?
            """,
            (academic_year_id,)
        ).fetchone()

        return dict(row) if row else None


def get_academic_years(search="", *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    search = str(search or "").strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT *
                FROM academic_years
                WHERE name LIKE ?
                   OR start_date LIKE ?
                   OR end_date LIKE ?
                ORDER BY is_current DESC, start_date DESC, id DESC
                """,
                (pattern, pattern, pattern)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT *
                FROM academic_years
                ORDER BY is_current DESC, start_date DESC, id DESC
                """
            ).fetchall()

        return [dict(row) for row in rows]


def update_academic_year(academic_year_id, year_data, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    academic_year_id = _validate_id(academic_year_id)

    year = AcademicYear(**year_data).validate()
    data = asdict(year)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT id
                    FROM academic_years
                    WHERE id = ?
                    """,
                    (academic_year_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Academic year record was not found."
                    )

                if data["is_current"]:
                    connection.execute(
                        """
                        UPDATE academic_years
                        SET is_current = 0
                        WHERE is_current = 1
                        """
                    )

                connection.execute(
                    """
                    UPDATE academic_years
                    SET name = ?,
                        start_date = ?,
                        end_date = ?,
                        is_current = ?
                    WHERE id = ?
                    """,
                    (
                        data["name"],
                        data["start_date"],
                        data["end_date"],
                        int(data["is_current"]),
                        academic_year_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        if "academic_years.name" in str(error):
            raise ValueError(
                "An academic year with this name already exists."
            )

        raise ValueError(
            f"Could not update academic year: {error}"
        )


def set_current_academic_year(academic_year_id, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    academic_year_id = _validate_id(academic_year_id)

    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT id
                FROM academic_years
                WHERE id = ?
                """,
                (academic_year_id,)
            ).fetchone()

            if not existing:
                raise ValueError(
                    "Academic year record was not found."
                )

            connection.execute(
                """
                UPDATE academic_years
                SET is_current = 0
                WHERE is_current = 1
                """
            )

            connection.execute(
                """
                UPDATE academic_years
                SET is_current = 1
                WHERE id = ?
                """,
                (academic_year_id,)
            )
