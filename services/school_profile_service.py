import re
from contextlib import closing

from database.database import get_connection
from services.permission_service import require_permission


def _validate_profile(profile_data):
    if not isinstance(profile_data, dict):
        raise ValueError("School profile data must be a dictionary.")

    fields = {
        "name": 120,
        "address": 500,
        "phone": 50,
        "email": 254,
    }

    cleaned = {}

    for field, maximum in fields.items():
        label = "School name" if field == "name" else field.title()
        value = profile_data.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            raise ValueError(f"{label} must be text.")

        value = value.strip()

        if len(value) > maximum:
            raise ValueError(
                f"{label} must not exceed {maximum} characters."
            )

        cleaned[field] = value or None

    if not cleaned["name"]:
        raise ValueError("School name is required.")

    email = cleaned["email"]

    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid school email address.")

    return cleaned


def get_school_profile(*, actor_user_id):
    require_permission(actor_user_id, "school.profile.view")

    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id, name, address, phone, email, created_at
            FROM schools
            ORDER BY id
            """
        ).fetchall()

        if len(rows) > 1:
            raise ValueError(
                "Multiple school profiles exist. "
                "This version supports one school profile."
            )

        return dict(rows[0]) if rows else None


def save_school_profile(profile_data, *, actor_user_id):
    require_permission(actor_user_id, "system.manage")
    data = _validate_profile(profile_data)

    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            rows = connection.execute(
                "SELECT id FROM schools ORDER BY id"
            ).fetchall()

            if len(rows) > 1:
                raise ValueError(
                    "Multiple school profiles exist. "
                    "This version supports one school profile."
                )

            if rows:
                school_id = rows[0]["id"]

                connection.execute(
                    """
                    UPDATE schools
                    SET name = ?,
                        address = ?,
                        phone = ?,
                        email = ?
                    WHERE id = ?
                    """,
                    (
                        data["name"],
                        data["address"],
                        data["phone"],
                        data["email"],
                        school_id,
                    ),
                )

                return school_id

            cursor = connection.execute(
                """
                INSERT INTO schools (
                    name,
                    address,
                    phone,
                    email
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["address"],
                    data["phone"],
                    data["email"],
                ),
            )

            return cursor.lastrowid
