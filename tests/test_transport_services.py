import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from services.vehicle_service import (
    create_vehicle,
    get_vehicle,
    get_vehicles,
    update_vehicle,
    update_vehicle_status,
)
from services.transport_staff_service import (
    create_transport_staff,
    get_transport_staff,
    get_transport_staff_list,
    update_transport_staff_status,
)
from services.transport_route_service import (
    create_transport_route,
    get_transport_route,
    get_transport_routes,
    update_transport_route_status,
)
from services.route_stop_service import (
    create_route_stop,
    get_route_stop,
    get_route_stops,
    update_route_stop,
    delete_route_stop,
)
from services.student_transport_assignment_service import (
    create_student_transport_assignment,
    get_student_transport_assignment,
    get_student_transport_assignments,
    update_student_transport_assignment_status,
)


class TransportServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "transport_test.db"

        self.db_patch = patch.object(
            database_module,
            "DB_PATH",
            str(self.db_path),
        )
        self.db_patch.start()

        database_module.initialize_database()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def create_student(self, admission_no, status="active"):
        with closing(database_module.get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        admission_no,
                        first_name,
                        last_name,
                        status
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (admission_no, "Test", "Student", status),
                )
                return cursor.lastrowid

    def create_route(self, code="TEST-ROUTE", vehicle_id=None):
        return create_transport_route({
            "route_code": code,
            "route_name": "Test Transport Route",
            "vehicle_id": vehicle_id,
        })

    def create_stop(self, route_id, name, order):
        return create_route_stop({
            "route_id": route_id,
            "stop_name": name,
            "stop_order": order,
        })

    def test_vehicle_crud_search_and_status(self):
        vehicle_id = create_vehicle({
            "registration_no": "TEST-001",
            "vehicle_type": "bus",
            "model": "Test Bus",
            "capacity": 30,
        })

        vehicle = get_vehicle(vehicle_id)

        self.assertEqual(vehicle["registration_no"], "TEST-001")
        self.assertEqual(vehicle["capacity"], 30)

        self.assertEqual(len(get_vehicles("TEST-001")), 1)

        update_vehicle(vehicle_id, {
            "registration_no": "TEST-001",
            "vehicle_type": "bus",
            "model": "Updated Bus",
            "capacity": 35,
            "status": "active",
        })

        self.assertEqual(
            get_vehicle(vehicle_id)["model"],
            "Updated Bus",
        )

        update_vehicle_status(vehicle_id, "maintenance")

        self.assertEqual(
            get_vehicle(vehicle_id)["status"],
            "maintenance",
        )

    def test_vehicle_duplicate_registration_rejected(self):
        data = {
            "registration_no": "DUPLICATE-001",
            "capacity": 20,
        }

        create_vehicle(data)

        with self.assertRaises(ValueError):
            create_vehicle(data)

    def test_transport_staff_crud_search_and_status(self):
        staff_id = create_transport_staff({
            "employee_no": "DRIVER-001",
            "first_name": "Test",
            "last_name": "Driver",
            "role": "driver",
            "license_number": "LIC-001",
        })

        staff = get_transport_staff(staff_id)

        self.assertEqual(staff["employee_no"], "DRIVER-001")
        self.assertEqual(staff["role"], "driver")

        self.assertEqual(
            len(get_transport_staff_list("DRIVER-001")),
            1,
        )

        update_transport_staff_status(staff_id, "inactive")

        self.assertEqual(
            get_transport_staff(staff_id)["status"],
            "inactive",
        )

    def test_route_crud_search_and_status(self):
        vehicle_id = create_vehicle({
            "registration_no": "ROUTE-BUS-001",
            "capacity": 30,
        })

        route_id = create_transport_route({
            "route_code": "ROUTE-TEST-001",
            "route_name": "Central Route",
            "description": "Test route",
            "vehicle_id": vehicle_id,
        })

        route = get_transport_route(route_id)

        self.assertEqual(route["route_code"], "ROUTE-TEST-001")
        self.assertEqual(route["vehicle_registration"], "ROUTE-BUS-001")

        self.assertEqual(
            len(get_transport_routes("Central Route")),
            1,
        )

        update_transport_route_status(route_id, "inactive")

        self.assertEqual(
            get_transport_route(route_id)["status"],
            "inactive",
        )

    def test_route_stop_creation_order_update_and_delete(self):
        route_id = self.create_route()

        first_id = self.create_stop(route_id, "First Stop", 1)
        second_id = self.create_stop(route_id, "Second Stop", 2)

        stops = get_route_stops(route_id)

        self.assertEqual(len(stops), 2)
        self.assertEqual(stops[0]["id"], first_id)
        self.assertEqual(stops[1]["id"], second_id)

        update_route_stop(second_id, {
            "route_id": route_id,
            "stop_name": "Updated Second Stop",
            "stop_order": 3,
        })

        updated = get_route_stop(second_id)

        self.assertEqual(updated["stop_name"], "Updated Second Stop")
        self.assertEqual(updated["stop_order"], 3)

        delete_route_stop(first_id)

        self.assertIsNone(get_route_stop(first_id))

    def test_duplicate_stop_order_rejected(self):
        route_id = self.create_route()

        self.create_stop(route_id, "First Stop", 1)

        with self.assertRaises(ValueError):
            self.create_stop(route_id, "Duplicate Stop", 1)

    def test_assignment_creation_search_and_status(self):
        student_id = self.create_student("ASSIGN-001")
        route_id = self.create_route()

        pickup_id = self.create_stop(route_id, "Pickup", 1)
        dropoff_id = self.create_stop(route_id, "Dropoff", 2)

        assignment_id = create_student_transport_assignment({
            "student_id": student_id,
            "route_id": route_id,
            "pickup_stop_id": pickup_id,
            "dropoff_stop_id": dropoff_id,
            "start_date": "2026-11-02",
        })

        assignment = get_student_transport_assignment(assignment_id)

        self.assertEqual(assignment["student_id"], student_id)
        self.assertEqual(assignment["route_id"], route_id)
        self.assertEqual(assignment["pickup_stop_name"], "Pickup")
        self.assertEqual(assignment["dropoff_stop_name"], "Dropoff")

        self.assertEqual(len(get_student_transport_assignments()), 1)
        self.assertEqual(
            len(get_student_transport_assignments("ASSIGN-001")),
            1,
        )

        update_student_transport_assignment_status(
            assignment_id,
            "cancelled",
        )

        self.assertEqual(
            get_student_transport_assignment(assignment_id)["status"],
            "cancelled",
        )

    def test_one_active_assignment_per_student(self):
        student_id = self.create_student("ASSIGN-002")
        route1 = self.create_route("ACTIVE-ROUTE-1")
        route2 = self.create_route("ACTIVE-ROUTE-2")

        create_student_transport_assignment({
            "student_id": student_id,
            "route_id": route1,
            "start_date": "2026-11-02",
        })

        with self.assertRaises(ValueError):
            create_student_transport_assignment({
                "student_id": student_id,
                "route_id": route2,
                "start_date": "2026-11-02",
            })

    def test_stop_from_another_route_rejected(self):
        student_id = self.create_student("ASSIGN-003")

        route1 = self.create_route("STOP-ROUTE-1")
        route2 = self.create_route("STOP-ROUTE-2")

        wrong_stop = self.create_stop(route2, "Wrong Route Stop", 1)

        with self.assertRaises(ValueError):
            create_student_transport_assignment({
                "student_id": student_id,
                "route_id": route1,
                "pickup_stop_id": wrong_stop,
                "start_date": "2026-11-02",
            })

    def test_vehicle_capacity_enforced(self):
        student1 = self.create_student("CAPACITY-001")
        student2 = self.create_student("CAPACITY-002")

        vehicle_id = create_vehicle({
            "registration_no": "CAPACITY-BUS",
            "capacity": 1,
        })

        route_id = self.create_route(
            "CAPACITY-ROUTE",
            vehicle_id,
        )

        create_student_transport_assignment({
            "student_id": student1,
            "route_id": route_id,
            "start_date": "2026-11-02",
        })

        with self.assertRaises(ValueError):
            create_student_transport_assignment({
                "student_id": student2,
                "route_id": route_id,
                "start_date": "2026-11-02",
            })

    def test_assigned_stops_cannot_be_deleted(self):
        student_id = self.create_student("ASSIGN-004")
        route_id = self.create_route()

        pickup_id = self.create_stop(route_id, "Assigned Pickup", 1)
        dropoff_id = self.create_stop(route_id, "Assigned Dropoff", 2)

        create_student_transport_assignment({
            "student_id": student_id,
            "route_id": route_id,
            "pickup_stop_id": pickup_id,
            "dropoff_stop_id": dropoff_id,
            "start_date": "2026-11-02",
        })

        with self.assertRaises(ValueError):
            delete_route_stop(pickup_id)

        with self.assertRaises(ValueError):
            delete_route_stop(dropoff_id)

        self.assertIsNotNone(get_route_stop(pickup_id))
        self.assertIsNotNone(get_route_stop(dropoff_id))


if __name__ == "__main__":
    unittest.main()
