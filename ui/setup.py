import tkinter as tk
from tkinter import ttk, messagebox

from services.auth_service import create_initial_admin


class SetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.setup_complete = False

        self.title("Administrator Setup")
        self.geometry("460x470")
        self.resizable(False, False)
        self.configure(padx=30, pady=25)

        ttk.Label(
            self,
            text="School Management System",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(10, 5))

        ttk.Label(
            self,
            text="Create your first administrator account"
        ).pack(pady=(0, 25))

        form = ttk.Frame(self)
        form.pack(fill="x")

        # Username
        ttk.Label(form, text="Administrator Username").pack(anchor="w")
        self.username = ttk.Entry(form)
        self.username.pack(fill="x", pady=(5, 15))

        # Full name
        ttk.Label(form, text="Full Name").pack(anchor="w")
        self.full_name = ttk.Entry(form)
        self.full_name.pack(fill="x", pady=(5, 15))

        # Password
        ttk.Label(form, text="Password").pack(anchor="w")
        self.password = ttk.Entry(form, show="*")
        self.password.pack(fill="x", pady=(5, 15))

        # Confirm password
        ttk.Label(form, text="Confirm Password").pack(anchor="w")
        self.confirm_password = ttk.Entry(form, show="*")
        self.confirm_password.pack(fill="x", pady=(5, 20))

        ttk.Label(
            form,
            text="Password must contain at least 8 characters.",
            foreground="gray"
        ).pack(anchor="w", pady=(0, 12))

        self.create_button = ttk.Button(
            form,
            text="Create Administrator",
            command=self.create_account
        )
        self.create_button.pack(fill="x", ipady=5)

        self.username.focus_set()

        self.confirm_password.bind(
            "<Return>",
            lambda event: self.create_account()
        )

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def create_account(self):
        username = self.username.get().strip()
        full_name = self.full_name.get().strip()
        password = self.password.get()
        confirm_password = self.confirm_password.get()

        if not username or not full_name or not password or not confirm_password:
            messagebox.showwarning(
                "Missing Information",
                "Please complete all fields.",
                parent=self
            )
            return

        if len(username) < 3 or len(username) > 30:
            messagebox.showwarning(
                "Invalid Username",
                "Username must contain between 3 and 30 characters.",
                parent=self
            )
            return

        if not username.replace("_", "").replace("-", "").isalnum():
            messagebox.showwarning(
                "Invalid Username",
                "Use only letters, numbers, underscores, and hyphens.",
                parent=self
            )
            return

        if password != confirm_password:
            messagebox.showerror(
                "Password Error",
                "The passwords do not match.",
                parent=self
            )
            self.confirm_password.focus_set()
            return

        try:
            create_initial_admin(
                username=username,
                password=password,
                full_name=full_name
            )

            self.setup_complete = True

            messagebox.showinfo(
                "Setup Complete",
                "Administrator account created successfully.\n"
                "You can now sign in.",
                parent=self
            )

            self.destroy()

        except ValueError as error:
            messagebox.showerror(
                "Setup Error",
                str(error),
                parent=self
            )

        except Exception as error:
            messagebox.showerror(
                "Unexpected Error",
                f"Could not create administrator account:\n{error}",
                parent=self
            )

    def close_window(self):
        if messagebox.askyesno(
            "Exit Setup",
            "Are you sure you want to close the application?",
            parent=self
        ):
            self.destroy()
