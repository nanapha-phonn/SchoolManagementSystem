import tkinter as tk
from tkinter import ttk, messagebox

from services.transport_staff_service import (
    create_transport_staff,
    update_transport_staff,
)


class TransportStaffForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        staff=None,
    ):
        super().__init__(master, padding=25)

        self.on_back = on_back
        self.on_saved = on_saved
        self.staff = staff
        self.variables = {}

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.staff:
            self.load_staff_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Transport Staff Information"
            if self.staff
            else "Transport Staff Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Register and manage bus drivers and transport attendants.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Transport Staff Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        fields = [
            ("Employee Number", "employee_no", 0, 0),
            ("First Name", "first_name", 0, 2),
            ("Last Name", "last_name", 1, 0),
            ("Phone Number", "phone", 1, 2),
            ("Email Address", "email", 2, 0),
            ("Role", "role", 2, 2),
            ("License Number", "license_number", 3, 0),
            ("Status", "status", 3, 2),
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

            if field_name == "role":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=["driver", "attendant"],
                    state="readonly",
                )
                variable.set("attendant")

            elif field_name == "status":
                widget = ttk.Combobox(
                    form,
                    textvariable=variable,
                    values=[
                        "active",
                        "inactive",
                        "resigned",
                        "terminated",
                    ],
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

        ttk.Label(
            form,
            text="License Number is optional for attendants.",
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

    def load_staff_data(self):
        for field, variable in self.variables.items():
            variable.set(
                self.staff.get(field) or ""
            )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Staff"
            if self.staff
            else "Register Staff"
        )

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_staff,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Staff Records",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_staff(self):
        staff_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        try:
            if self.staff:
                update_transport_staff(
                    self.staff["id"],
                    staff_data,
                )

                message = (
                    "Transport staff information updated successfully."
                )

            else:
                staff_id = create_transport_staff(staff_data)

                message = (
                    "Transport staff registered successfully.\n"
                    f"Staff ID: {staff_id}"
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
                "Invalid Staff Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Registration Error",
                f"Could not save transport staff:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR / BACK
    # --------------------------------------------------

    def clear_form(self):
        for variable in self.variables.values():
            variable.set("")

        self.variables["role"].set("attendant")
        self.variables["status"].set("active")

    def go_back(self):
        if self.on_back:
            self.on_back()
