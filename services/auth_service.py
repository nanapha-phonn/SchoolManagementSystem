import bcrypt
import sqlite3

from database.database import get_connection


VALID_ROLES = {"admin", "staff"}


def validate_password(password):
    if not password:
        raise ValueError("Password cannot be empty.")

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    # bcrypt has a 72-byte password limit.
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 bytes.")


def count_users():
    with get_connection() as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()

        return result[0]


def create_initial_admin(username, password, full_name):
    username = username.strip().lower()
    full_name = full_name.strip()

    if not username:
        raise ValueError("Username is required.")

    if not full_name:
        raise ValueError("Full name is required.")

    validate_password(password)

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            existing_users = connection.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            if existing_users > 0:
                raise ValueError(
                    "An administrator account has already been created."
                )

            connection.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    full_name,
                    role
                )
                VALUES (?, ?, ?, 'admin')
                """,
                (username, password_hash, full_name)
            )

    except sqlite3.IntegrityError:
        raise ValueError("This username is already registered.")

    return True


def authenticate_user(username, password):
    username = username.strip().lower()

    if not username or not password:
        return None

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, password_hash, full_name, role, is_active
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    if user is None:
        return None

    if not user["is_active"]:
        return None

    try:
        password_matches = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )
    except (ValueError, TypeError):
        return None

    if not password_matches:
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"]
    }


def change_password(user_id, current_password, new_password):
    validate_password(new_password)

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,)
        ).fetchone()

        if user is None:
            raise ValueError("User account was not found.")

        if not bcrypt.checkpw(
            current_password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        ):
            raise ValueError("Current password is incorrect.")

        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (new_hash, user_id)
        )

    return True
