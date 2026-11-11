import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from services.permission_service import require_permission
from models.subject import Subject, VALID_SUBJECT_STATUSES


def _validate_id(subject_id):
    if isinstance(subject_id, bool):
        raise ValueError("Subject ID must be a positive integer.")

    try:
        subject_id = int(subject_id)
    except (TypeError, ValueError):
        raise ValueError("Subject ID must be a positive integer.")

    if subject_id <= 0:
        raise ValueError("Subject ID must be a positive integer.")

    return subject_id


def create_subject(subject_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    subject = Subject(**subject_data).validate()
    data = asdict(subject)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO subjects (
                        subject_code,
                        name,
                        description,
                        status
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        data["subject_code"],
                        data["name"],
                        data["description"] or None,
                        data["status"],
                    )
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        message = str(error).lower()

        if "subject_code" in message:
            raise ValueError("This subject code already exists.")

        if "subjects.name" in message or "name" in message:
            raise ValueError("This subject name already exists.")

        raise ValueError(f"Could not create subject: {error}")


def get_subject(subject_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    subject_id = _validate_id(subject_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM subjects
            WHERE id = ?
            """,
            (subject_id,)
        ).fetchone()

        return dict(row) if row else None


def get_subjects(search="", status=None, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    search = str(search or "").strip()

    if status is not None:
        if status not in VALID_SUBJECT_STATUSES:
            raise ValueError("Invalid subject status filter.")

    conditions = []
    parameters = []

    if search:
        pattern = f"%{search}%"
        conditions.append("""
            (
                subject_code LIKE ?
                OR name LIKE ?
                OR description LIKE ?
            )
        """)
        parameters.extend([pattern, pattern, pattern])

    if status is not None:
        conditions.append("status = ?")
        parameters.append(status)

    query = "SELECT * FROM subjects"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY name COLLATE NOCASE, subject_code"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]


def update_subject(subject_id, subject_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    subject_id = _validate_id(subject_id)

    subject = Subject(**subject_data).validate()
    data = asdict(subject)

    try:
        with closing(get_connection()) as connection:
            with connection:
                existing = connection.execute(
                    """
                    SELECT id
                    FROM subjects
                    WHERE id = ?
                    """,
                    (subject_id,)
                ).fetchone()

                if not existing:
                    raise ValueError("Subject record was not found.")

                if data["status"] == "inactive":
                    active_assignments = connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM teacher_subject_assignments
                        WHERE subject_id = ?
                          AND status = 'active'
                        """,
                        (subject_id,)
                    ).fetchone()[0]

                    if active_assignments:
                        raise ValueError(
                            "End all active teacher assignments "
                            "before deactivating this subject."
                        )

                connection.execute(
                    """
                    UPDATE subjects
                    SET subject_code = ?,
                        name = ?,
                        description = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["subject_code"],
                        data["name"],
                        data["description"] or None,
                        data["status"],
                        subject_id,
                    )
                )

    except sqlite3.IntegrityError as error:
        message = str(error).lower()

        if "subject_code" in message:
            raise ValueError("This subject code already exists.")

        if "subjects.name" in message or "name" in message:
            raise ValueError("This subject name already exists.")

        raise ValueError(f"Could not update subject: {error}")


def update_subject_status(subject_id, status, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    subject_id = _validate_id(subject_id)

    if status not in VALID_SUBJECT_STATUSES:
        raise ValueError("Invalid subject status.")

    subject = get_subject(subject_id, actor_user_id=actor_user_id)

    if not subject:
        raise ValueError("Subject record was not found.")

    update_subject(
        subject_id,
        {
            "subject_code": subject["subject_code"],
            "name": subject["name"],
            "description": subject["description"] or "",
            "status": status,
        },
        actor_user_id=actor_user_id,
    )
