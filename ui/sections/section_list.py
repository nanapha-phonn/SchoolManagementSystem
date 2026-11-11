import tkinter as tk
from tkinter import ttk, messagebox

from services.class_service import get_classes
from services.section_service import (
    get_sections,
)


class SectionListFrame(ttk.Frame):

    ALL_CLASSES = "All Classes"

    def __init__(self, master, on_create, on_edit, *, user):
        super().__init__(master, padding=25)

        self.user = user
        self.on_create = on_create
        self.on_edit = on_edit

        self.search_var = tk.StringVar()
        self.class_filter_var = tk.StringVar(
            value=self.ALL_CLASSES
        )

        self.class_id_by_label = {
            self.ALL_CLASSES: None
        }

        self.create_header()
        self.create_search()
        self.create_table()
        self.create_actions()

        self.load_class_filters()
        self.load_sections()

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 20))

        ttk.Label(
            header,
            text="Section Management",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Register, search and manage class sections.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 0))

    # --------------------------------------------------
    # CLASS FILTER
    # --------------------------------------------------

    def load_class_filters(self):
        try:
            classes = get_classes(actor_user_id=self.user["id"])

            self.class_id_by_label = {
                self.ALL_CLASSES: None
            }

            labels = [self.ALL_CLASSES]

            for school_class in classes:
                class_id = int(school_class["id"])
                label = f"{class_id} - {school_class['name']}"

                labels.append(label)
                self.class_id_by_label[label] = class_id

            self.class_filter_box["values"] = labels

            if self.class_filter_var.get() not in labels:
                self.class_filter_var.set(self.ALL_CLASSES)

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load class filters:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    def create_search(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 15))

        ttk.Label(
            search_frame,
            text="Search:"
        ).pack(side="left", padx=(0, 5))

        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=25
        )
        search_entry.pack(side="left", padx=5)

        search_entry.bind(
            "<Return>",
            lambda event: self.load_sections()
        )

        ttk.Label(
            search_frame,
            text="Class:"
        ).pack(side="left", padx=(12, 5))

        self.class_filter_box = ttk.Combobox(
            search_frame,
            textvariable=self.class_filter_var,
            state="readonly",
            width=25
        )

        self.class_filter_box.pack(side="left", padx=5)

        self.class_filter_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_sections()
        )

        ttk.Button(
            search_frame,
            text="Search",
            command=self.load_sections
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
            "section",
            "class",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        headings = {
            "id": "ID",
            "section": "Section Name",
            "class": "Class",
        }

        widths = {
            "id": 65,
            "section": 220,
            "class": 220,
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
            lambda event: self.edit_section()
        )

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------

    def create_actions(self):
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(15, 0))

        ttk.Button(
            actions,
            text="Register Section",
            command=self.on_create
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Edit Section",
            command=self.edit_section
        ).pack(side="left", padx=4)

        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh
        ).pack(side="right", padx=4)

    # --------------------------------------------------
    # LOAD RECORDS
    # --------------------------------------------------

    def load_sections(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        class_id = self.class_id_by_label.get(
            self.class_filter_var.get()
        )

        try:
            sections = get_sections(
                search=self.search_var.get(),
                class_id=class_id,
                actor_user_id=self.user["id"],
            )

            for section in sections:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        section["id"],
                        section["name"],
                        section["class_name"],
                    )
                )

        except Exception as error:
            messagebox.showerror(
                "Loading Error",
                f"Could not load section records:\n{error}",
                parent=self
            )

    # --------------------------------------------------
    # REFRESH
    # --------------------------------------------------

    def refresh(self):
        self.load_class_filters()
        self.load_sections()

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_section_id(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a section first.",
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

    def edit_section(self):
        section_id = self.get_selected_section_id()

        if section_id is not None:
            self.on_edit(section_id)

    # --------------------------------------------------
    # CLEAR SEARCH
    # --------------------------------------------------

    def clear_search(self):
        self.search_var.set("")
        self.class_filter_var.set(self.ALL_CLASSES)
        self.load_sections()


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Section Management")
    root.geometry("1000x650")

    def unavailable_action():
        messagebox.showinfo(
            "Navigation",
            "Open this screen through the main dashboard."
        )

    page = SectionListFrame(
        root,
        on_create=unavailable_action,
        on_edit=lambda section_id: unavailable_action()
    )

    page.pack(fill="both", expand=True)
    root.mainloop()
