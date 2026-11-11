import tkinter as tk
from tkinter import ttk, messagebox

from services.grading_scheme_service import (
    get_grade_bands,
    delete_grade_band,
    activate_grading_scheme,
    archive_grading_scheme,
)


class GradeBandListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        grading_scheme,
        on_add=None,
        on_edit=None,
        on_back=None,
        on_scheme_changed=None,
        *,
        user,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.grading_scheme = grading_scheme
        self.on_add = on_add
        self.on_edit = on_edit
        self.on_back = on_back
        self.on_scheme_changed = on_scheme_changed

        self.status = str(
            grading_scheme.get("status", "")
        ).lower()

        self.create_widgets()
        self.load_grade_bands()

    # --------------------------------------------------
    # WIDGETS
    # --------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="Grade Band Management",
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="Back to Grading Schemes",
            command=self.go_back,
        ).pack(side="right")

        ttk.Label(
            self,
            text=(
                f'Scheme: {self.grading_scheme["name"]}  |  '
                f'Version: {self.grading_scheme["version_no"]}  |  '
                f'Status: {self.status.capitalize()}'
            ),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            self,
            text=(
                "Grade bands are evaluated using the highest minimum "
                "percentage threshold that does not exceed the student's "
                "percentage. Draft schemes can be edited. Active and "
                "archived schemes preserve their grade-band history."
            ),
            wraplength=950,
        ).pack(anchor="w", pady=(0, 18))

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
            "grade_label",
            "min_percentage",
            "grade_point",
            "remark",
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
            "grade_label": "Grade Label",
            "min_percentage": "Minimum Percentage",
            "grade_point": "Grade Point",
            "remark": "Remark",
        }

        widths = {
            "id": 65,
            "grade_label": 140,
            "min_percentage": 180,
            "grade_point": 130,
            "remark": 400,
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
            lambda event: self.edit_selected(),
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        self.add_button = ttk.Button(
            actions,
            text="+ Add Grade Band",
            command=self.add_grade_band,
        )
        self.add_button.pack(side="left", padx=4)

        self.edit_button = ttk.Button(
            actions,
            text="Edit Selected",
            command=self.edit_selected,
        )
        self.edit_button.pack(side="left", padx=4)

        self.delete_button = ttk.Button(
            actions,
            text="Delete Selected",
            command=self.delete_selected,
        )
        self.delete_button.pack(side="left", padx=4)

        self.activate_button = ttk.Button(
            actions,
            text="Activate Scheme",
            command=self.activate_scheme,
        )
        self.activate_button.pack(side="left", padx=4)

        self.archive_button = ttk.Button(
            actions,
            text="Archive Scheme",
            command=self.archive_scheme,
        )
        self.archive_button.pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right", padx=4)

        self.apply_status_controls()

    def apply_status_controls(self):
        editable = self.status == "draft"

        state = "normal" if editable else "disabled"

        self.add_button.configure(state=state)
        self.edit_button.configure(state=state)
        self.delete_button.configure(state=state)

        self.activate_button.configure(
            state=(
                "normal"
                if self.status == "draft"
                else "disabled"
            )
        )

        self.archive_button.configure(
            state=(
                "normal"
                if self.status in {"draft", "active"}
                else "disabled"
            )
        )

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_grade_bands(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            bands = get_grade_bands(
                self.grading_scheme["id"],
                actor_user_id=self.user["id"],
            )

            for band in bands:
                grade_point = band["grade_point"]

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        band["id"],
                        band["grade_label"],
                        f'{band["min_percentage"]:g}%',
                        (
                            ""
                            if grade_point is None
                            else f"{grade_point:g}"
                        ),
                        band["remark"],
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load grade bands:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_grade_band(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a grade band first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return {
            "id": int(values[0]),
            "grade_label": values[1],
            "min_percentage": values[2],
            "grade_point": values[3],
            "remark": values[4],
        }

    # --------------------------------------------------
    # CREATE / EDIT
    # --------------------------------------------------

    def add_grade_band(self):
        if self.status != "draft":
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Only draft grading schemes can be edited.",
                parent=self,
            )
            return

        if self.on_add:
            self.on_add()

    def edit_selected(self):
        if self.status != "draft":
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Only draft grading schemes can be edited.",
                parent=self,
            )
            return

        band = self.get_selected_grade_band()

        if band is not None and self.on_edit:
            self.on_edit(band["id"])

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    def delete_selected(self):
        if self.status != "draft":
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Grade bands cannot be deleted from active or archived schemes.",
                parent=self,
            )
            return

        band = self.get_selected_grade_band()

        if band is None:
            return

        confirmed = messagebox.askyesno(
            "Confirm Grade Band Deletion",
            (
                "Are you sure you want to delete this grade band?\n\n"
                f'Grade: {band["grade_label"]}\n'
                f'Minimum Percentage: {band["min_percentage"]}\n\n'
                "This action cannot be undone."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            delete_grade_band(
                band["id"],
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                "Grade band deleted successfully.",
                parent=self,
            )

            self.load_grade_bands()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Delete Grade Band",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not delete grade band:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SCHEME LIFECYCLE
    # --------------------------------------------------

    def activate_scheme(self):
        if self.status != "draft":
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
                f'Scheme: {self.grading_scheme["name"]}\n'
                f'Version: {self.grading_scheme["version_no"]}\n\n'
                "Activation requires at least two grade bands and "
                "exactly one 0 percent threshold. An active scheme "
                "cannot be edited or reactivated after archiving."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            activate_grading_scheme(
                self.grading_scheme["id"],
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                "Grading scheme activated successfully.",
                parent=self,
            )

            self.notify_scheme_changed()

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

    def archive_scheme(self):
        if self.status not in {"draft", "active"}:
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
                f'Scheme: {self.grading_scheme["name"]}\n'
                f'Version: {self.grading_scheme["version_no"]}\n'
                f'Status: {self.status.capitalize()}\n\n'
                "Archived schemes are permanently read-only and "
                "cannot be reactivated."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            archive_grading_scheme(
                self.grading_scheme["id"],
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                "Grading scheme archived successfully.",
                parent=self,
            )

            self.notify_scheme_changed()

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
    # NAVIGATION / REFRESH
    # --------------------------------------------------

    def notify_scheme_changed(self):
        if self.on_scheme_changed:
            self.on_scheme_changed()

    def go_back(self):
        if self.on_back:
            self.on_back()

    def refresh(self):
        self.load_grade_bands()
