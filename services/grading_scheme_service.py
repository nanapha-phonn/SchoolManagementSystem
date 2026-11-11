import math
import sqlite3
from contextlib import closing
from numbers import Real

from database.database import get_connection
from models.grading_scheme import GradingScheme
from models.grade_band import GradeBand
from services.permission_service import require_permission


def _validate_id(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    if value <= 0:
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    return value


def _translate_integrity_error(error):
    message = str(error)

    if (
        "UNIQUE constraint failed: "
        "grading_schemes.class_id, grading_schemes.academic_year_id"
    ) in message:
        return ValueError(
            "Another grading scheme is already active "
            "for this class and academic year."
        )

    if (
        "UNIQUE constraint failed: grading_schemes.class_id, "
        "grading_schemes.academic_year_id, grading_schemes.version_no"
    ) in message:
        return ValueError(
            "This grading scheme version already exists."
        )

    if "grade_bands.grading_scheme_id, grade_bands.grade_label" in message:
        return ValueError(
            "This grade label already exists in the grading scheme."
        )

    if "grade_bands.grading_scheme_id, grade_bands.min_percentage" in message:
        return ValueError(
            "This minimum percentage already exists in the grading scheme."
        )

    known_messages = (
        "New grading schemes must start as draft.",
        "Grading scheme identity and version cannot be changed.",
        "Only draft grading schemes can be renamed.",
        "Invalid grading scheme status transition.",
        "An active grading scheme requires at least two grade bands",
        "Grading scheme history cannot be deleted.",
        "Grade bands can only be added to an existing draft grading scheme.",
        "A grade band cannot be moved to another grading scheme.",
        "Only draft grading schemes can have their grade bands changed.",
        "Grade bands in active or archived schemes cannot be deleted.",
    )

    for known_message in known_messages:
        if known_message in message:
            return ValueError(known_message)

    if "FOREIGN KEY constraint failed" in message:
        return ValueError(
            "A selected class, academic year, or grading scheme was not found."
        )

    return ValueError(
        f"Grading database operation failed: {message}"
    )


def _scheme_query():
    return """
        SELECT
            gs.*,
            c.name AS class_name,
            ay.name AS academic_year_name,
            COUNT(gb.id) AS band_count
        FROM grading_schemes AS gs
        JOIN classes AS c
            ON c.id = gs.class_id
        JOIN academic_years AS ay
            ON ay.id = gs.academic_year_id
        LEFT JOIN grade_bands AS gb
            ON gb.grading_scheme_id = gs.id
    """


def _validate_draft_scheme(connection, scheme_id):
    scheme = connection.execute(
        """
        SELECT id, status
        FROM grading_schemes
        WHERE id = ?
        """,
        (scheme_id,),
    ).fetchone()

    if not scheme:
        raise ValueError("Grading scheme was not found.")

    if scheme["status"] != "draft":
        raise ValueError(
            "Only draft grading schemes can be modified."
        )

    return scheme


# --------------------------------------------------
# GRADING SCHEME CRUD
# --------------------------------------------------

def create_grading_scheme(scheme_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    if not isinstance(scheme_data, dict):
        raise ValueError("Grading scheme data must be a dictionary.")

    required_fields = {
        "class_id",
        "academic_year_id",
        "name",
    }

    if set(scheme_data) != required_fields:
        raise ValueError(
            "Grading scheme data must contain exactly "
            "class_id, academic_year_id, and name."
        )

    class_id = _validate_id(
        scheme_data["class_id"],
        "Class ID",
    )

    academic_year_id = _validate_id(
        scheme_data["academic_year_id"],
        "Academic year ID",
    )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                class_exists = connection.execute(
                    "SELECT id FROM classes WHERE id = ?",
                    (class_id,),
                ).fetchone()

                if not class_exists:
                    raise ValueError("Selected class was not found.")

                year_exists = connection.execute(
                    "SELECT id FROM academic_years WHERE id = ?",
                    (academic_year_id,),
                ).fetchone()

                if not year_exists:
                    raise ValueError(
                        "Selected academic year was not found."
                    )

                latest_version = connection.execute(
                    """
                    SELECT COALESCE(MAX(version_no), 0)
                    FROM grading_schemes
                    WHERE class_id = ?
                      AND academic_year_id = ?
                    """,
                    (class_id, academic_year_id),
                ).fetchone()[0]

                scheme = GradingScheme(
                    class_id=class_id,
                    academic_year_id=academic_year_id,
                    name=scheme_data["name"],
                    version_no=latest_version + 1,
                    status="draft",
                ).validate()

                cursor = connection.execute(
                    """
                    INSERT INTO grading_schemes (
                        class_id,
                        academic_year_id,
                        name,
                        version_no,
                        status
                    )
                    VALUES (?, ?, ?, ?, 'draft')
                    """,
                    (
                        scheme.class_id,
                        scheme.academic_year_id,
                        scheme.name,
                        scheme.version_no,
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def get_grading_scheme(scheme_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    with closing(get_connection()) as connection:
        row = connection.execute(
            _scheme_query() + """
                WHERE gs.id = ?
                GROUP BY gs.id
            """,
            (scheme_id,),
        ).fetchone()

        return dict(row) if row else None


def get_grading_schemes(
    class_id=None,
    academic_year_id=None,
    status=None,
    search="",
    *,
    actor_user_id,
):
    require_permission(actor_user_id, "academics.manage")
    conditions = []
    parameters = []

    if class_id is not None:
        class_id = _validate_id(class_id, "Class ID")
        conditions.append("gs.class_id = ?")
        parameters.append(class_id)

    if academic_year_id is not None:
        academic_year_id = _validate_id(
            academic_year_id,
            "Academic year ID",
        )
        conditions.append("gs.academic_year_id = ?")
        parameters.append(academic_year_id)

    if status is not None:
        status = str(status or "").strip().lower()

        if status not in {"draft", "active", "archived"}:
            raise ValueError("Invalid grading scheme status filter.")

        conditions.append("gs.status = ?")
        parameters.append(status)

    search = str(search or "").strip()

    if search:
        pattern = f"%{search}%"

        conditions.append("""
            (
                gs.name LIKE ?
                OR c.name LIKE ?
                OR ay.name LIKE ?
            )
        """)

        parameters.extend([pattern, pattern, pattern])

    query = _scheme_query()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        GROUP BY gs.id
        ORDER BY
            ay.start_date DESC,
            c.name COLLATE NOCASE,
            gs.version_no DESC
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]


def update_grading_scheme(scheme_id, scheme_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    if not isinstance(scheme_data, dict) or set(scheme_data) != {"name"}:
        raise ValueError(
            "Only the grading scheme name can be updated."
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = _validate_draft_scheme(
                    connection,
                    scheme_id,
                )

                row = connection.execute(
                    """
                    SELECT class_id, academic_year_id, version_no
                    FROM grading_schemes
                    WHERE id = ?
                    """,
                    (scheme_id,),
                ).fetchone()

                scheme = GradingScheme(
                    class_id=row["class_id"],
                    academic_year_id=row["academic_year_id"],
                    name=scheme_data["name"],
                    version_no=row["version_no"],
                    status=existing["status"],
                ).validate()

                connection.execute(
                    """
                    UPDATE grading_schemes
                    SET name = ?
                    WHERE id = ?
                    """,
                    (scheme.name, scheme_id),
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


# --------------------------------------------------
# GRADE BAND MANAGEMENT
# --------------------------------------------------

def _build_grade_band(scheme_id, band_data):
    if not isinstance(band_data, dict):
        raise ValueError("Grade band data must be a dictionary.")

    required_fields = {
        "grade_label",
        "min_percentage",
    }

    optional_fields = {
        "grade_point",
        "remark",
    }

    if not required_fields.issubset(band_data):
        raise ValueError(
            "Grade band requires grade_label and min_percentage."
        )

    if set(band_data) - required_fields - optional_fields:
        raise ValueError("Unexpected grade band fields were provided.")

    return GradeBand(
        grading_scheme_id=scheme_id,
        grade_label=band_data["grade_label"],
        min_percentage=band_data["min_percentage"],
        grade_point=band_data.get("grade_point"),
        remark=band_data.get("remark", ""),
    ).validate()


def create_grade_band(scheme_id, band_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    band = _build_grade_band(scheme_id, band_data)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                _validate_draft_scheme(connection, scheme_id)

                cursor = connection.execute(
                    """
                    INSERT INTO grade_bands (
                        grading_scheme_id,
                        grade_label,
                        min_percentage,
                        grade_point,
                        remark
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        band.grading_scheme_id,
                        band.grade_label,
                        band.min_percentage,
                        band.grade_point,
                        band.remark,
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def get_grade_band(band_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    band_id = _validate_id(
        band_id,
        "Grade band ID",
    )

    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM grade_bands
            WHERE id = ?
            """,
            (band_id,),
        ).fetchone()

        return dict(row) if row else None


def get_grade_bands(scheme_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    with closing(get_connection()) as connection:
        exists = connection.execute(
            "SELECT id FROM grading_schemes WHERE id = ?",
            (scheme_id,),
        ).fetchone()

        if not exists:
            raise ValueError("Grading scheme was not found.")

        rows = connection.execute(
            """
            SELECT *
            FROM grade_bands
            WHERE grading_scheme_id = ?
            ORDER BY min_percentage DESC, id
            """,
            (scheme_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def update_grade_band(band_id, band_data, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    band_id = _validate_id(
        band_id,
        "Grade band ID",
    )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT grading_scheme_id
                    FROM grade_bands
                    WHERE id = ?
                    """,
                    (band_id,),
                ).fetchone()

                if not existing:
                    raise ValueError("Grade band was not found.")

                scheme_id = existing["grading_scheme_id"]
                _validate_draft_scheme(connection, scheme_id)

                band = _build_grade_band(
                    scheme_id,
                    band_data,
                )

                connection.execute(
                    """
                    UPDATE grade_bands
                    SET grade_label = ?,
                        min_percentage = ?,
                        grade_point = ?,
                        remark = ?
                    WHERE id = ?
                    """,
                    (
                        band.grade_label,
                        band.min_percentage,
                        band.grade_point,
                        band.remark,
                        band_id,
                    ),
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def delete_grade_band(band_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    band_id = _validate_id(
        band_id,
        "Grade band ID",
    )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute(
                    """
                    SELECT grading_scheme_id
                    FROM grade_bands
                    WHERE id = ?
                    """,
                    (band_id,),
                ).fetchone()

                if not existing:
                    raise ValueError("Grade band was not found.")

                _validate_draft_scheme(
                    connection,
                    existing["grading_scheme_id"],
                )

                connection.execute(
                    "DELETE FROM grade_bands WHERE id = ?",
                    (band_id,),
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


# --------------------------------------------------
# SCHEME LIFECYCLE
# --------------------------------------------------

def activate_grading_scheme(scheme_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                scheme = _validate_draft_scheme(
                    connection,
                    scheme_id,
                )

                band_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM grade_bands
                    WHERE grading_scheme_id = ?
                    """,
                    (scheme_id,),
                ).fetchone()[0]

                zero_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM grade_bands
                    WHERE grading_scheme_id = ?
                      AND min_percentage = 0
                    """,
                    (scheme_id,),
                ).fetchone()[0]

                if band_count < 2 or zero_count != 1:
                    raise ValueError(
                        "An active grading scheme requires at least "
                        "two grade bands and exactly one 0 percent threshold."
                    )

                connection.execute(
                    """
                    UPDATE grading_schemes
                    SET status = 'active'
                    WHERE id = ?
                    """,
                    (scheme_id,),
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def archive_grading_scheme(scheme_id, *, actor_user_id):
    require_permission(actor_user_id, "academics.configure")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                row = connection.execute(
                    """
                    SELECT status
                    FROM grading_schemes
                    WHERE id = ?
                    """,
                    (scheme_id,),
                ).fetchone()

                if not row:
                    raise ValueError("Grading scheme was not found.")

                if row["status"] == "archived":
                    raise ValueError("Grading scheme is already archived.")

                connection.execute(
                    """
                    UPDATE grading_schemes
                    SET status = 'archived'
                    WHERE id = ?
                    """,
                    (scheme_id,),
                )

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


# --------------------------------------------------
# GRADE CALCULATION
# --------------------------------------------------

def get_grade_for_percentage(scheme_id, percentage, *, actor_user_id):
    require_permission(actor_user_id, "academics.manage")
    scheme_id = _validate_id(
        scheme_id,
        "Grading scheme ID",
    )

    if isinstance(percentage, bool) or not isinstance(percentage, Real):
        raise ValueError("Percentage must be numeric.")

    percentage = float(percentage)

    if not math.isfinite(percentage):
        raise ValueError("Percentage must be a finite number.")

    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100.")

    with closing(get_connection()) as connection:
        scheme = connection.execute(
            """
            SELECT status
            FROM grading_schemes
            WHERE id = ?
            """,
            (scheme_id,),
        ).fetchone()

        if not scheme:
            raise ValueError("Grading scheme was not found.")

        if scheme["status"] not in {"active", "archived"}:
            raise ValueError(
                "Grades can only be calculated using active "
                "or archived grading schemes."
            )

        row = connection.execute(
            """
            SELECT *
            FROM grade_bands
            WHERE grading_scheme_id = ?
              AND min_percentage <= ?
            ORDER BY min_percentage DESC
            LIMIT 1
            """,
            (scheme_id, percentage),
        ).fetchone()

        if not row:
            raise ValueError(
                "No applicable grade band was found."
            )

        return dict(row)
