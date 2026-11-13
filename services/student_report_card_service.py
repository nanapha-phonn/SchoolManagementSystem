from contextlib import closing

from database.database import get_connection


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


def _get_grade_band(connection, scheme_id, percentage):
    row = connection.execute("""
        SELECT
            id,
            grade_label,
            min_percentage,
            grade_point,
            remark
        FROM grade_bands
        WHERE grading_scheme_id = ?
          AND min_percentage <= ?
        ORDER BY min_percentage DESC
        LIMIT 1
    """, (scheme_id, percentage)).fetchone()

    if not row:
        raise ValueError(
            "No applicable grade band was found for the result."
        )

    return dict(row)


def get_student_report_card(enrollment_id, assessment_period_id):
    """
    Return one student's report card for an assessment period.

    Overall percentage is calculated using total marks obtained
    divided by total maximum marks. Subject results retain their
    original grading scheme.
    """
    enrollment_id = _validate_id(
        enrollment_id,
        "Enrollment ID",
    )
    assessment_period_id = _validate_id(
        assessment_period_id,
        "Assessment period ID",
    )

    with closing(get_connection()) as connection:
        school_rows = connection.execute("""
            SELECT id, name, address, phone, email
            FROM schools
            ORDER BY id
        """).fetchall()
        if len(school_rows) > 1:
            raise ValueError(
                "Multiple school profiles exist. "
                "This version supports one school profile."
            )
        school_profile = (
            dict(school_rows[0]) if school_rows else None
        )

        enrollment = connection.execute("""
            SELECT
                e.id AS enrollment_id,
                e.student_id,
                e.section_id,
                e.academic_year_id,
                e.enrolled_on,
                e.status AS enrollment_status,

                st.admission_no,
                st.first_name,
                st.last_name,
                st.first_name || ' ' || st.last_name AS student_name,

                sec.name AS section_name,

                c.id AS class_id,
                c.name AS class_name,

                ay.name AS academic_year_name

            FROM enrollments AS e

            JOIN students AS st
                ON st.id = e.student_id

            JOIN sections AS sec
                ON sec.id = e.section_id

            JOIN classes AS c
                ON c.id = sec.class_id

            JOIN academic_years AS ay
                ON ay.id = e.academic_year_id

            WHERE e.id = ?
        """, (enrollment_id,)).fetchone()

        if not enrollment:
            raise ValueError("Student enrollment was not found.")

        period = connection.execute("""
            SELECT
                ap.*,
                ay.name AS academic_year_name
            FROM assessment_periods AS ap
            JOIN academic_years AS ay
                ON ay.id = ap.academic_year_id
            WHERE ap.id = ?
        """, (assessment_period_id,)).fetchone()

        if not period:
            raise ValueError("Assessment period was not found.")

        if enrollment["academic_year_id"] != period["academic_year_id"]:
            raise ValueError(
                "The assessment period and student enrollment "
                "belong to different academic years."
            )

        rows = connection.execute("""
            SELECT
                r.id AS result_id,
                r.marks_obtained,
                r.maximum_marks,
                r.created_at,
                r.updated_at,

                s.id AS subject_id,
                s.subject_code,
                s.name AS subject_name,

                t.employee_no,
                t.first_name || ' ' || t.last_name AS teacher_name,

                gs.id AS grading_scheme_id,
                gs.name AS grading_scheme_name,
                gs.version_no AS grading_scheme_version,
                gs.status AS grading_scheme_status,

                ROUND(
                    r.marks_obtained * 100.0 / r.maximum_marks,
                    2
                ) AS percentage,

                gb.grade_label,
                gb.grade_point,
                gb.remark AS grade_remark

            FROM student_subject_results AS r

            JOIN subjects AS s
                ON s.id = r.subject_id

            JOIN teacher_subject_assignments AS tsa
                ON tsa.id = r.teacher_subject_assignment_id

            JOIN teachers AS t
                ON t.id = tsa.teacher_id

            JOIN grading_schemes AS gs
                ON gs.id = r.grading_scheme_id

            LEFT JOIN grade_bands AS gb
                ON gb.id = (
                    SELECT gb2.id
                    FROM grade_bands AS gb2
                    WHERE gb2.grading_scheme_id = r.grading_scheme_id
                      AND gb2.min_percentage <=
                          (r.marks_obtained * 100.0 / r.maximum_marks)
                    ORDER BY gb2.min_percentage DESC
                    LIMIT 1
                )

            WHERE r.enrollment_id = ?
              AND r.assessment_period_id = ?

            ORDER BY s.name COLLATE NOCASE
        """, (
            enrollment_id,
            assessment_period_id,
        )).fetchall()

        subjects = [dict(row) for row in rows]

        # Calculate the report-card summary.
        total_obtained = sum(
            float(row["marks_obtained"])
            for row in subjects
        )
        total_maximum = sum(
            float(row["maximum_marks"])
            for row in subjects
        )

        overall_percentage = None
        overall_grade = None
        grading_scheme = None

        if subjects:
            scheme_ids = {
                row["grading_scheme_id"]
                for row in subjects
            }

            if len(scheme_ids) != 1:
                raise ValueError(
                    "Report-card results use inconsistent grading schemes."
                )

            scheme_id = next(iter(scheme_ids))

            overall_percentage = round(
                total_obtained * 100.0 / total_maximum,
                2,
            )

            overall_grade = _get_grade_band(
                connection,
                scheme_id,
                total_obtained * 100.0 / total_maximum,
            )

            grading_scheme = {
                "id": scheme_id,
                "name": subjects[0]["grading_scheme_name"],
                "version": subjects[0]["grading_scheme_version"],
                "status": subjects[0]["grading_scheme_status"],
            }

        return {
            "school": school_profile,

            "student": {
                "id": enrollment["student_id"],
                "admission_no": enrollment["admission_no"],
                "first_name": enrollment["first_name"],
                "last_name": enrollment["last_name"],
                "full_name": enrollment["student_name"],
            },

            "enrollment": {
                "id": enrollment["enrollment_id"],
                "status": enrollment["enrollment_status"],
                "enrolled_on": enrollment["enrolled_on"],
            },

            "class": {
                "id": enrollment["class_id"],
                "name": enrollment["class_name"],
            },

            "section": {
                "id": enrollment["section_id"],
                "name": enrollment["section_name"],
            },

            "academic_year": {
                "id": enrollment["academic_year_id"],
                "name": enrollment["academic_year_name"],
            },

            "assessment_period": {
                "id": period["id"],
                "name": period["name"],
                "type": period["period_type"],
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "status": period["status"],
            },

            "grading_scheme": grading_scheme,

            "subjects": subjects,

            "summary": {
                "subject_count": len(subjects),
                "total_marks_obtained": round(total_obtained, 2),
                "total_maximum_marks": round(total_maximum, 2),
                "overall_percentage": overall_percentage,
                "overall_grade_label": (
                    overall_grade["grade_label"]
                    if overall_grade else None
                ),
                "overall_grade_point": (
                    overall_grade["grade_point"]
                    if overall_grade else None
                ),
                "overall_remark": (
                    overall_grade["remark"]
                    if overall_grade else None
                ),
            },
        }
