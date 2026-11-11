import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.vehicle import Vehicle, VALID_VEHICLE_STATUSES


def _validate_driver(connection, driver_id):
    """Allow only existing, active transport staff with the driver role."""

    if driver_id is None:
        return

    driver = connection.execute(
        """
        SELECT id, role, status
        FROM transport_staff
        WHERE id = ?
        """,
        (driver_id,),
    ).fetchone()

    if driver is None:
        raise ValueError("The selected driver does not exist.")

    if driver["role"] != "driver":
        raise ValueError(
            "Only transport staff with the driver role can be assigned."
        )

    if driver["status"] != "active":
        raise ValueError("The selected driver is not active.")


def create_vehicle(vehicle_data):
    vehicle = Vehicle(**vehicle_data).validate()
    data = asdict(vehicle)

    try:
        with closing(get_connection()) as connection:
            with connection:
                _validate_driver(connection, data["driver_id"])

                cursor = connection.execute(
                    """
                    INSERT INTO vehicles (
                        registration_no,
                        vehicle_type,
                        model,
                        capacity,
                        driver_id,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["registration_no"],
                        data["vehicle_type"] or None,
                        data["model"] or None,
                        data["capacity"],
                        data["driver_id"],
                        data["status"],
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "registration_no" in str(error):
            raise ValueError(
                "This vehicle registration number already exists."
            ) from error

        if "FOREIGN KEY constraint failed" in str(error):
            raise ValueError(
                "The selected driver does not exist."
            ) from error

        raise ValueError(f"Could not create vehicle: {error}") from error


def get_vehicle(vehicle_id):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                v.*,
                ts.employee_no AS driver_employee_no,
                ts.first_name AS driver_first_name,
                ts.last_name AS driver_last_name
            FROM vehicles AS v
            LEFT JOIN transport_staff AS ts
                ON v.driver_id = ts.id
            WHERE v.id = ?
            """,
            (vehicle_id,),
        ).fetchone()

        return dict(row) if row else None


def get_vehicles(search=""):
    search = search.strip()

    query = """
        SELECT
            v.*,
            ts.employee_no AS driver_employee_no,
            ts.first_name AS driver_first_name,
            ts.last_name AS driver_last_name
        FROM vehicles AS v
        LEFT JOIN transport_staff AS ts
            ON v.driver_id = ts.id
    """

    parameters = ()

    if search:
        pattern = f"%{search}%"

        query += """
            WHERE v.registration_no LIKE ?
               OR v.vehicle_type LIKE ?
               OR v.model LIKE ?
               OR ts.employee_no LIKE ?
               OR ts.first_name LIKE ?
               OR ts.last_name LIKE ?
        """

        parameters = (
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
            pattern,
        )

    query += " ORDER BY v.registration_no"

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]


def search_vehicles(search):
    return get_vehicles(search)


def update_vehicle(vehicle_id, vehicle_data):
    vehicle = Vehicle(**vehicle_data).validate()
    data = asdict(vehicle)

    try:
        with closing(get_connection()) as connection:
            with connection:
                _validate_driver(connection, data["driver_id"])

                cursor = connection.execute(
                    """
                    UPDATE vehicles
                    SET registration_no = ?,
                        vehicle_type = ?,
                        model = ?,
                        capacity = ?,
                        driver_id = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["registration_no"],
                        data["vehicle_type"] or None,
                        data["model"] or None,
                        data["capacity"],
                        data["driver_id"],
                        data["status"],
                        vehicle_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Vehicle record was not found.")

    except sqlite3.IntegrityError as error:
        if "registration_no" in str(error):
            raise ValueError(
                "This vehicle registration number already exists."
            ) from error

        if "FOREIGN KEY constraint failed" in str(error):
            raise ValueError(
                "The selected driver does not exist."
            ) from error

        raise ValueError(f"Could not update vehicle: {error}") from error


def update_vehicle_status(vehicle_id, status):
    if status not in VALID_VEHICLE_STATUSES:
        raise ValueError("Invalid vehicle status.")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE vehicles
                SET status = ?
                WHERE id = ?
                """,
                (status, vehicle_id),
            )

            if cursor.rowcount == 0:
                raise ValueError("Vehicle record was not found.")
