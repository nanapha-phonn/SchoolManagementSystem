import tkinter as tk
from tkinter import ttk, messagebox

from services.academic_year_service import (
    get_academic_years,
    set_current_academic_year,
)


class AcademicYearListFrame(ttk.Frame):

    def __init__(self, master, on_create, on_edit, *, user):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or user.get("id") is None:
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.can_configure = user.get("role") == "admin"
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_academic_years()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Academic Year Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Create, search, edit and manage academic years. "
                "Only one academic year can be current."
            ),
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search Academic Years:"
        ).pack(side="left", padx=(0, 10))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_academic_years()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_academic_years
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "name",
            "start_date",
            "end_date",
            "is_current",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "id": "ID",
            "name": "Academic Year",
            "start_date": "Start Date",
            "end_date": "End Date",
            "is_current": "Current",
        }

        widths = {
            "id": 65,
            "name": 180,
            "start_date": 150,
            "end_date": 150,
            "is_current": 110,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column]
            )

            self.tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_academic_year()
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        if self.can_configure:
            ttk.Button(
                actions,
                text="Create Academic Year",
                command=self.on_create
            ).pack(side="left", padx=4)

            ttk.Button(
                actions,
                text="Edit Academic Year",
                command=self.edit_academic_year
            ).pack(side="left", padx=4)

            ttk.Button(
                actions,
                text="Set as Current",
                command=self.set_current
            ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_academic_years
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_academic_years(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            academic_years = get_academic_years(
                self.search_var.get(),
                actor_user_id=self.user["id"]
            )

            for year in academic_years:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        year["id"],
                        year["name"],
                        year["start_date"],
                        year["end_date"],
                        "Yes" if year["is_current"] else "No",
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load academic years:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_academic_year(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select an academic year first.",
                parent=self
            )
            return None

        values = self.tree.item(
            selection[0],
            "values"
        )

        return {
            "id": int(values[0]),
            "name": values[1],
            "is_current": values[4] == "Yes",
        }

    # --------------------------------------------------
    # EDIT
    # --------------------------------------------------

    def edit_academic_year(self):
        if not self.can_configure:
            return

        year = self.get_selected_academic_year()

        if year is not None:
            self.on_edit(year["id"])

    # --------------------------------------------------
    # CURRENT ACADEMIC YEAR
    # --------------------------------------------------

    def set_current(self):
        if not self.can_configure:
            return

        year = self.get_selected_academic_year()

        if year is None:
            return

        if year["is_current"]:
            messagebox.showinfo(
                "Already Current",
                "This is already the current academic year.",
                parent=self
            )
            return

        confirmed = messagebox.askyesno(
            "Set Current Academic Year",
            (
                f"Set {year['name']} as the current academic year?\n\n"
                "The previously current academic year will be unset."
            ),
            parent=self
        )

        if not confirmed:
            return

        try:
            set_current_academic_year(
                year["id"],
                actor_user_id=self.user["id"]
            )

            messagebox.showinfo(
                "Success",
                f"{year['name']} is now the current academic year.",
                parent=self
            )

            self.load_academic_years()

        except ValueError as error:
            messagebox.showwarning(
                "Update Failed",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not change the current academic year:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR SEARCH
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_academic_years()
