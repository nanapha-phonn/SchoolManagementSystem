import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.student_transport_assignment import StudentTransportAssignment


def _validate_references(connection, assignment_data, exclude_assignment_id=None):
    """
    Validate student, route, and stop references.

    For active assignments, also check student, route, and vehicle status
    and available vehicle capacity.
    """
    student = connection.execute(
        """
        SELECT id, status
        FROM students
        WHERE id = ?
        """,
        (assignment_data["student_id"],),
    ).fetchone()

    if student is None:
        raise ValueError("The selected student does not exist.")

    route = connection.execute(
        """
        SELECT
            tr.id,
            tr.status,
            tr.vehicle_id,
            v.capacity,
            v.status AS vehicle_status
        FROM transport_routes AS tr
        LEFT JOIN vehicles AS v ON tr.vehicle_id = v.id
        WHERE tr.id = ?
        """,
        (assignment_data["route_id"],),
    ).fetchone()

    if route is None:
        raise ValueError("The selected transport route does not exist.")

    # A selected pickup or drop-off stop must belong to this route.
    for stop_field, label in (
        ("pickup_stop_id", "Pickup"),
        ("dropoff_stop_id", "Drop-off"),
    ):
        stop_id = assignment_data[stop_field]

        if stop_id is None:
            continue

        stop = connection.execute(
            """
            SELECT id
            FROM route_stops
            WHERE id = ? AND route_id = ?
            """,
            (stop_id, assignment_data["route_id"]),
        ).fetchone()

        if stop is None:
            raise ValueError(
                f"{label} stop does not belong to the selected route."
            )

    # Historical assignments do not require active resources.
    if assignment_data["status"] != "active":
        return

    if student["status"] != "active":
        raise ValueError(
            "Only active students can receive an active transport assignment."
        )

    if route["status"] != "active":
        raise ValueError(
            "Cannot assign a student to an inactive transport route."
        )

    # Routes without vehicles can be assigned while awaiting a vehicle.
    if route["vehicle_id"] is None:
        return

    if route["vehicle_status"] != "active":
        raise ValueError(
            "The vehicle assigned to this route is not active."
        )

    # Check vehicle capacity.
    capacity_query = """
        SELECT COUNT(*) AS assigned_count
        FROM student_transport_assignments
        WHERE route_id = ?
          AND status = 'active'
    """

    parameters = [assignment_data["route_id"]]

    if exclude_assignment_id is not None:
        capacity_query += " AND id != ?"
        parameters.append(exclude_assignment_id)

    assigned_count = connection.execute(
        capacity_query,
        parameters,
    ).fetchone()["assigned_count"]

    if assigned_count >= route["capacity"]:
        raise ValueError(
            "The vehicle assigned to this route has reached its capacity."
        )


def create_student_transport_assignment(assignment_data):
    assignment = StudentTransportAssignment(
        **assignment_data
    ).validate()

    data = asdict(assignment)

    try:
        with closing(get_connection()) as connection:
            with connection:
                _validate_references(connection, data)

                cursor = connection.execute(
                    """
                    INSERT INTO student_transport_assignments (
                        student_id,
                        route_id,
                        pickup_stop_id,
                        dropoff_stop_id,
                        start_date,
                        end_date,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["student_id"],
                        data["route_id"],
                        data["pickup_stop_id"],
                        data["dropoff_stop_id"],
                        data["start_date"],
                        data["end_date"],
                        data["status"],
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        message = str(error)

        if "student_transport_assignments.student_id" in message:
            raise ValueError(
                "This student already has an active transport assignment."
            ) from error

        if "FOREIGN KEY constraint failed" in message:
            raise ValueError(
                "One or more referenced records do not exist or are invalid."
            ) from error

        raise ValueError(
            f"Could not create transport assignment: {error}"
        ) from error


def get_student_transport_assignment(assignment_id):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                sta.*,
                s.admission_no,
                s.first_name AS student_first_name,
                s.last_name AS student_last_name,
                tr.route_code,
                tr.route_name,
                pickup.stop_name AS pickup_stop_name,
                dropoff.stop_name AS dropoff_stop_name
            FROM student_transport_assignments AS sta
            JOIN students AS s
                ON sta.student_id = s.id
            JOIN transport_routes AS tr
                ON sta.route_id = tr.id
            LEFT JOIN route_stops AS pickup
                ON sta.pickup_stop_id = pickup.id
            LEFT JOIN route_stops AS dropoff
                ON sta.dropoff_stop_id = dropoff.id
            WHERE sta.id = ?
            """,
            (assignment_id,),
        ).fetchone()

        return dict(row) if row else None


def get_student_transport_assignments(search=""):
    search = search.strip()

    query = """
        SELECT
            sta.*,
            s.admission_no,
            s.first_name AS student_first_name,
            s.last_name AS student_last_name,
            tr.route_code,
            tr.route_name,
            pickup.stop_name AS pickup_stop_name,
            dropoff.stop_name AS dropoff_stop_name
        FROM student_transport_assignments AS sta
        JOIN students AS s
            ON sta.student_id = s.id
        JOIN transport_routes AS tr
            ON sta.route_id = tr.id
        LEFT JOIN route_stops AS pickup
            ON sta.pickup_stop_id = pickup.id
        LEFT JOIN route_stops AS dropoff
            ON sta.dropoff_stop_id = dropoff.id
    """

    parameters = ()

    if search:
        pattern = f"%{search}%"
        query += """
            WHERE s.admission_no LIKE ?
               OR s.first_name LIKE ?
               OR s.last_name LIKE ?
               OR tr.route_code LIKE ?
               OR tr.route_name LIKE ?
        """
        parameters = (pattern, pattern, pattern, pattern, pattern)

    query += " ORDER BY sta.created_at DESC, sta.id DESC"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]


def get_student_transport_assignments_by_student(student_id):
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                sta.*,
                tr.route_code,
                tr.route_name,
                pickup.stop_name AS pickup_stop_name,
                dropoff.stop_name AS dropoff_stop_name
            FROM student_transport_assignments AS sta
            JOIN transport_routes AS tr
                ON sta.route_id = tr.id
            LEFT JOIN route_stops AS pickup
                ON sta.pickup_stop_id = pickup.id
            LEFT JOIN route_stops AS dropoff
                ON sta.dropoff_stop_id = dropoff.id
            WHERE sta.student_id = ?
            ORDER BY sta.created_at DESC, sta.id DESC
            """,
            (student_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def update_student_transport_assignment(assignment_id, assignment_data):
    assignment = StudentTransportAssignment(
        **assignment_data
    ).validate()

    data = asdict(assignment)

    try:
        with closing(get_connection()) as connection:
            with connection:
                existing = connection.execute(
                    """
                    SELECT id
                    FROM student_transport_assignments
                    WHERE id = ?
                    """,
                    (assignment_id,),
                ).fetchone()

                if existing is None:
                    raise ValueError(
                        "Transport assignment record was not found."
                    )

                _validate_references(
                    connection,
                    data,
                    exclude_assignment_id=assignment_id,
                )

                connection.execute(
                    """
                    UPDATE student_transport_assignments
                    SET student_id = ?,
                        route_id = ?,
                        pickup_stop_id = ?,
                        dropoff_stop_id = ?,
                        start_date = ?,
                        end_date = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["student_id"],
                        data["route_id"],
                        data["pickup_stop_id"],
                        data["dropoff_stop_id"],
                        data["start_date"],
                        data["end_date"],
                        data["status"],
                        assignment_id,
                    ),
                )

    except sqlite3.IntegrityError as error:
        message = str(error)

        if "student_transport_assignments.student_id" in message:
            raise ValueError(
                "This student already has an active transport assignment."
            ) from error

        if "FOREIGN KEY constraint failed" in message:
            raise ValueError(
                "One or more referenced records do not exist or are invalid."
            ) from error

        raise ValueError(
            f"Could not update transport assignment: {error}"
        ) from error


def update_student_transport_assignment_status(assignment_id, status):
    with closing(get_connection()) as connection:
        with connection:
            row = connection.execute(
                """
                SELECT *
                FROM student_transport_assignments
                WHERE id = ?
                """,
                (assignment_id,),
            ).fetchone()

            if row is None:
                raise ValueError(
                    "Transport assignment record was not found."
                )

            data = dict(row)
            data["status"] = status

            assignment = StudentTransportAssignment(
                student_id=data["student_id"],
                route_id=data["route_id"],
                pickup_stop_id=data["pickup_stop_id"],
                dropoff_stop_id=data["dropoff_stop_id"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                status=data["status"],
            ).validate()

            validated_data = asdict(assignment)

            try:
                _validate_references(
                    connection,
                    validated_data,
                    exclude_assignment_id=assignment_id,
                )

                connection.execute(
                    """
                    UPDATE student_transport_assignments
                    SET status = ?
                    WHERE id = ?
                    """,
                    (validated_data["status"], assignment_id),
                )

            except sqlite3.IntegrityError as error:
                if "student_transport_assignments.student_id" in str(error):
                    raise ValueError(
                        "This student already has another active "
                        "transport assignment."
                    ) from error

                raise ValueError(
                    f"Could not update assignment status: {error}"
                ) from error
