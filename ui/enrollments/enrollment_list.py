import tkinter as tk
from tkinter import ttk, messagebox

from services.enrollment_service import get_enrollments
from services.academic_year_service import get_academic_years
from services.class_service import get_classes


ENROLLMENT_STATUSES = [
    "enrolled",
    "completed",
    "withdrawn",
    "transferred",
]


class EnrollmentListFrame(ttk.Frame):

    ALL_YEARS = "All Academic Years"
    ALL_CLASSES = "All Classes"
    ALL_STATUSES = "All Statuses"

    def __init__(
        self,
        master,
        on_create,
        on_edit,
        on_promote,
        user,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit
        self.on_promote = on_promote

        self.search_var = tk.StringVar()
        self.year_filter_var = tk.StringVar(value=self.ALL_YEARS)
        self.class_filter_var = tk.StringVar(value=self.ALL_CLASSES)
        self.status_filter_var = tk.StringVar(value=self.ALL_STATUSES)

        self.year_id_by_label = {self.ALL_YEARS: None}
        self.class_id_by_label = {self.ALL_CLASSES: None}

        self.create_header()
        self.create_filters()
        self.create_table()
        self.create_actions()

        self.load_filter_options()
        self.load_enrollments()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))

        ttk.Label(
            header,
            text="Student Enrollment Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Manage enrollment records, search academic history "
                "and promote students to another academic year."
            ),
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------

    def create_filters(self):
        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=12
        )
        filters.pack(fill="x", pady=(0, 15))

        filters.columnconfigure(1, weight=1)
        filters.columnconfigure(3, weight=1)

        ttk.Label(
            filters,
            text="Search"
        ).grid(row=0, column=0, sticky="w", padx=5, pady=6)

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=25
        )
        search_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=5,
            pady=6
        )

        search_entry.bind(
            "<Return>",
            lambda event: self.load_enrollments()
        )

        ttk.Label(
            filters,
            text="Academic Year"
        ).grid(row=0, column=2, sticky="w", padx=5, pady=6)

        self.year_filter_combo = ttk.Combobox(
            filters,
            textvariable=self.year_filter_var,
            state="readonly",
            width=25
        )
        self.year_filter_combo.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=5,
            pady=6
        )

        self.year_filter_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_enrollments()
        )

        ttk.Label(
            filters,
            text="Class"
        ).grid(row=1, column=0, sticky="w", padx=5, pady=6)

        self.class_filter_combo = ttk.Combobox(
            filters,
            textvariable=self.class_filter_var,
            state="readonly",
            width=25
        )
        self.class_filter_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=5,
            pady=6
        )

        self.class_filter_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_enrollments()
        )

        ttk.Label(
            filters,
            text="Status"
        ).grid(row=1, column=2, sticky="w", padx=5, pady=6)

        self.status_filter_combo = ttk.Combobox(
            filters,
            textvariable=self.status_filter_var,
            values=[self.ALL_STATUSES] + ENROLLMENT_STATUSES,
            state="readonly",
            width=25
        )
        self.status_filter_combo.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=5,
            pady=6
        )

        self.status_filter_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_enrollments()
        )

        actions = ttk.Frame(filters)
        actions.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="e",
            padx=5,
            pady=(8, 0)
        )

        ttk.Button(
            actions,
            text="Search",
            command=self.load_enrollments
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Clear Filters",
            command=self.clear_filters
        ).pack(side="left", padx=4)

    # --------------------------------------------------
    # FILTER REFERENCE DATA
    # --------------------------------------------------

    def load_filter_options(self):
        try:
            selected_year = self.year_filter_var.get()
            selected_class = self.class_filter_var.get()

            self.year_id_by_label = {
                self.ALL_YEARS: None
            }

            year_labels = [self.ALL_YEARS]

            for year in get_academic_years(
                actor_user_id=self.user["id"]
            ):
                label = f'{year["id"]} - {year["name"]}'
                year_labels.append(label)
                self.year_id_by_label[label] = year["id"]

            self.year_filter_combo["values"] = year_labels

            if selected_year in year_labels:
                self.year_filter_var.set(selected_year)
            else:
                self.year_filter_var.set(self.ALL_YEARS)

            self.class_id_by_label = {
                self.ALL_CLASSES: None
            }

            class_labels = [self.ALL_CLASSES]

            for school_class in get_classes(
                actor_user_id=self.user["id"]
            ):
                label = (
                    f'{school_class["id"]} - '
                    f'{school_class["name"]}'
                )

                class_labels.append(label)
                self.class_id_by_label[label] = school_class["id"]

            self.class_filter_combo["values"] = class_labels

            if selected_class in class_labels:
                self.class_filter_var.set(selected_class)
            else:
                self.class_filter_var.set(self.ALL_CLASSES)

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load enrollment filters:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "admission_no",
            "student",
            "academic_year",
            "class",
            "section",
            "enrolled_on",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "id": "ID",
            "admission_no": "Admission No.",
            "student": "Student Name",
            "academic_year": "Academic Year",
            "class": "Class",
            "section": "Section",
            "enrolled_on": "Enrollment Date",
            "status": "Status",
        }

        widths = {
            "id": 50,
            "admission_no": 115,
            "student": 160,
            "academic_year": 110,
            "class": 90,
            "section": 75,
            "enrolled_on": 115,
            "status": 100,
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

        y_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        x_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        y_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        x_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_enrollment()
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="New Enrollment",
            command=self.on_create
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Enrollment",
            command=self.edit_enrollment
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Promote Student",
            command=self.promote_student
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD ENROLLMENTS
    # --------------------------------------------------

    def load_enrollments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        year_id = self.year_id_by_label.get(
            self.year_filter_var.get()
        )

        class_id = self.class_id_by_label.get(
            self.class_filter_var.get()
        )

        status = self.status_filter_var.get()

        if status == self.ALL_STATUSES:
            status = None

        try:
            enrollments = get_enrollments(
                search=self.search_var.get(),
                academic_year_id=year_id,
                class_id=class_id,
                status=status,
                actor_user_id=self.user["id"],
            )

            for enrollment in enrollments:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(enrollment["id"]),
                    values=(
                        enrollment["id"],
                        enrollment["admission_no"],
                        enrollment["student_name"],
                        enrollment["academic_year_name"],
                        enrollment["class_name"],
                        enrollment["section_name"],
                        enrollment["enrolled_on"],
                        enrollment["status"],
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load enrollment records:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_enrollment_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select an enrollment record first.",
                parent=self
            )
            return None

        return int(selection[0])

    # --------------------------------------------------
    # EDIT
    # --------------------------------------------------

    def edit_enrollment(self):
        enrollment_id = self.get_selected_enrollment_id()

        if enrollment_id is not None:
            self.on_edit(enrollment_id)

    # --------------------------------------------------
    # PROMOTION
    # --------------------------------------------------

    def promote_student(self):
        enrollment_id = self.get_selected_enrollment_id()

        if enrollment_id is not None:
            self.on_promote(enrollment_id)

    # --------------------------------------------------
    # REFRESH / CLEAR
    # --------------------------------------------------

    def refresh(self):
        self.load_filter_options()
        self.load_enrollments()

    def clear_filters(self):
        self.search_var.set("")
        self.year_filter_var.set(self.ALL_YEARS)
        self.class_filter_var.set(self.ALL_CLASSES)
        self.status_filter_var.set(self.ALL_STATUSES)
        self.load_enrollments()
