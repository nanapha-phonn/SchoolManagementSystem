import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from services.transport_staff_service import (
    get_transport_staff_list,
    update_transport_staff_status,
)


class TransportStaffListFrame(ttk.Frame):

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

        self.load_staff()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Transport Staff Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search, view and manage drivers and attendants.",
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
            text="Search Transport Staff:",
        ).pack(side="left", padx=(0, 10))

        entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35,
        )
        entry.pack(side="left", padx=5)

        entry.bind(
            "<Return>",
            lambda event: self.load_staff(),
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_staff,
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # STAFF TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "employee_no",
            "name",
            "role",
            "phone",
            "license_number",
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
            "employee_no": "Employee No.",
            "name": "Staff Name",
            "role": "Role",
            "phone": "Phone",
            "license_number": "License No.",
            "status": "Status",
        }

        widths = {
            "id": 50,
            "employee_no": 130,
            "name": 170,
            "role": 100,
            "phone": 120,
            "license_number": 130,
            "status": 110,
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
            text="Register Staff",
            command=self.on_register,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="View Profile",
            command=self.view_profile,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Staff",
            command=self.edit_staff,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_staff,
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_staff(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            staff_list = get_transport_staff_list(
                self.search_var.get()
            )

            for staff in staff_list:
                full_name = (
                    f'{staff["first_name"]} '
                    f'{staff["last_name"]}'
                )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        staff["id"],
                        staff["employee_no"],
                        full_name,
                        staff["role"],
                        staff.get("phone") or "-",
                        staff.get("license_number") or "-",
                        staff["status"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load transport staff records:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_staff_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Staff Selected",
                "Please select a transport staff record first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    def view_profile(self):
        staff_id = self.get_selected_staff_id()

        if staff_id is not None:
            self.on_profile(staff_id)

    def edit_staff(self):
        staff_id = self.get_selected_staff_id()

        if staff_id is not None:
            self.on_edit(staff_id)

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def change_status(self):
        staff_id = self.get_selected_staff_id()

        if staff_id is None:
            return

        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, "values")
        current_status = values[6]

        new_status = simpledialog.askstring(
            "Change Transport Staff Status",
            "Enter status: active, inactive, resigned, or terminated",
            initialvalue=current_status,
            parent=self,
        )

        if new_status is None:
            return

        new_status = new_status.strip().lower()

        try:
            update_transport_staff_status(
                staff_id,
                new_status,
            )

            messagebox.showinfo(
                "Success",
                "Transport staff status updated successfully.",
                parent=self,
            )

            self.load_staff()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Update Error",
                f"Could not update transport staff status:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SEARCH CLEAR
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_staff()
