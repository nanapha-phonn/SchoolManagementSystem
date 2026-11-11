import tkinter as tk
from tkinter import ttk, messagebox

from services.teacher_service import (
    get_teachers,
    get_teacher,
    update_teacher_status
)


class TeacherListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_register,
        on_profile,
        on_edit,
        *,
        user,
    ):
        super().__init__(master, padding=25)
        self.user = user

        self.on_register = on_register
        self.on_profile = on_profile
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_teachers()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Teacher Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search, view and manage employee records.",
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
            text="Search Teachers:"
        ).pack(side="left", padx=(0, 10))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_teachers()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_teachers
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # TEACHER TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "employee_no",
            "name",
            "department",
            "phone",
            "status"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "id": "ID",
            "employee_no": "Employee No.",
            "name": "Teacher Name",
            "department": "Department",
            "phone": "Phone",
            "status": "Status"
        }

        widths = {
            "id": 55,
            "employee_no": 130,
            "name": 200,
            "department": 150,
            "phone": 130,
            "status": 110
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
            lambda event: self.view_profile()
        )

    # --------------------------------------------------
    # ACTION BUTTONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Teacher",
            command=self.on_register
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="View Profile",
            command=self.view_profile
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Teacher",
            command=self.edit_teacher
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_teachers
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_teachers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            teachers = get_teachers(
                self.search_var.get(),
                actor_user_id=self.user["id"],
            )

            for teacher in teachers:
                full_name = (
                    f"{teacher['first_name']} "
                    f"{teacher['last_name']}"
                )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        teacher["id"],
                        teacher["employee_no"],
                        full_name,
                        teacher["department"] or "-",
                        teacher["phone"] or "-",
                        teacher["status"]
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load teacher records:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_teacher_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a teacher first.",
                parent=self
            )
            return None

        values = self.tree.item(
            selection[0],
            "values"
        )

        return int(values[0])

    # --------------------------------------------------
    # PROFILE
    # --------------------------------------------------

    def view_profile(self):
        teacher_id = self.get_selected_teacher_id()

        if teacher_id is not None:
            self.on_profile(teacher_id)

    # --------------------------------------------------
    # EDIT
    # --------------------------------------------------

    def edit_teacher(self):
        teacher_id = self.get_selected_teacher_id()

        if teacher_id is not None:
            self.on_edit(teacher_id)

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def change_status(self):
        teacher_id = self.get_selected_teacher_id()

        if teacher_id is None:
            return

        teacher = get_teacher(
            teacher_id,
            actor_user_id=self.user["id"],
        )

        if not teacher:
            messagebox.showerror(
                "Not Found",
                "Teacher record no longer exists.",
                parent=self
            )
            self.load_teachers()
            return

        dialog = tk.Toplevel(self)
        dialog.title("Change Teacher Status")
        dialog.geometry("370x190")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.wait_visibility()
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=(
                f"Teacher: {teacher['first_name']} "
                f"{teacher['last_name']}"
            ),
            font=("Segoe UI", 11, "bold")
        ).pack(pady=(20, 10))

        status_var = tk.StringVar(
            value=teacher["status"]
        )

        ttk.Label(
            dialog,
            text="Select new status:"
        ).pack(pady=5)

        status_box = ttk.Combobox(
            dialog,
            textvariable=status_var,
            values=[
                "active",
                "inactive",
                "resigned",
                "terminated"
            ],
            state="readonly",
            width=25
        )
        status_box.pack(pady=5)

        def save_status():
            try:
                new_status = status_var.get()

                if new_status == teacher["status"]:
                    dialog.destroy()
                    return

                update_teacher_status(
                    teacher_id,
                    new_status,
                    actor_user_id=self.user["id"],
                )

                dialog.destroy()
                self.load_teachers()

                messagebox.showinfo(
                    "Status Updated",
                    "Teacher status updated successfully.",
                    parent=self
                )

            except Exception as error:
                messagebox.showerror(
                    "Update Error",
                    str(error),
                    parent=dialog
                )

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)

        ttk.Button(
            button_frame,
            text="Save",
            command=save_status
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # CLEAR SEARCH
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_teachers()
