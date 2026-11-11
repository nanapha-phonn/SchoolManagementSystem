import tkinter as tk
from tkinter import ttk, messagebox

from services.route_stop_service import (
    get_route_stops,
    get_route_stop,
    create_route_stop,
    delete_route_stop,
    reorder_route_stops,
)

from ui.transport.route_stop_form import RouteStopForm


class TransportRouteProfile(ttk.Frame):

    def __init__(self, master, route, on_back, on_edit):
        super().__init__(master, padding=25)

        self.route = route
        self.on_back = on_back
        self.on_edit = on_edit
        self.stops = []

        self.create_header()
        self.create_route_details()
        self.create_stop_section()
        self.create_navigation_buttons()

        self.load_stops()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 15))

        ttk.Label(
            header,
            text="Bus Route Profile",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="View route information and manage pickup/drop-off stops.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # ROUTE DETAILS
    # --------------------------------------------------

    def create_route_details(self):
        container = ttk.LabelFrame(
            self,
            text="Route Information",
            padding=15,
        )
        container.pack(fill="x", pady=(0, 15))

        details = [
            ("Route Code", self.route.get("route_code")),
            ("Route Name", self.route.get("route_name")),
            (
                "Assigned Vehicle",
                self.route.get("vehicle_registration") or "Unassigned",
            ),
            ("Status", self.route.get("status")),
            ("Description", self.route.get("description")),
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
                padx=8,
                pady=8,
            )

            ttk.Label(
                container,
                text=str(value) if value not in (None, "") else "-",
                font=("Segoe UI", 10),
                wraplength=260,
            ).grid(
                row=row,
                column=column + 1,
                sticky="nw",
                padx=8,
                pady=8,
            )

        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

    # --------------------------------------------------
    # STOP SECTION
    # --------------------------------------------------

    def create_stop_section(self):
        section = ttk.LabelFrame(
            self,
            text="Route Stops",
            padding=12,
        )
        section.pack(fill="both", expand=True)

        table_frame = ttk.Frame(section)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "stop_order",
            "stop_name",
            "address",
            "pickup_time",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "stop_order": "Order",
            "stop_name": "Stop Name",
            "address": "Address",
            "pickup_time": "Pickup Time",
        }

        widths = {
            "id": 45,
            "stop_order": 65,
            "stop_name": 180,
            "address": 220,
            "pickup_time": 110,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )

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

        self.tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # Stop management controls.
        actions = ttk.Frame(section)
        actions.pack(fill="x", pady=(12, 0))

        ttk.Button(
            actions,
            text="Add Stop",
            command=self.add_stop,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Edit Stop",
            command=self.edit_stop,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Delete Stop",
            command=self.remove_stop,
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Move Up",
            command=self.move_stop_up,
        ).pack(side="right", padx=3)

        ttk.Button(
            actions,
            text="Move Down",
            command=self.move_stop_down,
        ).pack(side="right", padx=3)

        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_stop(),
        )

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def create_navigation_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=15)

        ttk.Button(
            buttons,
            text="Back to Routes",
            command=self.on_back,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Edit Route Information",
            command=self.on_edit,
        ).pack(side="right", padx=5)

    # --------------------------------------------------
    # LOAD STOPS
    # --------------------------------------------------

    def load_stops(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.stops = get_route_stops(self.route["id"])

            for stop in self.stops:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        stop["id"],
                        stop["stop_order"],
                        stop["stop_name"],
                        stop.get("address") or "-",
                        stop.get("pickup_time") or "-",
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load route stops:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTED STOP
    # --------------------------------------------------

    def get_selected_stop_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Stop Selected",
                "Please select a route stop first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    # --------------------------------------------------
    # ADD STOP
    # --------------------------------------------------

    def add_stop(self):
        next_order = (
            max(
                (stop["stop_order"] for stop in self.stops),
                default=0,
            ) + 1
        )

        RouteStopForm(
            self,
            route_id=self.route["id"],
            on_saved=self.load_stops,
            next_order=next_order,
        )

    # --------------------------------------------------
    # EDIT STOP
    # --------------------------------------------------

    def edit_stop(self):
        stop_id = self.get_selected_stop_id()

        if stop_id is None:
            return

        stop = get_route_stop(stop_id)

        if not stop:
            messagebox.showerror(
                "Stop Not Found",
                "The selected route stop could not be found.",
                parent=self,
            )
            self.load_stops()
            return

        RouteStopForm(
            self,
            route_id=self.route["id"],
            on_saved=self.load_stops,
            stop=stop,
        )

    # --------------------------------------------------
    # DELETE STOP
    # --------------------------------------------------

    def remove_stop(self):
        stop_id = self.get_selected_stop_id()

        if stop_id is None:
            return

        confirmed = messagebox.askyesno(
            "Delete Route Stop",
            "Are you sure you want to delete this stop?\n\n"
            "A stop referenced by a student transport assignment "
            "cannot be deleted.",
            parent=self,
        )

        if not confirmed:
            return

        try:
            delete_route_stop(stop_id)

            messagebox.showinfo(
                "Success",
                "Route stop deleted successfully.",
                parent=self,
            )

            self.load_stops()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Delete Stop",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Delete Error",
                f"Could not delete route stop:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # REORDER STOPS
    # --------------------------------------------------

    def move_selected_stop(self, direction):
        stop_id = self.get_selected_stop_id()

        if stop_id is None:
            return

        ordered_ids = [
            stop["id"]
            for stop in self.stops
        ]

        current_index = ordered_ids.index(stop_id)
        new_index = current_index + direction

        if new_index < 0 or new_index >= len(ordered_ids):
            return

        ordered_ids[current_index], ordered_ids[new_index] = (
            ordered_ids[new_index],
            ordered_ids[current_index],
        )

        try:
            reorder_route_stops(
                self.route["id"],
                ordered_ids,
            )

            self.load_stops()
            self.select_stop(stop_id)

        except ValueError as error:
            messagebox.showwarning(
                "Reorder Error",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Reorder Error",
                f"Could not reorder route stops:\n{error}",
                parent=self,
            )

    def move_stop_up(self):
        self.move_selected_stop(-1)

    def move_stop_down(self):
        self.move_selected_stop(1)

    def select_stop(self, stop_id):
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")

            if int(values[0]) == stop_id:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                return
