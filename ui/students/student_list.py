import tkinter as tk
from tkinter import ttk, messagebox

from services.student_service import (
    get_students,
    update_student_status
)


class StudentListFrame(ttk.Frame):

    def __init__(self, master, user, on_register, on_profile, on_edit):
        super().__init__(master, padding=25)

        if not user or not user.get("id"):
            raise ValueError("An authenticated user is required.")
        self.user = user
        self.on_register = on_register
        self.on_profile = on_profile
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_students()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Student Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search, view and manage student records.",
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
            text="Search Students:"
        ).pack(side="left", padx=(0, 10))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_students()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_students
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # STUDENT TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "admission_no",
            "name",
            "gender",
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
            "admission_no": "Admission No.",
            "name": "Student Name",
            "gender": "Gender",
            "phone": "Phone",
            "status": "Status"
        }

        widths = {
            "id": 55,
            "admission_no": 130,
            "name": 200,
            "gender": 90,
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
            text="Register Student",
            command=self.on_register
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="View Profile",
            command=self.view_profile
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Student",
            command=self.edit_student
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_students
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_students(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            students = get_students(
                self.search_var.get(),
                actor_user_id=self.user["id"]
            )

            for student in students:
                full_name = (
                    f"{student['first_name']} "
                    f"{student['last_name']}"
                )

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        student["id"],
                        student["admission_no"],
                        full_name,
                        student["gender"] or "-",
                        student["phone"] or "-",
                        student["status"]
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load student records:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_student_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a student first.",
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
        student_id = self.get_selected_student_id()

        if student_id is not None:
            self.on_profile(student_id)

    # --------------------------------------------------
    # EDIT
    # --------------------------------------------------

    def edit_student(self):
        student_id = self.get_selected_student_id()

        if student_id is not None:
            self.on_edit(student_id)

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def change_status(self):
        student_id = self.get_selected_student_id()

        if student_id is None:
            return

        from services.student_service import get_student

        student = get_student(
            student_id, actor_user_id=self.user["id"]
        )

        if not student:
            messagebox.showerror(
                "Not Found",
                "Student record no longer exists.",
                parent=self
            )
            self.load_students()
            return

        dialog = tk.Toplevel(self)
        dialog.title("Change Student Status")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"Student: {student['first_name']} "
                 f"{student['last_name']}",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=(20, 10))

        status_var = tk.StringVar(
            value=student["status"]
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
                "graduated",
                "transferred"
            ],
            state="readonly",
            width=25
        )
        status_box.pack(pady=5)

        def save_status():
            try:
                new_status = status_var.get()

                if new_status == student["status"]:
                    dialog.destroy()
                    return

                update_student_status(
                    student_id,
                    new_status,
                    actor_user_id=self.user["id"]
                )

                dialog.destroy()
                self.load_students()

                messagebox.showinfo(
                    "Status Updated",
                    "Student status updated successfully.",
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
        self.load_students()
