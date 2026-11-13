from database.database import get_connection


# Version 1.0 role-based access policy.
PERMISSIONS = {
    "dashboard.view": {"admin", "staff"},
    "students.manage": {"admin", "staff"},
    "documents.view": {"admin", "staff"},
    "documents.manage": {"admin", "staff"},
    "documents.archive": {"admin"},
    "academics.manage": {"admin", "staff"},
    "academics.configure": {"admin"},
    "teachers.manage": {"admin", "staff"},
    "transportation.manage": {"admin", "staff"},
    "fees.manage": {"admin", "staff"},
    "fees.void": {"admin"},
    "fees.reports.view": {"admin"},
    "student_accounts.view": {"admin"},
    "payroll.manage": {"admin"},
    "payroll.reports.view": {"admin"},
    "users.manage": {"admin"},
    "school.profile.view": {"admin", "staff"},
    "system.manage": {"admin"},
}


def _get_active_user_role(connection, user_id):
    user = connection.execute(
        """
        SELECT role, is_active
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if user is None or not user["is_active"]:
        raise PermissionError("An active user account is required.")

    return user["role"]


def has_permission(user_id, permission):
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    with get_connection() as connection:
        role = _get_active_user_role(connection, user_id)

    return role in PERMISSIONS[permission]


def require_permission(user_id, permission):
    if not has_permission(user_id, permission):
        raise PermissionError(
            f"You do not have permission to perform: {permission}"
        )

    return True
