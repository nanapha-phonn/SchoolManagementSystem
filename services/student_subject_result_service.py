import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.student_subject_result import StudentSubjectResult


def _validate_id(value, field_name="Result ID"):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{field_name} must be a positive integer.")

    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a positive integer.")

    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return value


def _translate_integrity_error(error):
    message = str(error).lower()

    if "unique constraint failed" in message:
        return ValueError(
            "A result already exists for this student, subject, "
            "and assessment period."
        )

    if "references do not match" in message:
        return ValueError(
            "The selected enrollment, assessment period, teacher "
            "assignment, subject, and grading scheme do not match."
        )

    if "cannot be changed" in message:
        return ValueError(str(error))

    if "cannot be deleted" in message:
        return ValueError(str(error))

    if "only be changed" in message:
        return ValueError(str(error))

    if "cannot invalidate existing" in message:
        return ValueError(str(error))

    if "foreign key constraint failed" in message:
        return ValueError(
            "One or more selected academic records no longer exist."
        )

    if "check constraint failed" in message:
        return ValueError(
            "Invalid marks. Marks must be nonnegative and "
            "cannot exceed the maximum marks."
        )

    return ValueError(f"Could not save student result: {error}")


def _result_query():
    return """
        SELECT
            r.*,

            e.student_id,
            st.admission_no,
            st.first_name AS student_first_name,
            st.last_name AS student_last_name,

            ap.name AS assessment_period_name,
            ap.period_type,
            ap.start_date AS assessment_start_date,
            ap.end_date AS assessment_end_date,
            ap.status AS assessment_period_status,

            ay.name AS academic_year_name,

            sec.name AS section_name,
            c.name AS class_name,

            sub.subject_code,
            sub.name AS subject_name,

            tsa.teacher_id,
            t.employee_no,
            t.first_name || ' ' || t.last_name AS teacher_name,

            gs.name AS grading_scheme_name,
            gs.version_no AS grading_scheme_version,
            gs.status AS grading_scheme_status

        FROM student_subject_results AS r

        JOIN enrollments AS e
            ON e.id = r.enrollment_id

        JOIN students AS st
            ON st.id = e.student_id

        JOIN assessment_periods AS ap
            ON ap.id = r.assessment_period_id

        JOIN academic_years AS ay
            ON ay.id = e.academic_year_id

        JOIN sections AS sec
            ON sec.id = e.section_id

        JOIN classes AS c
            ON c.id = sec.class_id

        JOIN subjects AS sub
            ON sub.id = r.subject_id

        JOIN teacher_subject_assignments AS tsa
            ON tsa.id = r.teacher_subject_assignment_id

        JOIN teachers AS t
            ON t.id = tsa.teacher_id

        JOIN grading_schemes AS gs
            ON gs.id = r.grading_scheme_id
    """


def create_student_subject_result(result_data):
    result = StudentSubjectResult(**result_data).validate()
    data = asdict(result)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                cursor = connection.execute("""
                    INSERT INTO student_subject_results (
                        enrollment_id,
                        assessment_period_id,
                        teacher_subject_assignment_id,
                        subject_id,
                        grading_scheme_id,
                        marks_obtained,
                        maximum_marks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["enrollment_id"],
                    data["assessment_period_id"],
                    data["teacher_subject_assignment_id"],
                    data["subject_id"],
                    data["grading_scheme_id"],
                    data["marks_obtained"],
                    data["maximum_marks"],
                ))

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)


def get_student_subject_result(result_id):
    result_id = _validate_id(result_id)

    with closing(get_connection()) as connection:
        row = connection.execute(
            _result_query() + " WHERE r.id = ?",
            (result_id,),
        ).fetchone()

        return dict(row) if row else None


def get_student_subject_results(
    enrollment_id=None,
    assessment_period_id=None,
    section_id=None,
    academic_year_id=None,
    subject_id=None,
    teacher_subject_assignment_id=None,
    grading_scheme_id=None,
    search="",
):
    filters = {
        "enrollment_id": enrollment_id,
        "assessment_period_id": assessment_period_id,
        "section_id": section_id,
        "academic_year_id": academic_year_id,
        "subject_id": subject_id,
        "teacher_subject_assignment_id": teacher_subject_assignment_id,
        "grading_scheme_id": grading_scheme_id,
    }

    conditions = []
    parameters = []

    column_map = {
        "enrollment_id": "r.enrollment_id",
        "assessment_period_id": "r.assessment_period_id",
        "section_id": "e.section_id",
        "academic_year_id": "e.academic_year_id",
        "subject_id": "r.subject_id",
        "teacher_subject_assignment_id": "r.teacher_subject_assignment_id",
        "grading_scheme_id": "r.grading_scheme_id",
    }

    for field, value in filters.items():
        if value is not None:
            validated_id = _validate_id(value, field.replace("_", " ").title())
            conditions.append(f"{column_map[field]} = ?")
            parameters.append(validated_id)

    if not isinstance(search, str):
        raise ValueError("Search text must be a string.")

    search = search.strip()

    if len(search) > 150:
        raise ValueError("Search text cannot exceed 150 characters.")

    if search:
        conditions.append("""
            (
                st.admission_no LIKE ?
                OR st.first_name LIKE ?
                OR st.last_name LIKE ?
                OR sub.subject_code LIKE ?
                OR sub.name LIKE ?
                OR ap.name LIKE ?
                OR t.first_name LIKE ?
                OR t.last_name LIKE ?
            )
        """)
        pattern = f"%{search}%"
        parameters.extend([pattern] * 8)

    query = _result_query()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY
            ap.start_date DESC,
            st.last_name,
            st.first_name,
            sub.name
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]


def update_student_subject_result(result_id, result_data):
    result_id = _validate_id(result_id)

    if not isinstance(result_data, dict) or not result_data:
        raise ValueError("Result update data is required.")

    allowed_fields = {"marks_obtained", "maximum_marks"}

    unexpected = set(result_data) - allowed_fields

    if unexpected:
        raise ValueError(
            f"Unsupported result update fields: {sorted(unexpected)}"
        )

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute("""
                    SELECT *
                    FROM student_subject_results
                    WHERE id = ?
                """, (result_id,)).fetchone()

                if not existing:
                    raise ValueError("Student result was not found.")

                data = {
                    "enrollment_id": existing["enrollment_id"],
                    "assessment_period_id": existing["assessment_period_id"],
                    "teacher_subject_assignment_id":
                        existing["teacher_subject_assignment_id"],
                    "subject_id": existing["subject_id"],
                    "grading_scheme_id": existing["grading_scheme_id"],
                    "marks_obtained": existing["marks_obtained"],
                    "maximum_marks": existing["maximum_marks"],
                }

                data.update(result_data)

                validated = StudentSubjectResult(**data).validate()

                connection.execute("""
                    UPDATE student_subject_results
                    SET marks_obtained = ?,
                        maximum_marks = ?
                    WHERE id = ?
                """, (
                    validated.marks_obtained,
                    validated.maximum_marks,
                    result_id,
                ))

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)

    return get_student_subject_result(result_id)


def delete_student_subject_result(result_id):
    result_id = _validate_id(result_id)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")

                existing = connection.execute("""
                    SELECT id
                    FROM student_subject_results
                    WHERE id = ?
                """, (result_id,)).fetchone()

                if not existing:
                    raise ValueError("Student result was not found.")

                connection.execute("""
                    DELETE FROM student_subject_results
                    WHERE id = ?
                """, (result_id,))

    except sqlite3.IntegrityError as error:
        raise _translate_integrity_error(error)

    return True
