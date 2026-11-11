import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import create_class, update_class


class ClassForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        school_class=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.school_class = school_class

        self.name_var = tk.StringVar()

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.school_class:
            self.load_class_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Class Information"
            if self.school_class
            else "Class Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Create and manage school classes.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Class Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        ttk.Label(
            form,
            text="Class Name"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=12
        )

        ttk.Entry(
            form,
            textvariable=self.name_var,
            width=40
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=12
        )

        ttk.Label(
            form,
            text="Description"
        ).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=8,
            pady=12
        )

        self.description_text = tk.Text(
            form,
            height=5,
            width=45,
            font=("Segoe UI", 10),
            wrap="word"
        )

        self.description_text.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=12
        )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_class_data(self):
        self.name_var.set(
            self.school_class.get("name") or ""
        )

        self.description_text.insert(
            "1.0",
            self.school_class.get("description") or ""
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Class"
            if self.school_class
            else "Save Class"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_class
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Classes",
            command=self.go_back
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_class(self):
        class_data = {
            "name": self.name_var.get(),
            "description": self.description_text.get(
                "1.0",
                "end"
            ).strip(),
        }

        try:
            if self.school_class:
                update_class(
                    self.school_class["id"],
                    class_data,
                    actor_user_id=self.user["id"],
                )

                message = "Class information updated successfully."

            else:
                class_id = create_class(
                    class_data,
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Class created successfully.\n"
                    f"Class ID: {class_id}"
                )

            messagebox.showinfo(
                "Success",
                message,
                parent=self
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Invalid Class Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save class information:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.name_var.set("")
        self.description_text.delete("1.0", "end")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
