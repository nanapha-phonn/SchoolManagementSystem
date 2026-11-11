import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from services.permission_service import require_permission
from models.section import Section


def _validate_section_id(section_id):
    if isinstance(section_id, bool):
        raise ValueError(
            "Section ID must be a positive integer."
        )

    try:
        section_id = int(section_id)
    except (TypeError, ValueError):
        raise ValueError(
            "Section ID must be a positive integer."
        )

    if section_id <= 0:
        raise ValueError(
            "Section ID must be a positive integer."
        )

    return section_id


def _validate_class_reference(connection, class_id):
    row = connection.execute(
        "SELECT id FROM classes WHERE id = ?",
        (class_id,)
    ).fetchone()

    if not row:
        raise ValueError("Selected class was not found.")


def create_section(section_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    section = Section(**section_data).validate()
    data = asdict(section)

    try:
        with closing(get_connection()) as connection:
            with connection:
                _validate_class_reference(
                    connection,
                    data["class_id"]
                )

                cursor = connection.execute(
                    """
                    INSERT INTO sections (
                        class_id,
                        name
                    )
                    VALUES (?, ?)
                    """,
                    (
                        data["class_id"],
                        data["name"],
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "sections.class_id, sections.name" in str(error):
            raise ValueError(
                "This section name already exists in the selected class."
            )

        raise ValueError(
            f"Could not create section: {error}"
        )


def get_section(section_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    section_id = _validate_section_id(section_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                s.id,
                s.class_id,
                s.name,
                c.name AS class_name
            FROM sections AS s
            JOIN classes AS c
                ON c.id = s.class_id
            WHERE s.id = ?
            """,
            (section_id,)
        ).fetchone()

        return dict(row) if row else None


def get_sections(search="", class_id=None, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    search = str(search or "").strip()

    conditions = []
    parameters = []

    if class_id is not None:
        if isinstance(class_id, bool):
            raise ValueError(
                "Class ID must be a positive integer."
            )

        try:
            class_id = int(class_id)
        except (TypeError, ValueError):
            raise ValueError(
                "Class ID must be a positive integer."
            )

        if class_id <= 0:
            raise ValueError(
                "Class ID must be a positive integer."
            )

        conditions.append("s.class_id = ?")
        parameters.append(class_id)

    if search:
        pattern = f"%{search}%"

        conditions.append(
            """
            (
                s.name LIKE ?
                OR c.name LIKE ?
            )
            """
        )

        parameters.extend([pattern, pattern])

    query = """
        SELECT
            s.id,
            s.class_id,
            s.name,
            c.name AS class_name
        FROM sections AS s
        JOIN classes AS c
            ON c.id = s.class_id
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY c.name COLLATE NOCASE,
                 s.name COLLATE NOCASE,
                 s.id
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def update_section(section_id, section_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    section_id = _validate_section_id(section_id)

    section = Section(**section_data).validate()
    data = asdict(section)

    try:
        with closing(get_connection()) as connection:
            with connection:
                existing = connection.execute(
                    """
                    SELECT id
                    FROM sections
                    WHERE id = ?
                    """,
                    (section_id,)
                ).fetchone()

                if not existing:
                    raise ValueError(
                        "Section record was not found."
                    )

                _validate_class_reference(
                    connection,
                    data["class_id"]
                )

                connection.execute(
                    """
                    UPDATE sections
                    SET class_id = ?,
                        name = ?
                    WHERE id = ?
                    """,
                    (
                        data["class_id"],
                        data["name"],
                        section_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        if "sections.class_id, sections.name" in str(error):
            raise ValueError(
                "This section name already exists in the selected class."
            )

        raise ValueError(
            f"Could not update section: {error}"
        )
