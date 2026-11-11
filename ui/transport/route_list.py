import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.transport_route_service import (
    get_transport_routes,
    update_transport_route_status,
)


class TransportRouteListFrame(ttk.Frame):

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

        self.load_routes()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Bus Route Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Create, search, view and manage school bus routes.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search Routes:",
        ).pack(side="left", padx=(0, 10))

        entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35,
        )
        entry.pack(side="left", padx=5)

        entry.bind(
            "<Return>",
            lambda event: self.load_routes(),
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_routes,
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # ROUTE TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "route_code",
            "route_name",
            "description",
            "vehicle",
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
            "route_code": "Route Code",
            "route_name": "Route Name",
            "description": "Description",
            "vehicle": "Assigned Vehicle",
            "status": "Status",
        }

        widths = {
            "id": 50,
            "route_code": 120,
            "route_name": 170,
            "description": 220,
            "vehicle": 145,
            "status": 100,
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

        self.tree.bind(
            "<Double-1>",
            lambda event: self.view_profile(),
        )

    # --------------------------------------------------
    # ACTION BUTTONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Route",
            command=self.on_register,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="View Route",
            command=self.view_profile,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Route",
            command=self.edit_route,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_routes,
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD ROUTES
    # --------------------------------------------------

    def load_routes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            routes = get_transport_routes(
                self.search_var.get()
            )

            for route in routes:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        route["id"],
                        route["route_code"],
                        route["route_name"],
                        route.get("description") or "-",
                        route.get("vehicle_registration") or "Unassigned",
                        route["status"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load bus routes:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_route_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Route Selected",
                "Please select a bus route first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    def view_profile(self):
        route_id = self.get_selected_route_id()

        if route_id is not None:
            self.on_profile(route_id)

    def edit_route(self):
        route_id = self.get_selected_route_id()

        if route_id is not None:
            self.on_edit(route_id)

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def change_status(self):
        route_id = self.get_selected_route_id()

        if route_id is None:
            return

        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, "values")
        current_status = values[5]

        new_status = simpledialog.askstring(
            "Change Route Status",
            "Enter status: active or inactive",
            initialvalue=current_status,
            parent=self,
        )

        if new_status is None:
            return

        new_status = new_status.strip().lower()

        try:
            update_transport_route_status(
                route_id,
                new_status,
            )

            messagebox.showinfo(
                "Success",
                "Route status updated successfully.",
                parent=self,
            )

            self.load_routes()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Update Error",
                f"Could not update route status:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SEARCH CLEAR
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_routes()
