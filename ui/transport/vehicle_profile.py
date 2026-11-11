from tkinter import ttk


class VehicleProfile(ttk.Frame):

    def __init__(self, master, vehicle, on_back, on_edit):
        super().__init__(master, padding=25)

        self.vehicle = vehicle
        self.on_back = on_back
        self.on_edit = on_edit

        self.create_header()
        self.create_profile()

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Vehicle Profile",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Complete vehicle information and driver assignment.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    def create_profile(self):
        container = ttk.LabelFrame(
            self,
            text="Vehicle Information",
            padding=20,
        )
        container.pack(fill="both", expand=True)

        driver_name = "-"

        if self.vehicle.get("driver_id"):
            driver_name = (
                f'{self.vehicle.get("driver_first_name") or ""} '
                f'{self.vehicle.get("driver_last_name") or ""}'
            ).strip()

        if not driver_name:
            driver_name = (
                self.vehicle.get("driver_employee_no") or "-"
            )

        details = [
            ("Vehicle ID", self.vehicle.get("id")),
            ("Registration Number", self.vehicle.get("registration_no")),
            ("Vehicle Type", self.vehicle.get("vehicle_type")),
            ("Model", self.vehicle.get("model")),
            ("Passenger Capacity", self.vehicle.get("capacity")),
            ("Assigned Driver", driver_name),
            ("Driver Employee Number", self.vehicle.get("driver_employee_no")),
            ("Status", self.vehicle.get("status")),
            ("Registration Date", self.vehicle.get("created_at")),
        ]

        for index, (label, value) in enumerate(details):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(
                container,
                text=f"{label}:",
                font=("Segoe UI", 10, "bold"),
            ).grid(
                row=row,
                column=column,
                sticky="nw",
                padx=10,
                pady=12,
            )

            ttk.Label(
                container,
                text=str(value) if value not in (None, "") else "-",
                font=("Segoe UI", 10),
                wraplength=280,
            ).grid(
                row=row,
                column=column + 1,
                sticky="nw",
                padx=10,
                pady=12,
            )

        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        ttk.Button(
            buttons,
            text="Back to Vehicles",
            command=self.on_back,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Edit Vehicle",
            command=self.on_edit,
        ).pack(side="right", padx=5)
