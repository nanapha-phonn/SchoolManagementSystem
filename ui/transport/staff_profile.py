from tkinter import ttk

from ui.documents.document_panel import DocumentPanel


class TransportStaffProfile(ttk.Frame):

    def __init__(self, master, staff, on_back, on_edit, user=None):
        super().__init__(master, padding=25)

        self.staff = staff
        self.on_back = on_back
        self.on_edit = on_edit
        self.user = user

        self.create_header()
        self.create_profile()

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Transport Staff Profile",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Complete driver or attendant information.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))

    def create_profile(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        information_tab = ttk.Frame(notebook, padding=12)
        documents_tab = ttk.Frame(notebook, padding=12)

        notebook.add(information_tab, text="Information")
        notebook.add(documents_tab, text="Documents")

        container = ttk.LabelFrame(
            information_tab,
            text="Transport Staff Information",
            padding=20,
        )
        container.pack(fill="both", expand=True)

        details = [
            ("Staff ID", self.staff.get("id")),
            ("Employee Number", self.staff.get("employee_no")),
            ("First Name", self.staff.get("first_name")),
            ("Last Name", self.staff.get("last_name")),
            ("Role", self.staff.get("role")),
            ("Phone", self.staff.get("phone")),
            ("Email", self.staff.get("email")),
            ("License Number", self.staff.get("license_number")),
            ("Status", self.staff.get("status")),
            ("Registration Date", self.staff.get("created_at")),
        ]

        for index, (label, value) in enumerate(details):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(
                container,
                text=f"{label}:",
                font=("Segoe UI", 10, "bold"),
            ).grid(
                row=row,
                column=column,
                sticky="nw",
                padx=10,
                pady=12,
            )

            ttk.Label(
                container,
                text=str(value) if value not in (None, "") else "-",
                font=("Segoe UI", 10),
                wraplength=280,
            ).grid(
                row=row,
                column=column + 1,
                sticky="nw",
                padx=10,
                pady=12,
            )

        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

        self.create_documents_tab(
            documents_tab,
            owner_type="transport_staff",
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(15, 0))

        ttk.Button(
            buttons,
            text="Back to Staff Records",
            command=self.on_back,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Edit Staff",
            command=self.on_edit,
        ).pack(side="right", padx=5)

    def create_documents_tab(self, parent, owner_type):
        if self.user is None:
            ttk.Label(
                parent,
                text=(
                    "Document access requires an authenticated user. "
                    "Open this profile from the dashboard."
                ),
                wraplength=650,
            ).pack(anchor="w", padx=10, pady=10)
            return

        self.document_panel = DocumentPanel(
            parent,
            owner_type=owner_type,
            owner_id=self.staff["id"],
            user=self.user,
        )
        self.document_panel.pack(fill="both", expand=True)
