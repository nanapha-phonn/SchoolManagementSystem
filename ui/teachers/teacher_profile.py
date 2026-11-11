from tkinter import ttk

from ui.documents.document_panel import DocumentPanel


class TeacherProfile(ttk.Frame):

    def __init__(self, master, teacher, on_back, on_edit, user=None):
        super().__init__(master, padding=25)

        self.teacher = teacher
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
            text="Teacher Profile",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Complete employee information and employment details.",
            font=("Segoe UI", 10)
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
            text="Teacher Information",
            padding=20
        )
        container.pack(fill="both", expand=True)

        details = [
            ("Teacher ID", self.teacher.get("id")),
            ("Employee Number", self.teacher.get("employee_no")),
            ("First Name", self.teacher.get("first_name")),
            ("Last Name", self.teacher.get("last_name")),
            ("Date of Birth", self.teacher.get("date_of_birth")),
            ("Gender", self.teacher.get("gender")),
            ("Phone", self.teacher.get("phone")),
            ("Email", self.teacher.get("email")),
            ("Address", self.teacher.get("address")),
            ("Qualification", self.teacher.get("qualification")),
            ("Specialization", self.teacher.get("specialization")),
            ("Department", self.teacher.get("department")),
            ("Employment Date", self.teacher.get("employment_date")),
            ("Status", self.teacher.get("status")),
            ("Registration Date", self.teacher.get("created_at")),
        ]

        for index, (label, value) in enumerate(details):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(
                container,
                text=label + ":",
                font=("Segoe UI", 10, "bold")
            ).grid(
                row=row,
                column=column,
                sticky="nw",
                padx=10,
                pady=12
            )

            ttk.Label(
                container,
                text=value or "-",
                font=("Segoe UI", 10),
                wraplength=280
            ).grid(
                row=row,
                column=column + 1,
                sticky="nw",
                padx=10,
                pady=12
            )

        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

        self.create_documents_tab(
            documents_tab,
            owner_type="teacher",
        )

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(15, 0))

        ttk.Button(
            buttons,
            text="Back to Records",
            command=self.on_back
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Edit Teacher",
            command=self.on_edit
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
            owner_id=self.teacher["id"],
            user=self.user,
        )
        self.document_panel.pack(fill="both", expand=True)
