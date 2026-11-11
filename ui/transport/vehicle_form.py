import tkinter as tk
from tkinter import ttk, messagebox

from services.vehicle_service import (
    create_vehicle,
    update_vehicle,
)
from services.transport_staff_service import (
    get_transport_staff,
    get_transport_staff_list,
)


class VehicleForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        vehicle=None,
    ):
        super().__init__(master, padding=25)

        self.on_back = on_back
        self.on_saved = on_saved
        self.vehicle = vehicle

        self.variables = {}
        self.driver_choices = {"Unassigned": None}

        self.load_driver_options()
        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.vehicle:
            self.load_vehicle_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Vehicle Information"
            if self.vehicle
            else "Vehicle Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Register and manage school transportation vehicles.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # DRIVER OPTIONS
    # --------------------------------------------------

    def load_driver_options(self):
        self.driver_choices = {"Unassigned": None}

        try:
            staff_list = get_transport_staff_list()

            for staff in staff_list:
                if (
                    staff["role"] == "driver"
                    and staff["status"] == "active"
                ):
                    label = (
                        f'{staff["employee_no"]} - '
                        f'{staff["first_name"]} {staff["last_name"]}'
                    )
                    self.driver_choices[label] = staff["id"]

            # Preserve visibility of an already assigned driver,
            # even if that driver's status has changed.
            if self.vehicle and self.vehicle.get("driver_id"):
                current_driver_id = self.vehicle["driver_id"]
                current_driver = get_transport_staff(current_driver_id)

                if current_driver:
                    label = (
                        f'{current_driver["employee_no"]} - '
                        f'{current_driver["first_name"]} '
                        f'{current_driver["last_name"]}'
                    )

                    if current_driver["status"] != "active":
                        label += " (Inactive - reassign or unassign)"

                    self.driver_choices[label] = current_driver_id

        except Exception as error:
            messagebox.showerror(
                "Driver Loading Error",
                f"Could not load transport drivers:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Vehicle Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        fields = [
            ("Registration Number", "registration_no", 0, 0),
            ("Vehicle Type", "vehicle_type", 0, 2),
            ("Model", "model", 1, 0),
            ("Passenger Capacity", "capacity", 1, 2),
            ("Status", "status", 2, 0),
        ]

        for label_text, field_name, row, column in fields:
            ttk.Label(
                form,
                text=label_text,
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=8,
                pady=10,
            )

            variable = tk.StringVar()
            self.variables[field_name] = variable

            if field_name == "vehicle_type":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=["", "bus", "minibus", "van", "other"],
                    state="readonly",
                )

            elif field_name == "status":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=["active", "maintenance", "retired"],
                    state="readonly",
                )
                variable.set("active")

            else:
                widget = ttk.Entry(
                    form,
                    textvariable=variable,
                    width=30,
                )

            widget.grid(
                row=row,
                column=column + 1,
                sticky="ew",
                padx=8,
                pady=10,
            )

        # Driver assignment
        ttk.Label(
            form,
            text="Assigned Driver",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.driver_var = tk.StringVar(value="Unassigned")

        self.driver_combo = ttk.Combobox(
            form,
            textvariable=self.driver_var,
            values=list(self.driver_choices.keys()),
            state="readonly",
        )

        self.driver_combo.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        ttk.Label(
            form,
            text="Only active transport staff with the driver role can be assigned.",
            font=("Segoe UI", 9),
        ).grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 5),
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_vehicle_data(self):
        for field, variable in self.variables.items():
            variable.set(
                str(self.vehicle.get(field) or "")
            )

        current_driver_id = self.vehicle.get("driver_id")

        selected_label = "Unassigned"

        if current_driver_id is not None:
            for label, driver_id in self.driver_choices.items():
                if driver_id == current_driver_id:
                    selected_label = label
                    break

        self.driver_var.set(selected_label)

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Vehicle"
            if self.vehicle
            else "Save Vehicle"
        )

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_vehicle,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Vehicles",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_vehicle(self):
        vehicle_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        selected_driver = self.driver_var.get()

        if selected_driver not in self.driver_choices:
            messagebox.showwarning(
                "Invalid Driver",
                "Please select a valid driver.",
                parent=self,
            )
            return

        vehicle_data["driver_id"] = self.driver_choices[
            selected_driver
        ]

        try:
            if self.vehicle:
                update_vehicle(
                    self.vehicle["id"],
                    vehicle_data,
                )
                message = "Vehicle information updated successfully."

            else:
                vehicle_id = create_vehicle(vehicle_data)
                message = (
                    "Vehicle registered successfully.\n"
                    f"Vehicle ID: {vehicle_id}"
                )

            messagebox.showinfo(
                "Success",
                message,
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Vehicle Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Vehicle Error",
                f"Could not save vehicle:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR / BACK
    # --------------------------------------------------

    def clear_form(self):
        for field, variable in self.variables.items():
            variable.set("")

        self.variables["status"].set("active")
        self.driver_var.set("Unassigned")

    def go_back(self):
        if self.on_back:
            self.on_back()
