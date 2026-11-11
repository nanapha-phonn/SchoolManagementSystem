import tkinter as tk
from tkinter import ttk, messagebox

from services.user_service import (
    create_user,
    update_user,
)


class UserForm(ttk.Frame):

    def __init__(
        self,
        master,
        on_back=None,
        on_saved=None,
        account=None,
        *,
        user,
    ):
        super().__init__(master, padding=25)

        self.user = user
        self.account = account
        self.on_back = on_back
        self.on_saved = on_saved

        self.username_var = tk.StringVar()
        self.full_name_var = tk.StringVar()
        self.role_var = tk.StringVar(value="staff")
        self.password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()

        self.create_header()
        self.create_form()
        self.create_buttons()

        if self.account:
            self.load_account_data()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        title = (
            "Edit User Account"
            if self.account
            else "Create User Account"
        )

        description = (
            "Update account details and system permissions."
            if self.account
            else "Create a new administrator or staff account."
        )

        ttk.Label(
            self,
            text=title,
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=description,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 20))

    # --------------------------------------------------
    # FORM
    # --------------------------------------------------

    def create_form(self):
        form = ttk.LabelFrame(
            self,
            text="Account Information",
            padding=20,
        )
        form.pack(fill="x", anchor="n")

        form.columnconfigure(1, weight=1)

        fields = [
            ("Username", self.username_var),
            ("Full Name", self.full_name_var),
        ]

        for row, (label_text, variable) in enumerate(fields):
            ttk.Label(
                form,
                text=label_text,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=8,
                pady=10,
            )

            ttk.Entry(
                form,
                textvariable=variable,
                width=40,
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                padx=8,
                pady=10,
            )

        ttk.Label(
            form,
            text="Role",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=8,
            pady=10,
        )

        self.role_combo = ttk.Combobox(
            form,
            textvariable=self.role_var,
            values=("admin", "staff"),
            state="readonly",
            width=37,
        )
        self.role_combo.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )

        if not self.account:
            ttk.Separator(
                form,
                orient="horizontal",
            ).grid(
                row=3,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=8,
                pady=12,
            )

            ttk.Label(
                form,
                text="Password",
            ).grid(
                row=4,
                column=0,
                sticky="w",
                padx=8,
                pady=10,
            )

            ttk.Entry(
                form,
                textvariable=self.password_var,
                show="*",
                width=40,
            ).grid(
                row=4,
                column=1,
                sticky="ew",
                padx=8,
                pady=10,
            )

            ttk.Label(
                form,
                text="Confirm Password",
            ).grid(
                row=5,
                column=0,
                sticky="w",
                padx=8,
                pady=10,
            )

            ttk.Entry(
                form,
                textvariable=self.confirm_password_var,
                show="*",
                width=40,
            ).grid(
                row=5,
                column=1,
                sticky="ew",
                padx=8,
                pady=10,
            )

            ttk.Label(
                form,
                text="Password must contain at least 8 characters and no more than 72 UTF-8 bytes.",
                wraplength=520,
                font=("Segoe UI", 9),
            ).grid(
                row=6,
                column=1,
                sticky="w",
                padx=8,
                pady=(2, 8),
            )

        else:
            ttk.Label(
                form,
                text="To change this user's password, use the password change function after signing in as that user.",
                wraplength=520,
                font=("Segoe UI", 9),
            ).grid(
                row=3,
                column=0,
                columnspan=2,
                sticky="w",
                padx=8,
                pady=(12, 5),
            )

    # --------------------------------------------------
    # LOAD ACCOUNT
    # --------------------------------------------------

    def load_account_data(self):
        self.username_var.set(
            self.account["username"]
        )

        self.full_name_var.set(
            self.account["full_name"]
        )

        self.role_var.set(
            self.account["role"]
        )

    # --------------------------------------------------
    # BUTTONS
    # --------------------------------------------------

    def create_buttons(self):
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=20)

        save_text = (
            "Update Account"
            if self.account
            else "Create Account"
        )

        ttk.Button(
            buttons,
            text=save_text,
            command=self.save_account,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Clear Form",
            command=self.clear_form,
        ).pack(side="right", padx=5)

        ttk.Button(
            buttons,
            text="Back to Users",
            command=self.go_back,
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # SAVE ACCOUNT
    # --------------------------------------------------

    def save_account(self):
        username = self.username_var.get().strip()
        full_name = self.full_name_var.get().strip()
        role = self.role_var.get()

        if not username:
            messagebox.showwarning(
                "Validation Error",
                "Username is required.",
                parent=self,
            )
            return

        if not full_name:
            messagebox.showwarning(
                "Validation Error",
                "Full name is required.",
                parent=self,
            )
            return

        if not role:
            messagebox.showwarning(
                "Validation Error",
                "Please select an account role.",
                parent=self,
            )
            return

        try:
            if self.account:
                update_user(
                    self.account["id"],
                    username,
                    full_name,
                    role,
                    actor_user_id=self.user["id"],
                )

                message = "User account updated successfully."

            else:
                password = self.password_var.get()
                confirm_password = self.confirm_password_var.get()

                if password != confirm_password:
                    messagebox.showwarning(
                        "Validation Error",
                        "Passwords do not match.",
                        parent=self,
                    )
                    return

                create_user(
                    username,
                    password,
                    full_name,
                    role,
                    actor_user_id=self.user["id"],
                )

                message = "User account created successfully."

            messagebox.showinfo(
                "Success",
                message,
                parent=self,
            )

            if self.on_saved:
                self.on_saved()

        except (ValueError, PermissionError) as error:
            messagebox.showerror(
                "Account Error",
                str(error),
                parent=self,
            )

        except Exception as error:
            messagebox.showerror(
                "Unexpected Error",
                f"Could not save the user account:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # CLEAR FORM
    # --------------------------------------------------

    def clear_form(self):
        if self.account:
            self.load_account_data()
            return

        self.username_var.set("")
        self.full_name_var.set("")
        self.role_var.set("staff")
        self.password_var.set("")
        self.confirm_password_var.set("")

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    def go_back(self):
        if self.on_back:
            self.on_back()
