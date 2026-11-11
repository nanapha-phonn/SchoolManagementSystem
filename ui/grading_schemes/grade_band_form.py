import tkinter as tk
from tkinter import ttk, messagebox

from services.grading_scheme_service import (
    create_grade_band,
    update_grade_band,
)


class GradeBandForm(ttk.Frame):

    def __init__(
        self,
        master,
        grading_scheme,
        on_back=None,
        on_saved=None,
        grade_band=None,
        *,
        user,
    ):
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("An authenticated user is required.")

        super().__init__(master, padding=25)

        self.user = user
        self.grading_scheme = grading_scheme
        self.grade_band = grade_band
        self.on_back = on_back
        self.on_saved = on_saved

        self.grade_label_var = tk.StringVar()
        self.min_percentage_var = tk.StringVar()
        self.grade_point_var = tk.StringVar()

        self.is_locked = (
            grading_scheme.get("status") != "draft"
        )

        self.create_header()
        self.create_form()

        if self.grade_band:
            self.load_grade_band()

        self.create_buttons()
        self.apply_form_state()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Grade Band"
            if self.grade_band
            else "Add Grade Band"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                f'Grading Scheme: {self.grading_scheme["name"]} '
                f'(Version {self.grading_scheme["version_no"]})'
            ),
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 5))

        ttk.Label(
            self,
            text=(
                "Define the minimum percentage required for this grade. "
                "The highest qualifying threshold determines the grade."
            ),
            font=("Segoe UI", 10),
            wraplength=800,
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Grade Band Information",
            padding=20,
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        fields = [
            (
                "Grade Label",
                self.grade_label_var,
                "Example: A, B, C, Pass, Fail",
            ),
            (
                "Minimum Percentage",
                self.min_percentage_var,
                "Example: 80",
            ),
            (
                "Grade Point (Optional)",
                self.grade_point_var,
                "Example: 4.0",
            ),
        ]

        self.entries = {}

        for row, (label_text, variable, placeholder) in enumerate(fields):
            ttk.Label(
                form,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=8,
                pady=12,
            )

            entry = ttk.Entry(
                form,
                textvariable=variable,
                width=35,
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                padx=8,
                pady=12,
            )

            self.entries[label_text] = entry

        ttk.Label(
            form,
            text="Remark (Optional)",
        ).grid(
            row=3,
            column=0,
            sticky="nw",
            padx=8,
            pady=12,
        )

        self.remark_text = tk.Text(
            form,
            height=4,
            width=45,
            font=("Segoe UI", 10),
            wrap="word",
        )
        self.remark_text.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=8,
            pady=12,
        )

        ttk.Label(
            form,
            text=(
                "Minimum percentage must be between 0 and 100. "
                "Every active scheme requires at least two grade bands "
                "and exactly one band starting at 0%."
            ),
            foreground="#64748B",
            wraplength=650,
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=8,
            pady=(12, 5),
        )

    # --------------------------------------------------
    # LOAD EXISTING BAND
    # --------------------------------------------------

    def load_grade_band(self):
        band = self.grade_band

        self.remark_text.delete("1.0", "end")

        self.grade_label_var.set(
            band.get("grade_label") or ""
        )

        self.min_percentage_var.set(
            str(band.get("min_percentage", ""))
        )

        grade_point = band.get("grade_point")

        self.grade_point_var.set(
            "" if grade_point is None else str(grade_point)
        )

        self.remark_text.insert(
            "1.0",
            band.get("remark") or "",
        )

    # --------------------------------------------------
    # FORM STATE
    # --------------------------------------------------

    def apply_form_state(self):
        if self.is_locked:
            for entry in self.entries.values():
                entry.configure(state="disabled")

            self.remark_text.configure(state="disabled")
            self.save_button.configure(state="disabled")
            self.clear_button.configure(state="disabled")

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Grade Band"
            if self.grade_band
            else "Save Grade Band"
        )

        self.save_button = ttk.Button(
            buttons,
            text=save_text,
            command=self.save_grade_band,
        )
        self.save_button.pack(side="right", padx=5)

        self.clear_button = ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        )
        self.clear_button.pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Grade Bands",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_grade_band(self):
        if self.is_locked:
            messagebox.showwarning(
                "Grading Scheme Locked",
                "Grade bands cannot be changed in active or archived schemes.",
                parent=self,
            )
            return

        try:
            minimum_text = self.min_percentage_var.get().strip()

            if not minimum_text:
                raise ValueError("Minimum percentage is required.")

            try:
                min_percentage = float(minimum_text)
            except ValueError:
                raise ValueError(
                    "Minimum percentage must be numeric."
                )

            grade_point_text = self.grade_point_var.get().strip()

            if grade_point_text:
                try:
                    grade_point = float(grade_point_text)
                except ValueError:
                    raise ValueError(
                        "Grade point must be numeric or left empty."
                    )
            else:
                grade_point = None

            band_data = {
                "grade_label": self.grade_label_var.get().strip(),
                "min_percentage": min_percentage,
                "grade_point": grade_point,
                "remark": self.remark_text.get(
                    "1.0",
                    "end-1c",
                ).strip(),
            }

            if self.grade_band:
                update_grade_band(
                    self.grade_band["id"],
                    band_data,
                    actor_user_id=self.user["id"],
                )
                message = "Grade band updated successfully."

            else:
                band_id = create_grade_band(
                    self.grading_scheme["id"],
                    band_data,
                    actor_user_id=self.user["id"],
                )
                message = (
                    "Grade band created successfully.\n"
                    f"Grade Band ID: {band_id}"
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
                "Invalid Grade Band Information",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save grade band:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        if self.grade_band:
            self.load_grade_band()
            return

        self.grade_label_var.set("")
        self.min_percentage_var.set("")
        self.grade_point_var.set("")
        self.remark_text.delete("1.0", "end")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
