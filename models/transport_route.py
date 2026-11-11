from dataclasses import dataclass


VALID_ROUTE_STATUSES = {
    "active",
    "inactive",
}


@dataclass
class TransportRoute:
    route_code: str
    route_name: str

    description: str = ""
    vehicle_id: int = None
    status: str = "active"

    def validate(self):
        self.route_code = self.route_code.strip().upper()
        self.route_name = self.route_name.strip()
        self.description = self.description.strip()
        self.status = self.status.strip().lower()

        if not self.route_code:
            raise ValueError("Route code is required.")

        if len(self.route_code) > 30:
            raise ValueError("Route code cannot exceed 30 characters.")

        if not self.route_code.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Route code contains invalid characters.")

        if not self.route_name:
            raise ValueError("Route name is required.")

        if len(self.route_name) > 100:
            raise ValueError("Route name cannot exceed 100 characters.")

        if len(self.description) > 500:
            raise ValueError("Description cannot exceed 500 characters.")

        if self.vehicle_id is not None:
            if isinstance(self.vehicle_id, bool):
                raise ValueError("Vehicle ID must be a positive integer.")

            try:
                converted_id = int(self.vehicle_id)
            except (TypeError, ValueError):
                raise ValueError("Vehicle ID must be a positive integer.")

            if converted_id <= 0:
                raise ValueError("Vehicle ID must be a positive integer.")

            if str(self.vehicle_id).strip() != str(converted_id):
                raise ValueError("Vehicle ID must be a whole number.")

            self.vehicle_id = converted_id

        if self.status not in VALID_ROUTE_STATUSES:
            raise ValueError("Route status must be active or inactive.")

        return self
