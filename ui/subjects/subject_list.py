import tkinter as tk
from tkinter import ttk, messagebox

from services.subject_service import (
    get_subjects,
    update_subject_status,
)


class SubjectListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create=None,
        on_edit=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="All")

        self.create_widgets()
        self.load_subjects()

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Subject Management",
            font=("Segoe UI", 20, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Register Subject",
            command=self.create_subject,
        ).pack(side="right")

        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 12))

        ttk.Label(
            filters,
            text="Search:",
        ).pack(side="left", padx=(0, 8))

        search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=35,
        )
        search_entry.pack(side="left", padx=(0, 15))
        search_entry.bind(
            "<Return>",
            lambda event: self.load_subjects(),
        )

        ttk.Label(
            filters,
            text="Status:",
        ).pack(side="left", padx=(0, 8))

        status_box = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            values=("All", "Active", "Inactive"),
            state="readonly",
            width=12,
        )
        status_box.pack(side="left")
        status_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_subjects(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_subjects,
        ).pack(side="left", padx=8)

        ttk.Button(
            filters,
            text="Reset",
            command=self.reset_filters,
        ).pack(side="left")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "subject_code",
            "name",
            "description",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=16,
        )

        headings = {
            "id": "ID",
            "subject_code": "Subject Code",
            "name": "Subject Name",
            "description": "Description",
            "status": "Status",
        }

        widths = {
            "id": 55,
            "subject_code": 130,
            "name": 190,
            "description": 300,
            "status": 100,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="w",
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
        scrollbar.pack(side="right", fill="y")

        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected(),
        )

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Edit Selected",
            command=self.edit_selected,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="Activate",
            command=lambda: self.change_status("active"),
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Deactivate",
            command=lambda: self.change_status("inactive"),
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_subjects,
        ).pack(side="right")

    def load_subjects(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_status = self.status_var.get()
        status = (
            None
            if selected_status == "All"
            else selected_status.lower()
        )

        try:
            subjects = get_subjects(
                search=self.search_var.get(),
                status=status,
                actor_user_id=self.user["id"],
            )

            for subject in subjects:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        subject["id"],
                        subject["subject_code"],
                        subject["name"],
                        subject.get("description") or "",
                        subject["status"].capitalize(),
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not load subjects:\n{error}",
                parent=self,
            )

    def get_selected_subject_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a subject first.",
                parent=self,
            )
            return None

        values = self.tree.item(
            selection[0],
            "values",
        )

        return int(values[0])

    def create_subject(self):
        if self.on_create:
            self.on_create()

    def edit_selected(self):
        subject_id = self.get_selected_subject_id()

        if subject_id is None:
            return

        if self.on_edit:
            self.on_edit(subject_id)

    def change_status(self, new_status):
        subject_id = self.get_selected_subject_id()

        if subject_id is None:
            return

        action = (
            "activate"
            if new_status == "active"
            else "deactivate"
        )

        confirmed = messagebox.askyesno(
            "Confirm Status Change",
            f"Are you sure you want to {action} this subject?",
            parent=self,
        )

        if not confirmed:
            return

        try:
            update_subject_status(
                subject_id,
                new_status,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                f"Subject {action}d successfully.",
                parent=self,
            )

            self.load_subjects()

        except ValueError as error:
            messagebox.showwarning(
                "Cannot Change Status",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Error",
                f"Could not change subject status:\n{error}",
                parent=self,
            )

    def reset_filters(self):
        self.search_var.set("")
        self.status_var.set("All")
        self.load_subjects()
