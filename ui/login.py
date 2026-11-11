import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import APP_TITLE
from services.auth_service import authenticate_user
from ui.dashboard import DashboardWindow


class LoginWindow(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("460x350")
        self.minsize(420, 320)
        self.configure(padx=28, pady=24)

        self.dashboard = None

        ttk.Label(
            self,
            text=APP_TITLE,
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(10, 6))

        ttk.Label(
            self,
            text="Sign in to continue"
        ).pack(pady=(0, 22))

        form = ttk.Frame(self)
        form.pack(fill="x")

        ttk.Label(form, text="Username").pack(anchor="w")

        self.username = ttk.Entry(form)
        self.username.pack(fill="x", pady=(4, 14))

        ttk.Label(form, text="Password").pack(anchor="w")

        self.password = ttk.Entry(form, show="*")
        self.password.pack(fill="x", pady=(4, 18))

        ttk.Button(
            form,
            text="Sign in",
            command=self.login
        ).pack(fill="x", ipady=4)

        ttk.Label(
            self,
            text="Please enter your account credentials.",
            foreground="gray"
        ).pack(pady=18)

        self.username.focus_set()

        self.password.bind(
            "<Return>",
            lambda event: self.login()
        )

    def login(self):
        username = self.username.get()
        password = self.password.get()

        if not username or not password:
            messagebox.showwarning(
                "Missing Information",
                "Please enter your username and password.",
                parent=self
            )
            return

        try:
            user = authenticate_user(username, password)
        except Exception as error:
            messagebox.showerror(
                "Login Error",
                f"Could not authenticate user:\n{error}",
                parent=self
            )
            return

        if user is None:
            messagebox.showerror(
                "Login Failed",
                "Invalid username or password.",
                parent=self
            )
            self.password.delete(0, tk.END)
            self.password.focus_set()
            return

        self.password.delete(0, tk.END)
        self.withdraw()

        self.dashboard = DashboardWindow(
            master=self,
            user=user,
            on_logout=self.handle_logout
        )

    def handle_logout(self):
        self.dashboard = None
        self.deiconify()
        self.password.delete(0, tk.END)
        self.username.focus_set()