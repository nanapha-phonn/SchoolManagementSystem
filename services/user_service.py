import re
import sqlite3
import bcrypt

from database.database import get_connection
from services.auth_service import VALID_ROLES, validate_password


def _validate_user_data(username, full_name, role):
    username = username.strip().lower()
    full_name = full_name.strip()

    if not re.fullmatch(r"[a-z0-9_-]{3,30}", username):
        raise ValueError(
            "Username must contain 3–30 letters, numbers, underscores, or hyphens."
        )

    if not full_name:
        raise ValueError("Full name is required.")

    if len(full_name) > 100:
        raise ValueError("Full name must not exceed 100 characters.")

    if role not in VALID_ROLES:
        raise ValueError("Invalid user role.")

    return username, full_name


def _require_admin(connection, actor_user_id):
    actor = connection.execute(
        """
        SELECT id, role, is_active
        FROM users
        WHERE id = ?
        """,
        (actor_user_id,)
    ).fetchone()

    if actor is None or not actor["is_active"] or actor["role"] != "admin":
        raise PermissionError("Administrator permission is required.")

    return actor


def _get_active_admin_count(connection):
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'admin' AND is_active = 1
        """
    ).fetchone()[0]


def _public_user(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"],
    }


def create_user(username, password, full_name, role, actor_user_id):
    username, full_name = _validate_user_data(
        username, full_name, role
    )
    validate_password(password)

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            _require_admin(connection, actor_user_id)

            cursor = connection.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    full_name,
                    role
                )
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, full_name, role)
            )

            user_id = cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "username" in str(error).lower():
            raise ValueError("This username is already registered.")
        raise ValueError("Could not create user because of a database constraint.")

    return user_id


def get_user(user_id, actor_user_id):
    with get_connection() as connection:
        _require_admin(connection, actor_user_id)
        row = connection.execute(
            """
            SELECT id, username, full_name, role, is_active, created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()
    return _public_user(row)


def get_users(actor_user_id):
    with get_connection() as connection:
        _require_admin(connection, actor_user_id)

        rows = connection.execute(
            """
            SELECT id, username, full_name, role, is_active, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    return [_public_user(row) for row in rows]


def search_users(search_term, actor_user_id):
    search_term = search_term.strip()

    with get_connection() as connection:
        _require_admin(connection, actor_user_id)

        rows = connection.execute(
            """
            SELECT id, username, full_name, role, is_active, created_at
            FROM users
            WHERE username LIKE ?
               OR full_name LIKE ?
               OR role LIKE ?
            ORDER BY id
            """,
            (
                f"%{search_term}%",
                f"%{search_term}%",
                f"%{search_term}%"
            )
        ).fetchall()

    return [_public_user(row) for row in rows]


def update_user(
    user_id,
    username,
    full_name,
    role,
    actor_user_id
):
    username, full_name = _validate_user_data(
        username, full_name, role
    )

    try:
        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")

            _require_admin(connection, actor_user_id)

            target = connection.execute(
                """
                SELECT id, role, is_active
                FROM users
                WHERE id = ?
                """,
                (user_id,)
            ).fetchone()

            if target is None:
                raise ValueError("User account was not found.")

            if user_id == actor_user_id and role != target["role"]:
                raise ValueError("You cannot change your own administrator role.")

            if (
                target["role"] == "admin"
                and target["is_active"]
                and role != "admin"
                and _get_active_admin_count(connection) <= 1
            ):
                raise ValueError(
                    "The last active administrator cannot be demoted."
                )

            connection.execute(
                """
                UPDATE users
                SET username = ?, full_name = ?, role = ?
                WHERE id = ?
                """,
                (username, full_name, role, user_id)
            )

    except sqlite3.IntegrityError as error:
        if "username" in str(error).lower():
            raise ValueError("This username is already registered.")
        raise ValueError("Could not update user because of a database constraint.")

    return True


def update_user_status(user_id, is_active, actor_user_id):
    if type(is_active) is not bool:
        raise ValueError("Account status must be True or False.")

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        _require_admin(connection, actor_user_id)

        target = connection.execute(
            """
            SELECT id, role, is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if target is None:
            raise ValueError("User account was not found.")

        if user_id == actor_user_id and not is_active:
            raise ValueError("You cannot deactivate your own account.")

        if (
            target["role"] == "admin"
            and target["is_active"]
            and not is_active
            and _get_active_admin_count(connection) <= 1
        ):
            raise ValueError(
                "The last active administrator cannot be deactivated."
            )

        connection.execute(
            """
            UPDATE users
            SET is_active = ?
            WHERE id = ?
            """,
            (int(is_active), user_id)
        )

    return True
