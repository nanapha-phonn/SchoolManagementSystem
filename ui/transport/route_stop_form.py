import tkinter as tk
from tkinter import ttk, messagebox

from services.route_stop_service import (
    create_route_stop,
    update_route_stop,
)


class RouteStopForm(tk.Toplevel):

    def __init__(
        self,
        master,
        route_id,
        on_saved=None,
        stop=None,
        next_order=1,
    ):
        super().__init__(master)

        self.route_id = route_id
        self.on_saved = on_saved
        self.stop = stop
        self.next_order = next_order

        self.title(
            "Edit Route Stop" if self.stop else "Add Route Stop"
        )
        self.geometry("540x390")
        self.minsize(500, 350)
        self.transient(master.winfo_toplevel())

        self.variables = {}

        self.create_form()
        self.create_buttons()

        if self.stop:
            self.load_stop_data()
        else:
            self.variables["stop_order"].set(str(self.next_order))

        self.grab_set()
        self.focus_set()

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        container = ttk.LabelFrame(
            self,
            text="Route Stop Information",
            padding=20,
        )
        container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        container.columnconfigure(1, weight=1)

        fields = [
            ("Stop Name", "stop_name"),
            ("Address", "address"),
            ("Stop Order", "stop_order"),
            ("Pickup Time (HH:MM)", "pickup_time"),
        ]

        for row, (label_text, field_name) in enumerate(fields):
            ttk.Label(
                container,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=8,
                pady=12,
            )

            variable = tk.StringVar()
            self.variables[field_name] = variable

            ttk.Entry(
                container,
                textvariable=variable,
                width=35,
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                padx=8,
                pady=12,
            )

        ttk.Label(
            container,
            text="Use 24-hour time, for example 07:30. Leave blank if not specified.",
            font=("Segoe UI", 9),
            wraplength=350,
        ).grid(
            row=4,
            column=1,
            sticky="w",
            padx=8,
            pady=(0, 5),
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_stop_data(self):
        for field, variable in self.variables.items():
            variable.set(
                str(self.stop.get(field) or "")
            )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        save_text = (
            "Update Stop" if self.stop else "Save Stop"
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_stop,
        ).pack(side="right", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_stop(self):
        stop_data = {
            field: variable.get().strip()
            for field, variable in self.variables.items()
        }

        stop_data["route_id"] = self.route_id

        try:
            if self.stop:
                update_route_stop(
                    self.stop["id"],
                    stop_data,
                )

                message = "Route stop updated successfully."

            else:
                stop_id = create_route_stop(stop_data)

                message = (
                    "Route stop added successfully.\n"
                    f"Stop ID: {stop_id}"
                )

            messagebox.showinfo(
                "Success",
                message,
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

            self.destroy()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Route Stop Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Route Stop Error",
                f"Could not save route stop:\n{error}",
                parent=self,
            )
