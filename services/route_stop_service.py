import sqlite3
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.route_stop import RouteStop


def create_route_stop(stop_data):
    stop = RouteStop(**stop_data).validate()
    data = asdict(stop)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO route_stops (
                        route_id,
                        stop_name,
                        address,
                        stop_order,
                        pickup_time
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        data["route_id"],
                        data["stop_name"],
                        data["address"] or None,
                        data["stop_order"],
                        data["pickup_time"] or None,
                    ),
                )

                return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        message = str(error)

        if "UNIQUE constraint failed" in message:
            raise ValueError(
                "This stop order already exists on the selected route."
            ) from error

        if "FOREIGN KEY constraint failed" in message:
            raise ValueError(
                "The selected route does not exist."
            ) from error

        raise ValueError(
            f"Could not create route stop: {error}"
        ) from error


def get_route_stop(stop_id):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                rs.*,
                tr.route_code,
                tr.route_name
            FROM route_stops AS rs
            JOIN transport_routes AS tr
                ON rs.route_id = tr.id
            WHERE rs.id = ?
            """,
            (stop_id,),
        ).fetchone()

        return dict(row) if row else None


def get_route_stops(route_id):
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM route_stops
            WHERE route_id = ?
            ORDER BY stop_order
            """,
            (route_id,),
        ).fetchall()

        return [dict(row) for row in rows]


def update_route_stop(stop_id, stop_data):
    stop = RouteStop(**stop_data).validate()
    data = asdict(stop)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE route_stops
                    SET route_id = ?,
                        stop_name = ?,
                        address = ?,
                        stop_order = ?,
                        pickup_time = ?
                    WHERE id = ?
                    """,
                    (
                        data["route_id"],
                        data["stop_name"],
                        data["address"] or None,
                        data["stop_order"],
                        data["pickup_time"] or None,
                        stop_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Route stop record was not found.")

    except sqlite3.IntegrityError as error:
        message = str(error)

        if "UNIQUE constraint failed" in message:
            raise ValueError(
                "This stop order already exists on the selected route."
            ) from error

        if "FOREIGN KEY constraint failed" in message:
            raise ValueError(
                "The route does not exist, or this stop is referenced "
                "by a student transport assignment."
            ) from error

        raise ValueError(
            f"Could not update route stop: {error}"
        ) from error


def delete_route_stop(stop_id):
    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM route_stops
                    WHERE id = ?
                    """,
                    (stop_id,),
                )

                if cursor.rowcount == 0:
                    raise ValueError("Route stop record was not found.")

    except sqlite3.IntegrityError as error:
        raise ValueError(
            "This stop cannot be deleted because it is referenced "
            "by a student transport assignment."
        ) from error


def reorder_route_stops(route_id, ordered_stop_ids):
    """
    Reorder every stop belonging to a route.

    ordered_stop_ids must contain every stop ID for the route exactly once.
    The operation is atomic and normalizes stop_order to 1..N.
    """

    if isinstance(route_id, bool):
        raise ValueError("Route ID must be a positive integer.")

    try:
        parsed_route_id = int(route_id)
    except (TypeError, ValueError):
        raise ValueError("Route ID must be a positive integer.")

    if (
        parsed_route_id <= 0
        or str(route_id).strip() != str(parsed_route_id)
    ):
        raise ValueError("Route ID must be a positive integer.")

    if not isinstance(ordered_stop_ids, (list, tuple)):
        raise ValueError("Stop IDs must be provided as a list.")

    normalized_ids = []

    for stop_id in ordered_stop_ids:
        if isinstance(stop_id, bool):
            raise ValueError("Every stop ID must be a positive integer.")

        try:
            parsed_id = int(stop_id)
        except (TypeError, ValueError):
            raise ValueError(
                "Every stop ID must be a positive integer."
            )

        if (
            parsed_id <= 0
            or str(stop_id).strip() != str(parsed_id)
        ):
            raise ValueError(
                "Every stop ID must be a positive integer."
            )

        normalized_ids.append(parsed_id)

    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("Duplicate stop IDs are not allowed.")

    try:
        with closing(get_connection()) as connection:
            with connection:
                route = connection.execute(
                    """
                    SELECT id
                    FROM transport_routes
                    WHERE id = ?
                    """,
                    (parsed_route_id,),
                ).fetchone()

                if route is None:
                    raise ValueError("Transport route was not found.")

                rows = connection.execute(
                    """
                    SELECT id, stop_order
                    FROM route_stops
                    WHERE route_id = ?
                    ORDER BY stop_order
                    """,
                    (parsed_route_id,),
                ).fetchall()

                existing_ids = {row["id"] for row in rows}

                if set(normalized_ids) != existing_ids:
                    raise ValueError(
                        "The reorder request must include every stop "
                        "belonging to this route exactly once."
                    )

                if not normalized_ids:
                    return

                maximum_order = max(
                    row["stop_order"] for row in rows
                )

                # Move all existing positions above the current maximum.
                # This avoids conflicts with the UNIQUE(route_id, stop_order)
                # constraint while the final positions are assigned.
                offset = maximum_order + len(normalized_ids) + 1

                connection.execute(
                    """
                    UPDATE route_stops
                    SET stop_order = stop_order + ?
                    WHERE route_id = ?
                    """,
                    (offset, parsed_route_id),
                )

                # Assign normalized positions in the requested sequence.
                for position, stop_id in enumerate(
                    normalized_ids,
                    start=1,
                ):
                    connection.execute(
                        """
                        UPDATE route_stops
                        SET stop_order = ?
                        WHERE id = ? AND route_id = ?
                        """,
                        (
                            position,
                            stop_id,
                            parsed_route_id,
                        ),
                    )

    except sqlite3.IntegrityError as error:
        raise ValueError(
            f"Could not reorder route stops: {error}"
        ) from error
