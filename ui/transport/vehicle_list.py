import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.vehicle_service import (
    get_vehicles,
    update_vehicle_status,
)


class VehicleListFrame(ttk.Frame):

    def __init__(self, master, on_register, on_profile, on_edit):
        super().__init__(master, padding=25)

        self.on_register = on_register
        self.on_profile = on_profile
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_vehicles()

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Vehicle Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search, view and manage school vehicles.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search Vehicles:",
        ).pack(side="left", padx=(0, 10))

        entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35,
        )
        entry.pack(side="left", padx=5)
        entry.bind(
            "<Return>",
            lambda event: self.load_vehicles(),
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_vehicles,
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
        ).pack(side="left", padx=5)

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "registration_no",
            "vehicle_type",
            "model",
            "capacity",
            "driver",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "registration_no": "Registration No.",
            "vehicle_type": "Type",
            "model": "Model",
            "capacity": "Capacity",
            "driver": "Assigned Driver",
            "status": "Status",
        }

        widths = {
            "id": 50,
            "registration_no": 125,
            "vehicle_type": 90,
            "model": 140,
            "capacity": 80,
            "driver": 180,
            "status": 110,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )

        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind(
            "<Double-1>",
            lambda event: self.view_profile(),
        )

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Vehicle",
            command=self.on_register,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="View Profile",
            command=self.view_profile,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Vehicle",
            command=self.edit_vehicle,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_vehicles,
        ).pack(side="right", padx=4)

    def load_vehicles(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            vehicles = get_vehicles(self.search_var.get())

            for vehicle in vehicles:
                driver_name = "-"

                if vehicle.get("driver_id"):
                    driver_name = (
                        f'{vehicle.get("driver_first_name") or ""} '
                        f'{vehicle.get("driver_last_name") or ""}'
                    ).strip()

                    if not driver_name:
                        driver_name = (
                            vehicle.get("driver_employee_no") or "-"
                        )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        vehicle["id"],
                        vehicle["registration_no"],
                        vehicle.get("vehicle_type") or "-",
                        vehicle.get("model") or "-",
                        vehicle["capacity"],
                        driver_name,
                        vehicle["status"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load vehicle records:\n{error}",
                parent=self,
            )

    def get_selected_vehicle_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Vehicle Selected",
                "Please select a vehicle first.",
                parent=self,
            )
            return None

        values = self.tree.item(selection[0], "values")
        return int(values[0])

    def view_profile(self):
        vehicle_id = self.get_selected_vehicle_id()

        if vehicle_id is not None:
            self.on_profile(vehicle_id)

    def edit_vehicle(self):
        vehicle_id = self.get_selected_vehicle_id()

        if vehicle_id is not None:
            self.on_edit(vehicle_id)

    def change_status(self):
        vehicle_id = self.get_selected_vehicle_id()

        if vehicle_id is None:
            return

        current_values = self.tree.item(
            self.tree.selection()[0],
            "values",
        )
        current_status = current_values[6]

        new_status = simpledialog.askstring(
            "Change Vehicle Status",
            "Enter status: active, maintenance, or retired",
            initialvalue=current_status,
            parent=self,
        )

        if new_status is None:
            return

        new_status = new_status.strip().lower()

        try:
            update_vehicle_status(vehicle_id, new_status)

            messagebox.showinfo(
                "Success",
                "Vehicle status updated successfully.",
                parent=self,
            )

            self.load_vehicles()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Update Error",
                f"Could not update vehicle status:\n{error}",
                parent=self,
            )

    def clear_search(self):
        self.search_var.set("")
        self.load_vehicles()
