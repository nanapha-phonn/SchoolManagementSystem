import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import get_classes
from services.academic_year_service import get_academic_years

from services.grading_scheme_service import (
    get_grading_schemes,
    activate_grading_scheme,
    archive_grading_scheme,
)


class GradingSchemeListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create=None,
        on_edit=None,
        on_manage_bands=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit
        self.on_manage_bands = on_manage_bands

        self.search_var = tk.StringVar()
        self.class_var = tk.StringVar(value="All")
        self.academic_year_var = tk.StringVar(value="All")
        self.status_var = tk.StringVar(value="All")

        self.class_id_by_label = {"All": None}
        self.academic_year_id_by_label = {"All": None}

        self.create_widgets()
        self.load_class_options()
        self.load_academic_year_options()
        self.load_grading_schemes()

    # --------------------------------------------------
    # WIDGETS
    # --------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="Grading Scheme Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Create Grading Scheme",
            command=self.create_grading_scheme,
        ).pack(side="right")

        ttk.Label(
            self,
            text=(
                "Manage configurable grading schemes by class and academic "
                "year. Each class and academic year can have only one active "
                "scheme. Schemes are versioned, and active or archived "
                "schemes preserve their grade-band history."
            ),
            font=("Segoe UI", 10),
            wraplength=950,
        ).pack(anchor="w", pady=(0, 18))

        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=12,
        )
        filters.pack(fill="x", pady=(0, 12))

        ttk.Label(
            filters,
            text="Search:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=28,
        )
        search_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=5,
            pady=5,
        )
        search_entry.bind(
            "<Return>",
            lambda event: self.load_grading_schemes(),
        )

        ttk.Label(
            filters,
            text="Class:",
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(15, 5),
            pady=5,
        )

        self.class_combo = ttk.Combobox(
            filters,
            textvariable=self.class_var,
            state="readonly",
            width=22,
        )
        self.class_combo.grid(
            row=0,
            column=3,
            sticky="w",
            padx=5,
            pady=5,
        )
        self.class_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_grading_schemes(),
        )

        ttk.Label(
            filters,
            text="Academic Year:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5,
        )

        self.academic_year_combo = ttk.Combobox(
            filters,
            textvariable=self.academic_year_var,
            state="readonly",
            width=27,
        )
        self.academic_year_combo.grid(
            row=1,
            column=1,
            sticky="w",
            padx=5,
            pady=5,
        )
        self.academic_year_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_grading_schemes(),
        )

        ttk.Label(
            filters,
            text="Status:",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(15, 5),
            pady=5,
        )

        self.status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=("All", "Draft", "Active", "Archived"),
            state="readonly",
            width=15,
        )
        self.status_combo.grid(
            row=1,
            column=3,
            sticky="w",
            padx=5,
            pady=5,
        )
        self.status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_grading_schemes(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_grading_schemes,
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(15, 5),
            pady=5,
        )

        ttk.Button(
            filters,
            text="Reset Filters",
            command=self.reset_filters,
        ).grid(
            row=1,
            column=4,
            sticky="w",
            padx=(15, 5),
            pady=5,
        )

        filters.columnconfigure(1, weight=1)

        self.create_table()
        self.create_actions()

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "name",
            "class_name",
            "academic_year_name",
            "version_no",
            "band_count",
            "status",
            "created_at",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=16,
        )

        headings = {
            "id": "ID",
            "name": "Scheme Name",
            "class_name": "Class",
            "academic_year_name": "Academic Year",
            "version_no": "Version",
            "band_count": "Grade Bands",
            "status": "Status",
            "created_at": "Created At",
        }

        widths = {
            "id": 55,
            "name": 190,
            "class_name": 120,
            "academic_year_name": 145,
            "version_no": 75,
            "band_count": 90,
            "status": 95,
            "created_at": 155,
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
            "<<TreeviewSelect>>",
            self.apply_selection_controls,
        )
        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected(),
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        self.edit_button = ttk.Button(
            actions,
            text="Edit Selected",
            command=self.edit_selected,
        )
        self.edit_button.pack(side="left", padx=4)

        self.manage_bands_button = ttk.Button(
            actions,
            text="Manage Grade Bands",
            command=self.manage_selected_bands,
        )
        self.manage_bands_button.pack(side="left", padx=4)

        self.activate_button = ttk.Button(
            actions,
            text="Activate",
            command=self.activate_selected,
        )
        self.activate_button.pack(side="left", padx=4)

        self.archive_button = ttk.Button(
            actions,
            text="Archive",
            command=self.archive_selected,
        )
        self.archive_button.pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right", padx=4)

        self.apply_selection_controls()

    # --------------------------------------------------
    # CLASS FILTER
    # --------------------------------------------------

    def load_class_options(self):
        selected_label = self.class_var.get()

        self.class_id_by_label = {"All": None}
        labels = ["All"]

        try:
            classes = get_classes(actor_user_id=self.user["id"])

            for school_class in classes:
                class_id = int(school_class["id"])
                class_name = str(school_class["name"])

                label = f"{class_name} (ID: {class_id})"

                self.class_id_by_label[label] = class_id
                labels.append(label)

            self.class_combo["values"] = labels

            if selected_label in self.class_id_by_label:
                self.class_var.set(selected_label)
            else:
                self.class_var.set("All")

        except Exception as error:
            self.class_combo["values"] = labels
            self.class_var.set("All")

            messagebox.showerror(
                "Loading Error",
                f"Could not load class filters:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # ACADEMIC YEAR FILTER
    # --------------------------------------------------

    def load_academic_year_options(self):
        selected_label = self.academic_year_var.get()

        self.academic_year_id_by_label = {"All": None}
        labels = ["All"]

        try:
            academic_years = get_academic_years(actor_user_id=self.user['id'])

            for year in academic_years:
                year_id = int(year["id"])
                year_name = str(year["name"])

                label = (
                    f'{year_name} '
                    f'({year["start_date"]} to {year["end_date"]}) '
                    f'(ID: {year_id})'
                )

                self.academic_year_id_by_label[label] = year_id
                labels.append(label)

            self.academic_year_combo["values"] = labels

            if selected_label in self.academic_year_id_by_label:
                self.academic_year_var.set(selected_label)
            else:
                self.academic_year_var.set("All")

        except Exception as error:
            self.academic_year_combo["values"] = labels
            self.academic_year_var.set("All")

            messagebox.showerror(
                "Loading Error",
                f"Could not load academic-year filters:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_grading_schemes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        class_id = self.class_id_by_label.get(
            self.class_var.get()
        )

        academic_year_id = self.academic_year_id_by_label.get(
            self.academic_year_var.get()
        )

        selected_status = self.status_var.get()
        status = (
            None
            if selected_status == "All"
            else selected_status.lower()
        )

        try:
            schemes = get_grading_schemes(
                class_id=class_id,
                academic_year_id=academic_year_id,
                status=status,
                search=self.search_var.get().strip(),
                actor_user_id=self.user["id"],
            )

            for scheme in schemes:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(scheme["id"]),
                    values=(
                        scheme["id"],
                        scheme["name"],
                        scheme["class_name"],
                        scheme["academic_year_name"],
                        scheme["version_no"],
                        scheme["band_count"],
                        str(scheme["status"]).capitalize(),
                        scheme["created_at"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load grading schemes:\n{error}",
                parent=self,
            )

        self.apply_selection_controls()

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_scheme(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a grading scheme first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return {
            "id": int(values[0]),
            "name": values[1],
            "class_name": values[2],
            "academic_year_name": values[3],
            "version_no": int(values[4]),
            "band_count": int(values[5]),
            "status": str(values[6]).strip().lower(),
            "created_at": values[7],
        }

    def apply_selection_controls(self, event=None):
        selection = self.tree.selection()

        if not selection:
            self.edit_button.configure(state="disabled")
            self.manage_bands_button.configure(state="disabled")
            self.activate_button.configure(state="disabled")
            self.archive_button.configure(state="disabled")
            return

        scheme = self.get_selected_scheme_from_tree()

        if scheme is None:
            self.edit_button.configure(state="disabled")
            self.manage_bands_button.configure(state="disabled")
            self.activate_button.configure(state="disabled")
            self.archive_button.configure(state="disabled")
            return

        status = scheme["status"]

        self.edit_button.configure(
            state="normal" if status == "draft" else "disabled"
        )

        self.manage_bands_button.configure(state="normal")

        self.activate_button.configure(
            state="normal" if status == "draft" else "disabled"
        )

        self.archive_button.configure(
            state=(
                "normal"
                if status in {"draft", "active"}
                else "disabled"
            )
        )

    def get_selected_scheme_from_tree(self):
        selection = self.tree.selection()

        if not selection:
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        if not values:
            return None

        return {
            "id": int(values[0]),
            "status": str(values[6]).strip().lower(),
        }

    # --------------------------------------------------
    # CREATE / EDIT
    # --------------------------------------------------

    def create_grading_scheme(self):
        if self.on_create:
            self.on_create()

    def edit_selected(self):
        scheme = self.get_selected_scheme()

        if scheme is None:
            return

        if scheme["status"] != "draft":
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Only draft grading schemes can be edited.",
                parent=self,
            )
            return

        if self.on_edit:
            self.on_edit(scheme["id"])

    # --------------------------------------------------
    # GRADE BAND MANAGEMENT
    # --------------------------------------------------

    def manage_selected_bands(self):
        scheme = self.get_selected_scheme()

        if scheme is None:
            return

        if self.on_manage_bands:
            self.on_manage_bands(scheme["id"])

    # --------------------------------------------------
    # SCHEME LIFECYCLE
    # --------------------------------------------------

    def activate_selected(self):
        scheme = self.get_selected_scheme()

        if scheme is None:
            return

        if scheme["status"] != "draft":
            messagebox.showwarning(
                "Invalid Operation",
                "Only draft grading schemes can be activated.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Grading Scheme Activation",
            (
                "Are you sure you want to activate this grading scheme?\n\n"
                f'Scheme: {scheme["name"]}\n'
                f'Class: {scheme["class_name"]}\n'
                f'Academic Year: {scheme["academic_year_name"]}\n'
                f'Version: {scheme["version_no"]}\n\n'
                "Activation requires at least two grade bands and "
                "exactly one 0 percent threshold. Only one active "
                "scheme is allowed per class and academic year."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            activate_grading_scheme(
                scheme["id"], actor_user_id=self.user["id"]
            )

            messagebox.showinfo(
                "Success",
                "Grading scheme activated successfully.",
                parent=self,
            )

            self.load_grading_schemes()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Activate Scheme",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not activate grading scheme:\n{error}",
                parent=self,
            )

    def archive_selected(self):
        scheme = self.get_selected_scheme()

        if scheme is None:
            return

        if scheme["status"] not in {"draft", "active"}:
            messagebox.showwarning(
                "Invalid Operation",
                "This grading scheme cannot be archived.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Grading Scheme Archive",
            (
                "Are you sure you want to archive this grading scheme?\n\n"
                f'Scheme: {scheme["name"]}\n'
                f'Class: {scheme["class_name"]}\n'
                f'Academic Year: {scheme["academic_year_name"]}\n'
                f'Version: {scheme["version_no"]}\n'
                f'Status: {scheme["status"].capitalize()}\n\n'
                "Archived schemes are permanently read-only and "
                "cannot be reactivated."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            archive_grading_scheme(
                scheme["id"], actor_user_id=self.user["id"]
            )

            messagebox.showinfo(
                "Success",
                "Grading scheme archived successfully.",
                parent=self,
            )

            self.load_grading_schemes()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Archive Scheme",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not archive grading scheme:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # FILTERS / REFRESH
    # --------------------------------------------------

    def reset_filters(self):
        self.search_var.set("")
        self.class_var.set("All")
        self.academic_year_var.set("All")
        self.status_var.set("All")

        self.load_grading_schemes()

    def refresh(self):
        self.load_class_options()
        self.load_academic_year_options()
        self.load_grading_schemes()
