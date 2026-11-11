import tkinter as tk
from tkinter import ttk, messagebox

from services.transport_route_service import (
    create_transport_route,
    update_transport_route,
    get_transport_routes,
)
from services.vehicle_service import get_vehicles


class TransportRouteForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        route=None,
    ):
        super().__init__(master, padding=25)

        self.on_back = on_back
        self.on_saved = on_saved
        self.route = route

        self.variables = {}
        self.vehicle_choices = {"Unassigned": None}

        self.load_vehicle_options()
        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.route:
            self.load_route_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Bus Route"
            if self.route
            else "Bus Route Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Create and manage school transportation routes.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # VEHICLE OPTIONS
    # --------------------------------------------------

    def load_vehicle_options(self):
        self.vehicle_choices = {"Unassigned": None}

        try:
            vehicles = get_vehicles()
            routes = get_transport_routes()

            current_route_id = (
                self.route["id"] if self.route else None
            )

            current_vehicle_id = (
                self.route.get("vehicle_id") if self.route else None
            )

            used_vehicle_ids = {
                item["vehicle_id"]
                for item in routes
                if item.get("vehicle_id") is not None
                and item["id"] != current_route_id
                and item.get("status") == "active"
            }

            for vehicle in vehicles:
                vehicle_id = vehicle["id"]
                is_current_vehicle = (
                    vehicle_id == current_vehicle_id
                )

                if vehicle["status"] != "active" and not is_current_vehicle:
                    continue

                if (
                    vehicle_id in used_vehicle_ids
                    and not is_current_vehicle
                ):
                    continue

                label = (
                    f'{vehicle["registration_no"]} - '
                    f'{vehicle.get("vehicle_type") or "Vehicle"} - '
                    f'{vehicle.get("model") or "Unknown model"}'
                )

                if vehicle["status"] != "active":
                    label += f' ({vehicle["status"]})'

                self.vehicle_choices[label] = vehicle_id

        except Exception as error:
            messagebox.showerror(
                "Vehicle Loading Error",
                f"Could not load available vehicles:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Route Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        fields = [
            ("Route Code", "route_code", 0, 0),
            ("Route Name", "route_name", 0, 2),
            ("Status", "status", 1, 0),
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

            if field_name == "status":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=["active", "inactive"],
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

        # Vehicle assignment
        ttk.Label(
            form,
            text="Assigned Vehicle",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.vehicle_var = tk.StringVar(value="Unassigned")

        self.vehicle_combo = ttk.Combobox(
            form,
            textvariable=self.vehicle_var,
            values=list(self.vehicle_choices.keys()),
            state="readonly",
        )

        self.vehicle_combo.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

        # Description
        ttk.Label(
            form,
            text="Description",
        ).grid(
            row=2,
            column=0,
            sticky="nw",
            padx=8,
            pady=10,
        )

        self.description_text = tk.Text(
            form,
            height=4,
            width=50,
            font=("Segoe UI", 10),
            wrap="word",
        )

        self.description_text.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=8,
            pady=10,
        )

    # --------------------------------------------------
    # LOAD EXISTING ROUTE
    # --------------------------------------------------

    def load_route_data(self):
        for field, variable in self.variables.items():
            variable.set(
                str(self.route.get(field) or "")
            )

        self.description_text.insert(
            "1.0",
            self.route.get("description") or "",
        )

        current_vehicle_id = self.route.get("vehicle_id")
        selected_label = "Unassigned"

        if current_vehicle_id is not None:
            for label, vehicle_id in self.vehicle_choices.items():
                if vehicle_id == current_vehicle_id:
                    selected_label = label
                    break

        self.vehicle_var.set(selected_label)

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Route"
            if self.route
            else "Save Route"
        )

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_route,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Routes",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_route(self):
        selected_vehicle = self.vehicle_var.get()

        if selected_vehicle not in self.vehicle_choices:
            messagebox.showwarning(
                "Invalid Vehicle",
                "Please select a valid vehicle.",
                parent=self,
            )
            return

        route_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        route_data["description"] = self.description_text.get(
            "1.0",
            "end",
        ).strip()

        route_data["vehicle_id"] = self.vehicle_choices[
            selected_vehicle
        ]

        try:
            if self.route:
                update_transport_route(
                    self.route["id"],
                    route_data,
                )

                message = "Route information updated successfully."

            else:
                route_id = create_transport_route(route_data)

                message = (
                    "Bus route created successfully.\n"
                    f"Route ID: {route_id}"
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
                "Invalid Route Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Route Error",
                f"Could not save bus route:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR / BACK
    # --------------------------------------------------

    def clear_form(self):
        for variable in self.variables.values():
            variable.set("")

        self.variables["status"].set("active")
        self.vehicle_var.set("Unassigned")
        self.description_text.delete("1.0", "end")

    def go_back(self):
        if self.on_back:
            self.on_back()
