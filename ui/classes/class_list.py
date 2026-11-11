import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import get_classes


class ClassListFrame(ttk.Frame):

    def __init__(self, master, on_create, on_edit, *, user):
        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_classes()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Class Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search and manage school classes.",
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
            text="Search Classes:"
        ).pack(side="left", padx=(0, 10))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=35
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_classes()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_classes
        ).pack(side="left", padx=5)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=5)

    # --------------------------------------------------
    # TABLE
    # --------------------------------------------------

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id",
            "name",
            "description",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "id": "ID",
            "name": "Class Name",
            "description": "Description",
        }

        widths = {
            "id": 65,
            "name": 200,
            "description": 450,
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
            lambda event: self.edit_class()
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Class",
            command=self.on_create
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Class",
            command=self.edit_class
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_classes
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_classes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            classes = get_classes(
                self.search_var.get(),
                actor_user_id=self.user["id"],
            )

            for school_class in classes:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        school_class["id"],
                        school_class["name"],
                        school_class["description"] or "-",
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load class records:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_class_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a class first.",
                parent=self
            )
            return None

        values = self.tree.item(
            selection[0],
            "values"
        )

        return int(values[0])

    # --------------------------------------------------
    # EDIT
    # --------------------------------------------------

    def edit_class(self):
        class_id = self.get_selected_class_id()

        if class_id is not None:
            self.on_edit(class_id)

    # --------------------------------------------------
    # CLEAR SEARCH
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.load_classes()
