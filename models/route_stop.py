from dataclasses import dataclass
import re


@dataclass
class RouteStop:
    route_id: int
    stop_name: str
    stop_order: int

    address: str = ""
    pickup_time: str = ""

    def validate(self):
        # Validate route ID
        if isinstance(self.route_id, bool):
            raise ValueError("Route ID must be a positive integer.")

        try:
            route_id = int(self.route_id)
        except (TypeError, ValueError):
            raise ValueError("Route ID must be a positive integer.")

        if (
            route_id <= 0
            or str(self.route_id).strip() != str(route_id)
        ):
            raise ValueError("Route ID must be a positive integer.")

        self.route_id = route_id

        # Normalize text fields
        self.stop_name = self.stop_name.strip()
        self.address = self.address.strip()
        self.pickup_time = self.pickup_time.strip()

        # Validate stop name
        if not self.stop_name:
            raise ValueError("Stop name is required.")

        if len(self.stop_name) > 100:
            raise ValueError("Stop name cannot exceed 100 characters.")

        # Validate address
        if len(self.address) > 250:
            raise ValueError("Address cannot exceed 250 characters.")

        # Validate stop order
        if isinstance(self.stop_order, bool):
            raise ValueError("Stop order must be a positive integer.")

        try:
            stop_order = int(self.stop_order)
        except (TypeError, ValueError):
            raise ValueError("Stop order must be a positive integer.")

        if (
            stop_order <= 0
            or str(self.stop_order).strip() != str(stop_order)
        ):
            raise ValueError("Stop order must be a positive integer.")

        self.stop_order = stop_order

        # Validate pickup time using strict 24-hour HH:MM format
        if self.pickup_time:
            if not re.fullmatch(
                r"(?:[01]\d|2[0-3]):[0-5]\d",
                self.pickup_time
            ):
                raise ValueError(
                    "Pickup time must use the HH:MM format (24-hour clock)."
                )

        return self
