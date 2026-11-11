from dataclasses import dataclass
import re


VALID_VEHICLE_STATUSES = {
    "active",
    "maintenance",
    "retired",
}

VALID_VEHICLE_TYPES = {
    "bus",
    "minibus",
    "van",
    "other",
}


@dataclass
class Vehicle:
    registration_no: str
    capacity: int

    vehicle_type: str = ""
    model: str = ""
    status: str = "active"
    driver_id: int = None

    def validate(self):
        self.registration_no = self.registration_no.strip().upper()
        self.vehicle_type = self.vehicle_type.strip().lower()
        self.model = self.model.strip()
        self.status = self.status.strip().lower()

        if not self.registration_no:
            raise ValueError("Vehicle registration number is required.")

        if len(self.registration_no) > 30:
            raise ValueError(
                "Registration number cannot exceed 30 characters."
            )

        if not re.fullmatch(
            r"[A-Z0-9\-\s]+",
            self.registration_no
        ):
            raise ValueError(
                "Registration number contains invalid characters."
            )

        # Validate whole-number capacity without truncating decimals.
        if isinstance(self.capacity, bool):
            raise ValueError("Vehicle capacity must be a whole number.")

        try:
            capacity = int(self.capacity)
        except (TypeError, ValueError):
            raise ValueError("Vehicle capacity must be a whole number.")

        if str(self.capacity).strip() != str(capacity):
            raise ValueError("Vehicle capacity must be a whole number.")

        if capacity <= 0:
            raise ValueError("Vehicle capacity must be greater than zero.")

        if capacity > 500:
            raise ValueError("Vehicle capacity cannot exceed 500.")

        self.capacity = capacity

        if self.vehicle_type:
            if self.vehicle_type not in VALID_VEHICLE_TYPES:
                raise ValueError("Please select a valid vehicle type.")

        if len(self.model) > 100:
            raise ValueError("Vehicle model cannot exceed 100 characters.")

        if self.status not in VALID_VEHICLE_STATUSES:
            raise ValueError("Invalid vehicle status.")

        # Validate optional driver ID.
        if self.driver_id in (None, ""):
            self.driver_id = None
        else:
            if isinstance(self.driver_id, bool):
                raise ValueError("Driver ID must be a positive integer.")

            try:
                driver_id = int(self.driver_id)
            except (TypeError, ValueError):
                raise ValueError(
                    "Driver ID must be a positive integer."
                )

            if (
                driver_id <= 0
                or str(self.driver_id).strip() != str(driver_id)
            ):
                raise ValueError(
                    "Driver ID must be a positive integer."
                )

            self.driver_id = driver_id

        return self
