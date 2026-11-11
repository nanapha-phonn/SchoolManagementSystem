import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import get_classes
from services.section_service import create_section, update_section


class SectionForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        section=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.section = section

        self.name_var = tk.StringVar()
        self.class_var = tk.StringVar()

        self.class_id_by_label = {}
        self.class_label_by_id = {}

        self.create_header()
        self.create_form()
        self.load_classes()
        self.create_buttons()

        if self.section:
            self.load_section_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit Section Information"
            if self.section
            else "Section Registration"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Create and manage sections within school classes.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Section Information",
            padding=20
        )
        form.pack(fill="x")

        form.columnconfigure(1, weight=1)

        ttk.Label(
            form,
            text="Class"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=12
        )

        self.class_box = ttk.Combobox(
            form,
            textvariable=self.class_var,
            state="readonly",
            width=35
        )

        self.class_box.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=12
        )

        ttk.Label(
            form,
            text="Section Name"
        ).grid(
            row=1,
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
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=12
        )

        ttk.Label(
            form,
            text="Create a class first if no classes are available.",
            foreground="#64748B"
        ).grid(
            row=2,
            column=1,
            sticky="w",
            padx=8,
            pady=(3, 10)
        )

    # --------------------------------------------------
    # LOAD AVAILABLE CLASSES
    # --------------------------------------------------

    def load_classes(self):
        try:
            classes = get_classes(actor_user_id=self.user["id"])

            self.class_id_by_label.clear()
            self.class_label_by_id.clear()

            labels = []

            for school_class in classes:
                class_id = int(school_class["id"])
                label = (
                    f"{class_id} - {school_class['name']}"
                )

                labels.append(label)
                self.class_id_by_label[label] = class_id
                self.class_label_by_id[class_id] = label

            self.class_box["values"] = labels

            self.class_var.set("")

        except Exception as error:
            self.class_box["values"] = ()

            messagebox.showerror(
                "Loading Error",
                f"Could not load available classes:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # LOAD EXISTING DATA
    # --------------------------------------------------

    def load_section_data(self):
        self.name_var.set(
            self.section.get("name") or ""
        )

        class_id = int(self.section["class_id"])

        self.class_var.set(
            self.class_label_by_id.get(class_id, "")
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)

        save_text = (
            "Update Section"
            if self.section
            else "Save Section"
        )

        ttk.Button(
            button_frame,
            text=save_text,
            command=self.save_section
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Clear Form",
            command=self.clear_form
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="Back to Sections",
            command=self.go_back
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE / UPDATE
    # --------------------------------------------------

    def save_section(self):
        selected_class_id = self.class_id_by_label.get(
            self.class_var.get()
        )

        if selected_class_id is None:
            messagebox.showwarning(
                "Class Required",
                "Please select a class. Create a class first "
                "if no classes are available.",
                parent=self
            )
            return

        section_data = {
            "class_id": selected_class_id,
            "name": self.name_var.get().strip(),
        }

        try:
            if self.section:
                update_section(
                    self.section["id"],
                    section_data,
                    actor_user_id=self.user["id"],
                )

                message = "Section information updated successfully."

            else:
                section_id = create_section(
                    section_data,
                    actor_user_id=self.user["id"],
                )

                message = (
                    "Section created successfully.\n"
                    f"Section ID: {section_id}"
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
                "Invalid Section Information",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Operation Error",
                f"Could not save section information:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # CLEAR
    # --------------------------------------------------

    def clear_form(self):
        self.name_var.set("")
        self.class_var.set("")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
