import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import get_classes
from services.academic_year_service import get_academic_years
from services.grading_scheme_service import (
    create_grading_scheme,
    update_grading_scheme,
)


class GradingSchemeForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        grading_scheme=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.grading_scheme = grading_scheme

        self.classes = []
        self.academic_years = []

        self.class_id_by_label = {}
        self.year_id_by_label = {}

        self.class_label_by_id = {}
        self.year_label_by_id = {}

        self.class_var = tk.StringVar()
        self.academic_year_var = tk.StringVar()
        self.name_var = tk.StringVar()

        self.class_combo = None
        self.academic_year_combo = None
        self.name_entry = None
        self.save_button = None
        self.clear_button = None

        self.status = (
            str(grading_scheme.get("status") or "draft").lower()
            if grading_scheme
            else "draft"
        )

        self.is_locked = self.status != "draft"
        self.load_error = None

        try:
            self.classes = get_classes(actor_user_id=self.user["id"])
            self.academic_years = get_academic_years(actor_user_id=self.user['id'])
        except Exception as error:
            self.load_error = error

        self.create_header()
        self.create_form()
        self.load_reference_options()

        if self.grading_scheme:
            self.load_grading_scheme()

        self.create_buttons()
        self.apply_form_state()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Grading Scheme"
            if self.grading_scheme
            else "Create Grading Scheme"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Configure percentage-based grading rules for a class "
                "and academic year. New schemes are created as drafts."
            ),
            font=("Segoe UI", 10),
            wraplength=850,
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Grading Scheme Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        ttk.Label(
            form,
            text="Class",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.class_combo = ttk.Combobox(
            form,
            textvariable=self.class_var,
            state="readonly",
            width=45,
        )
        self.class_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="Academic Year",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.academic_year_combo = ttk.Combobox(
            form,
            textvariable=self.academic_year_var,
            state="readonly",
            width=45,
        )
        self.academic_year_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text="Grading Scheme Name",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=8,
            pady=12,
        )

        self.name_entry = ttk.Entry(
            form,
            textvariable=self.name_var,
            width=45,
        )
        self.name_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        self.version_label = ttk.Label(
            form,
            text="Version: Assigned automatically",
            foreground="#64748B",
        )
        self.version_label.grid(
            row=3,
            column=1,
            sticky="w",
            padx=8,
            pady=(8, 5),
        )

        self.status_label = ttk.Label(
            form,
            text="Status: Draft",
            foreground="#64748B",
        )
        self.status_label.grid(
            row=4,
            column=1,
            sticky="w",
            padx=8,
            pady=5,
        )

        self.info_label = ttk.Label(
            form,
            text=(
                "After saving, configure grade bands and activate "
                "the scheme when the rules are complete."
            ),
            foreground="#64748B",
            wraplength=650,
        )
        self.info_label.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
            padx=8,
            pady=(12, 5),
        )

        self.warning_label = ttk.Label(
            form,
            text="",
            foreground="#B45309",
            wraplength=650,
        )
        self.warning_label.grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            padx=8,
            pady=(8, 0),
        )

    # --------------------------------------------------
    # REFERENCE OPTIONS
    # --------------------------------------------------

    def load_reference_options(self):
        class_labels = []

        for school_class in self.classes:
            class_id = int(school_class["id"])
            label = f'{class_id} - {school_class["name"]}'

            self.class_id_by_label[label] = class_id
            self.class_label_by_id[class_id] = label
            class_labels.append(label)

        self.class_combo["values"] = class_labels

        year_labels = []

        for year in self.academic_years:
            year_id = int(year["id"])

            label = (
                f'{year["name"]} '
                f'({year["start_date"]} to {year["end_date"]})'
            )

            self.year_id_by_label[label] = year_id
            self.year_label_by_id[year_id] = label
            year_labels.append(label)

        self.academic_year_combo["values"] = year_labels

        if self.load_error:
            self.warning_label.configure(
                text=f"Could not load reference records: {self.load_error}"
            )
            return

        missing = []

        if not self.classes:
            missing.append("classes")

        if not self.academic_years:
            missing.append("academic years")

        if missing and not self.grading_scheme:
            self.warning_label.configure(
                text=(
                    "No "
                    + " or ".join(missing)
                    + " are available. Register these records first."
                )
            )

    # --------------------------------------------------
    # LOAD EXISTING SCHEME
    # --------------------------------------------------

    def load_grading_scheme(self):
        scheme = self.grading_scheme

        class_id = int(scheme["class_id"])
        year_id = int(scheme["academic_year_id"])

        class_label = self.class_label_by_id.get(class_id)

        if class_label is None:
            class_label = (
                f'{class_id} - {scheme.get("class_name", "Recorded class")}'
            )
            self.class_id_by_label[class_label] = class_id
            self.class_combo["values"] = (
                *self.class_combo["values"],
                class_label,
            )

        year_label = self.year_label_by_id.get(year_id)

        if year_label is None:
            year_label = (
                f'{year_id} - '
                f'{scheme.get("academic_year_name", "Recorded year")}'
            )
            self.year_id_by_label[year_label] = year_id
            self.academic_year_combo["values"] = (
                *self.academic_year_combo["values"],
                year_label,
            )

        self.class_var.set(class_label)
        self.academic_year_var.set(year_label)
        self.name_var.set(scheme.get("name") or "")

        self.version_label.configure(
            text=f'Version: {scheme.get("version_no", 1)}'
        )

        self.status_label.configure(
            text=f'Status: {self.status.capitalize()}'
        )

        if self.is_locked:
            self.info_label.configure(
                text=(
                    "This grading scheme is historical and read-only. "
                    "Create a new version to use different grading rules."
                )
            )

    # --------------------------------------------------
    # FORM STATE
    # --------------------------------------------------

    def apply_form_state(self):
        if self.grading_scheme:
            self.class_combo.configure(state="disabled")
            self.academic_year_combo.configure(state="disabled")

        if self.is_locked:
            self.name_entry.configure(state="disabled")

        no_references = (
            not self.classes
            or not self.academic_years
        ) and not self.grading_scheme

        if self.load_error or no_references or self.is_locked:
            self.save_button.configure(state="disabled")

        if self.grading_scheme:
            self.clear_button.configure(state="disabled")

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Grading Scheme"
            if self.grading_scheme
            else "Save Grading Scheme"
        )

        self.save_button = ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_grading_scheme,
        )
        self.save_button.pack(side="right", padx=5)

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form,
        )
        self.clear_button.pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Records",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_grading_scheme(self):
        if self.is_locked:
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Only draft grading schemes can be edited.",
                parent=self,
            )
            return

        class_id = self.class_id_by_label.get(
            self.class_var.get()
        )

        academic_year_id = self.year_id_by_label.get(
            self.academic_year_var.get()
        )

        if class_id is None:
            messagebox.showwarning(
                "Invalid Grading Scheme Information",
                "Please select a class.",
                parent=self,
            )
            return

        if academic_year_id is None:
            messagebox.showwarning(
                "Invalid Grading Scheme Information",
                "Please select an academic year.",
                parent=self,
            )
            return

        try:
            if self.grading_scheme:
                update_grading_scheme(
                    self.grading_scheme["id"],
                    {
                        "name": self.name_var.get().strip(),
                    },
                    actor_user_id=self.user["id"],
                )

                message = "Grading scheme updated successfully."

            else:
                scheme_id = create_grading_scheme(
                    {
                        "class_id": class_id,
                        "academic_year_id": academic_year_id,
                        "name": self.name_var.get().strip(),
                    },
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Grading scheme created successfully.\n"
                    f"Grading Scheme ID: {scheme_id}"
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
                "Invalid Grading Scheme Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save grading scheme:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.class_var.set("")
        self.academic_year_var.set("")
        self.name_var.set("")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
