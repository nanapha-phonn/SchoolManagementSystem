import tkinter as tk
from tkinter import ttk, messagebox

from services.subject_service import (
    create_subject,
    update_subject,
)


class SubjectForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        subject=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_back = on_back
        self.on_saved = on_saved
        self.subject = subject

        self.subject_code_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.status_var = tk.StringVar(value="active")

        self.create_widgets()

        if self.subject:
            self.load_subject()

    def create_widgets(self):
        title = (
            "Edit Subject"
            if self.subject
            else "Register Subject"
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", pady=(0, 20))

        form = ttk.Frame(self)
        form.pack(fill="x")

        ttk.Label(
            form,
            text="Subject Code",
        ).grid(row=0, column=0, sticky="w", pady=8)

        self.code_entry = ttk.Entry(
            form,
            textvariable=self.subject_code_var,
            width=45,
        )
        self.code_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(15, 0),
            pady=8,
        )

        ttk.Label(
            form,
            text="Subject Name",
        ).grid(row=1, column=0, sticky="w", pady=8)

        ttk.Entry(
            form,
            textvariable=self.name_var,
            width=45,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(15, 0),
            pady=8,
        )

        ttk.Label(
            form,
            text="Description",
        ).grid(row=2, column=0, sticky="nw", pady=8)

        self.description_text = tk.Text(
            form,
            width=45,
            height=5,
            font=("Segoe UI", 10),
            wrap="word",
        )
        self.description_text.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(15, 0),
            pady=8,
        )

        ttk.Label(
            form,
            text="Status",
        ).grid(row=3, column=0, sticky="w", pady=8)

        self.status_box = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=("active", "inactive"),
            state="readonly",
            width=42,
        )
        self.status_box.grid(
            row=3,
            column=1,
            sticky="w",
            padx=(15, 0),
            pady=8,
        )

        form.columnconfigure(1, weight=1)

        if not self.subject:
            self.status_box.configure(state="disabled")

        buttons = ttk.Frame(self)
        buttons.pack(anchor="w", pady=(20, 0))

        ttk.Button(
            buttons,
            text="Save Subject",
            command=self.save_subject,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Clear",
            command=self.clear_form,
        ).pack(side="left", padx=8)

        ttk.Button(
            buttons,
            text="Back",
            command=self.go_back,
        ).pack(side="left", padx=8)

    def load_subject(self):
        self.subject_code_var.set(
            self.subject.get("subject_code", "")
        )
        self.name_var.set(
            self.subject.get("name", "")
        )
        self.description_text.insert(
            "1.0",
            self.subject.get("description") or "",
        )
        self.status_var.set(
            self.subject.get("status", "active")
        )

    def save_subject(self):
        description = self.description_text.get(
            "1.0",
            "end-1c",
        ).strip()

        subject_data = {
            "subject_code": self.subject_code_var.get(),
            "name": self.name_var.get(),
            "description": description,
            "status": (
                self.status_var.get()
                if self.subject
                else "active"
            ),
        }

        try:
            if self.subject:
                update_subject(
                    self.subject["id"],
                    subject_data,
                    actor_user_id=self.user["id"],
                )
                message = "Subject updated successfully."
            else:
                create_subject(
                    subject_data,
                    actor_user_id=self.user["id"],
                )
                message = "Subject registered successfully."

            messagebox.showinfo(
                "Success",
                message,
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except ValueError as error:
            messagebox.showwarning(
                "Validation Error",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not save subject:\n{error}",
                parent=self,
            )

    def clear_form(self):
        self.subject_code_var.set("")
        self.name_var.set("")
        self.description_text.delete("1.0", "end")

        if self.subject:
            self.status_var.set(
                self.subject.get("status", "active")
            )
        else:
            self.status_var.set("active")

    def go_back(self):
        if self.on_back:
            self.on_back()
