import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.transport_route import (
    TransportRoute,
    VALID_ROUTE_STATUSES,
)


def create_transport_route(route_data):
    route = TransportRoute(**route_data).validate()
    data = asdict(route)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO transport_routes (
                        route_code,
                        route_name,
                        description,
                        vehicle_id,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data["route_code"],
                        data["route_name"],
                        data["description"] or None,
                        data["vehicle_id"],
                        data["status"],
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        if "route_code" in str(error):
            raise ValueError(
                "This route code already exists."
            ) from error

        if "vehicle_id" in str(error):
            raise ValueError(
                "The selected vehicle does not exist."
            ) from error

        raise ValueError(
            f"Could not create route: {error}"
        ) from error


def get_transport_route(route_id):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                r.*,
                v.registration_no AS vehicle_registration
            FROM transport_routes AS r
            LEFT JOIN vehicles AS v
                ON r.vehicle_id = v.id
            WHERE r.id = ?
            """,
            (route_id,),
        ).fetchone()

        return dict(row) if row else None


def get_transport_routes(search=""):
    search = search.strip()

    with closing(get_connection()) as connection:
        if search:
            pattern = f"%{search}%"

            rows = connection.execute(
                """
                SELECT
                    r.*,
                    v.registration_no AS vehicle_registration
                FROM transport_routes AS r
                LEFT JOIN vehicles AS v
                    ON r.vehicle_id = v.id
                WHERE r.route_code LIKE ?
                   OR r.route_name LIKE ?
                   OR r.description LIKE ?
                   OR v.registration_no LIKE ?
                ORDER BY r.route_code
                """,
                (pattern, pattern, pattern, pattern),
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    r.*,
                    v.registration_no AS vehicle_registration
                FROM transport_routes AS r
                LEFT JOIN vehicles AS v
                    ON r.vehicle_id = v.id
                ORDER BY r.route_code
                """
            ).fetchall()

        return [dict(row) for row in rows]


def search_transport_routes(search):
    return get_transport_routes(search)


def update_transport_route(route_id, route_data):
    route = TransportRoute(**route_data).validate()
    data = asdict(route)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE transport_routes
                    SET route_code = ?,
                        route_name = ?,
                        description = ?,
                        vehicle_id = ?,
                        status = ?
                    WHERE id = ?
                    """,
                    (
                        data["route_code"],
                        data["route_name"],
                        data["description"] or None,
                        data["vehicle_id"],
                        data["status"],
                        route_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Route record was not found.")

    except sqlite3.IntegrityError as error:
        if "route_code" in str(error):
            raise ValueError(
                "This route code already exists."
            ) from error

        if "vehicle_id" in str(error):
            raise ValueError(
                "The selected vehicle does not exist."
            ) from error

        raise ValueError(
            f"Could not update route: {error}"
        ) from error


def update_transport_route_status(route_id, status):
    if status not in VALID_ROUTE_STATUSES:
        raise ValueError("Invalid route status.")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE transport_routes
                SET status = ?
                WHERE id = ?
                """,
                (status, route_id),
            )

            if cursor.rowcount == 0:
                raise ValueError("Route record was not found.")
