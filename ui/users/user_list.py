import tkinter as tk
from tkinter import ttk, messagebox

from services.user_service import (
    get_users,
    search_users,
    update_user_status,
)


class UserListFrame(ttk.Frame):

    def __init__(
        self,
        master,
        on_create,
        on_edit,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_users()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        ttk.Label(
            self,
            text="User Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Create, search, edit and manage system accounts.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search Users:"
        ).pack(side="left", padx=(0, 10))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_users()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_users
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # USER TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "username",
            "full_name",
            "role",
            "status",
            "created_at",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "username": "Username",
            "full_name": "Full Name",
            "role": "Role",
            "status": "Account Status",
            "created_at": "Created At",
        }

        widths = {
            "id": 55,
            "username": 150,
            "full_name": 220,
            "role": 100,
            "status": 130,
            "created_at": 170,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column]
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
            yscrollcommand=scrollbar.set
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
            lambda event: self.edit_selected_user()
        )

    # --------------------------------------------------
    # ACTION BUTTONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Create User",
            command=self.on_create,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit User",
            command=self.edit_selected_user,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Change Status",
            command=self.change_status,
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_users,
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD USERS
    # --------------------------------------------------

    def load_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            search_term = self.search_var.get().strip()

            if search_term:
                users = search_users(
                    search_term,
                    actor_user_id=self.user["id"],
                )
            else:
                users = get_users(
                    actor_user_id=self.user["id"],
                )

            for account in users:
                status = (
                    "Active"
                    if account["is_active"]
                    else "Inactive"
                )

                self.tree.insert(
                    "",
                    "end",
                    iid=str(account["id"]),
                    values=(
                        account["id"],
                        account["username"],
                        account["full_name"],
                        account["role"].upper(),
                        status,
                        account["created_at"] or "-",
                    ),
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load user accounts:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_user_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a user account first.",
                parent=self,
            )
            return None

        return int(selection[0])

    def edit_selected_user(self):
        user_id = self.get_selected_user_id()

        if user_id is not None:
            self.on_edit(user_id)

    # --------------------------------------------------
    # ACCOUNT STATUS
    # --------------------------------------------------

    def change_status(self):
        user_id = self.get_selected_user_id()

        if user_id is None:
            return

        values = self.tree.item(
            str(user_id),
            "values",
        )

        current_status = values[4]
        activate = current_status == "Inactive"

        action = "activate" if activate else "deactivate"

        confirmed = messagebox.askyesno(
            "Confirm Account Status",
            f"Are you sure you want to {action} this account?",
            parent=self,
        )

        if not confirmed:
            return

        try:
            update_user_status(
                user_id,
                activate,
                actor_user_id=self.user["id"],
            )

            messagebox.showinfo(
                "Success",
                f"User account {action}d successfully.",
                parent=self,
            )

            self.load_users()

        except Exception as error:
            messagebox.showerror(
                "Account Status Error",
                str(error),
                parent=self,
            )

    # --------------------------------------------------
    # SEARCH RESET
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_users()
