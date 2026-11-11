from database.database import get_connection


def get_dashboard_summary():
    """Retrieve summary statistics from the school database."""

    with get_connection() as connection:
        students = connection.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        classes = connection.execute(
            "SELECT COUNT(*) FROM classes"
        ).fetchone()[0]

        enrollments = connection.execute(
            "SELECT COUNT(*) FROM enrollments"
        ).fetchone()[0]

        users = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

    return {
        "students": students,
        "classes": classes,
        "enrollments": enrollments,
        "users": users
    }
