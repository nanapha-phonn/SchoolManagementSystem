import os
import shutil
import tempfile
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from models.document import (
    VALID_CATEGORIES_BY_OWNER,
    VALID_DOCUMENT_CATEGORIES,
)
from services.document_service import (
    archive_document,
    get_documents,
    open_document,
)
from services.student_service import get_students
from services.teacher_service import get_teachers
from services.transport_staff_service import get_transport_staff_list
from ui.documents.document_upload_dialog import DocumentUploadDialog


OWNER_LABELS = {
    "student": "Student",
    "teacher": "Teacher",
    "transport_staff": "Transport Staff",
}

OWNER_FILTER_OPTIONS = {
    "All Owners": None,
    "Student": "student",
    "Teacher": "teacher",
    "Transport Staff": "transport_staff",
}

STATUS_FILTER_OPTIONS = {
    "Active": "active",
    "Archived": "archived",
    "All": None,
}


class DocumentListFrame(ttk.Frame):
    """Search, filter, upload, download, and archive all documents."""

    def __init__(self, master, user):
        super().__init__(master, padding=18)

        self.user = user
        self.actor_user_id = user["id"]

        self.documents_by_id = {}
        self.owner_labels = {}
        self.owner_labels_loaded = False
        self.category_codes = {}

        self.search_var = tk.StringVar(master=self)
        self.owner_type_var = tk.StringVar(
            master=self,
            value="All Owners",
        )
        self.category_var = tk.StringVar(
            master=self,
            value="All Categories",
        )
        self.status_var = tk.StringVar(
            master=self,
            value="Active",
        )

        self.create_widgets()
        self.load_categories()
        self.load_documents()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def create_widgets(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 15))

        heading_frame = ttk.Frame(header)
        heading_frame.pack(side="left", fill="x", expand=True)

        ttk.Label(
            heading_frame,
            text="Document Management",
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            heading_frame,
            text="Manage documents attached to students, teachers, "
                 "and transport staff.",
            foreground="#64748B",
        ).pack(anchor="w", pady=(4, 0))

        ttk.Button(
            header,
            text="Upload Document",
            command=self.open_upload_dialog,
        ).pack(side="right", padx=(10, 0), pady=8)

        filters = ttk.LabelFrame(
            self,
            text="Search and Filters",
            padding=10,
        )
        filters.pack(fill="x", pady=(0, 12))

        filters.columnconfigure(1, weight=1)

        ttk.Label(
            filters,
            text="Search:",
        ).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=5)

        self.search_entry = ttk.Entry(
            filters,
            textvariable=self.search_var,
            width=25,
        )
        self.search_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 6),
            pady=5,
        )
        self.search_entry.bind(
            "<Return>",
            lambda event: self.load_documents(),
        )

        ttk.Button(
            filters,
            text="Search",
            command=self.load_documents,
        ).grid(row=0, column=2, padx=(0, 12), pady=5)

        ttk.Label(
            filters,
            text="Owner:",
        ).grid(row=0, column=3, sticky="w", padx=(0, 5), pady=5)

        self.owner_type_combo = ttk.Combobox(
            filters,
            textvariable=self.owner_type_var,
            state="readonly",
            width=15,
            values=tuple(OWNER_FILTER_OPTIONS),
        )
        self.owner_type_combo.grid(
            row=0,
            column=4,
            padx=(0, 12),
            pady=5,
        )
        self.owner_type_combo.bind(
            "<<ComboboxSelected>>",
            self.on_owner_type_changed,
        )

        ttk.Label(
            filters,
            text="Category:",
        ).grid(row=0, column=5, sticky="w", padx=(0, 5), pady=5)

        self.category_combo = ttk.Combobox(
            filters,
            textvariable=self.category_var,
            state="readonly",
            width=22,
        )
        self.category_combo.grid(
            row=0,
            column=6,
            padx=(0, 12),
            pady=5,
        )
        self.category_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_documents(),
        )

        ttk.Label(
            filters,
            text="Status:",
        ).grid(row=0, column=7, sticky="w", padx=(0, 5), pady=5)

        self.status_combo = ttk.Combobox(
            filters,
            textvariable=self.status_var,
            state="readonly",
            width=11,
            values=tuple(STATUS_FILTER_OPTIONS),
        )
        self.status_combo.grid(
            row=0,
            column=8,
            pady=5,
        )
        self.status_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_documents(),
        )

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 8))

        ttk.Button(
            actions,
            text="Refresh",
            command=self.load_documents,
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Download Selected",
            command=self.download_selected,
        ).pack(side="right", padx=(5, 0))

        if self.user.get("role") == "admin":
            self.archive_button = ttk.Button(
                actions,
                text="Archive Selected",
                command=self.archive_selected,
            )
            self.archive_button.pack(side="right", padx=5)
        else:
            self.archive_button = None

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "owner_type",
            "owner",
            "category",
            "title",
            "filename",
            "size",
            "uploaded",
            "status",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "owner_type": ("Owner Type", 110, "w"),
            "owner": ("Owner Record", 190, "w"),
            "category": ("Category", 155, "w"),
            "title": ("Document Title", 180, "w"),
            "filename": ("Original Filename", 180, "w"),
            "size": ("Size", 85, "e"),
            "uploaded": ("Uploaded", 145, "center"),
            "status": ("Status", 85, "center"),
        }

        for column, (heading, width, anchor) in headings.items():
            self.tree.heading(column, text=heading)
            self.tree.column(
                column,
                width=width,
                minwidth=70,
                anchor=anchor,
                stretch=True,
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.empty_label = ttk.Label(
            self,
            text="No documents found.",
            font=("Segoe UI", 10),
        )
        self.empty_label.pack(anchor="center", pady=12)

        self.tree.tag_configure(
            "archived",
            foreground="#777777",
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self.download_selected(),
        )

    # --------------------------------------------------
    # FORMATTING AND FILTERS
    # --------------------------------------------------

    @staticmethod
    def format_category(category):
        return str(category or "").replace("_", " ").title()

    @staticmethod
    def format_size(size_bytes):
        size_bytes = int(size_bytes or 0)

        if size_bytes < 1024:
            return f"{size_bytes} B"

        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"

        return f"{size_bytes / (1024 * 1024):.2f} MB"

    def load_categories(self):
        owner_type = OWNER_FILTER_OPTIONS.get(
            self.owner_type_var.get()
        )

        if owner_type is None:
            categories = sorted(VALID_DOCUMENT_CATEGORIES)
        else:
            categories = sorted(
                VALID_CATEGORIES_BY_OWNER[owner_type]
            )

        self.category_codes = {
            self.format_category(category): category
            for category in categories
        }

        values = ("All Categories", *self.category_codes.keys())

        self.category_combo.configure(values=values)

        current_category = self.category_var.get()

        if current_category not in values:
            self.category_var.set("All Categories")

    def on_owner_type_changed(self, event=None):
        self.load_categories()
        self.load_documents()

    # --------------------------------------------------
    # OWNER DISPLAY
    # --------------------------------------------------

    def load_owner_labels(self):
        """Load readable owner labels through existing service APIs."""

        if self.owner_labels_loaded:
            return

        owner_services = (
            (
                "student",
                lambda: get_students(
                    actor_user_id=self.actor_user_id,
                ),
            ),
            (
                "teacher",
                lambda: get_teachers(
                    actor_user_id=self.actor_user_id,
                ),
            ),
            (
                "transport_staff",
                get_transport_staff_list,
            ),
        )

        for owner_type, loader in owner_services:
            try:
                records = loader()
            except Exception:
                # Documents remain accessible using a type and record ID.
                continue

            for record in records:
                record_id = int(record["id"])

                if owner_type == "student":
                    reference = record.get("admission_no")
                else:
                    reference = record.get("employee_no")

                full_name = " ".join(
                    str(record.get(field) or "").strip()
                    for field in ("first_name", "last_name")
                ).strip()

                if reference and full_name:
                    label = f"{reference} — {full_name}"
                elif full_name:
                    label = full_name
                elif reference:
                    label = str(reference)
                else:
                    label = f"ID {record_id}"

                self.owner_labels[(owner_type, record_id)] = label

        self.owner_labels_loaded = True

    def get_document_owner(self, document):
        owner_columns = (
            ("student", "student_id"),
            ("teacher", "teacher_id"),
            ("transport_staff", "transport_staff_id"),
        )

        for owner_type, owner_column in owner_columns:
            owner_id = document.get(owner_column)

            if owner_id is None:
                continue

            owner_id = int(owner_id)

            owner_label = self.owner_labels.get(
                (owner_type, owner_id),
                f"ID {owner_id}",
            )

            return OWNER_LABELS[owner_type], owner_label

        return "Unknown", "Unknown owner"

    # --------------------------------------------------
    # DATA
    # --------------------------------------------------

    def load_documents(self):
        owner_type = OWNER_FILTER_OPTIONS.get(
            self.owner_type_var.get()
        )

        category = self.category_codes.get(
            self.category_var.get()
        )

        status = STATUS_FILTER_OPTIONS.get(
            self.status_var.get(),
            "active",
        )

        try:
            documents = get_documents(
                search=self.search_var.get().strip(),
                owner_type=owner_type,
                category=category,
                status=status,
                actor_user_id=self.actor_user_id,
            )

        except Exception:
            self.documents_by_id = {}

            for item in self.tree.get_children():
                self.tree.delete(item)

            self.empty_label.configure(
                text="Could not load documents.",
            )
            self.empty_label.pack(anchor="center", pady=12)

            messagebox.showerror(
                "Document Error",
                "Could not load documents. Please check your access "
                "and try again.",
                parent=self.winfo_toplevel(),
            )
            return

        if documents and not self.owner_labels_loaded:
            self.load_owner_labels()

        self.documents_by_id = {}

        for item in self.tree.get_children():
            self.tree.delete(item)

        for document in documents:
            document_id = int(document["id"])
            self.documents_by_id[document_id] = document

            owner_type_label, owner_label = self.get_document_owner(
                document
            )

            self.tree.insert(
                "",
                "end",
                iid=str(document_id),
                values=(
                    owner_type_label,
                    owner_label,
                    self.format_category(document.get("category")),
                    document.get("title") or "-",
                    document.get("original_filename") or "-",
                    self.format_size(document.get("size_bytes")),
                    document.get("created_at") or "-",
                    str(document.get("status") or "").title(),
                ),
                tags=(
                    ("archived",)
                    if document.get("status") == "archived"
                    else ()
                ),
            )

        if documents:
            self.empty_label.pack_forget()
        else:
            self.empty_label.configure(
                text="No documents found.",
            )
            self.empty_label.pack(anchor="center", pady=12)

    # --------------------------------------------------
    # SELECTION
    # --------------------------------------------------

    def get_selected_document(self):
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning(
                "No Document Selected",
                "Please select a document first.",
                parent=self.winfo_toplevel(),
            )
            return None

        try:
            document_id = int(selection[0])
        except (TypeError, ValueError):
            return None

        return self.documents_by_id.get(document_id)

    # --------------------------------------------------
    # UPLOAD
    # --------------------------------------------------

    def open_upload_dialog(self):
        try:
            DocumentUploadDialog(
                self,
                user=self.user,
                on_uploaded=self.load_documents,
            )
        except Exception:
            messagebox.showerror(
                "Upload Error",
                "Could not open the document upload window.",
                parent=self.winfo_toplevel(),
            )

    # --------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------

    def download_selected(self):
        document = self.get_selected_document()

        if document is None:
            return

        original_filename = (
            document.get("original_filename") or "document"
        )
        extension = document.get("file_extension") or ""

        destination = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Document",
            initialfile=original_filename,
            defaultextension=extension,
            filetypes=(
                ("PDF files", "*.pdf"),
                ("JPEG images", "*.jpg *.jpeg"),
                ("PNG images", "*.png"),
                ("All files", "*.*"),
            ),
        )

        if not destination:
            return

        destination_path = Path(destination)
        temporary_path = None

        try:
            with open_document(
                document["id"],
                actor_user_id=self.actor_user_id,
            ) as source:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination_path.name}.",
                    suffix=".tmp",
                    dir=destination_path.parent,
                    delete=False,
                ) as temporary_file:
                    temporary_path = Path(temporary_file.name)

                    shutil.copyfileobj(source, temporary_file)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())

            os.replace(temporary_path, destination_path)
            temporary_path = None

            messagebox.showinfo(
                "Download Complete",
                "The document was downloaded successfully.",
                parent=self.winfo_toplevel(),
            )

        except Exception:
            messagebox.showerror(
                "Download Failed",
                "The document could not be downloaded. It may be missing "
                "or may have failed its integrity check.",
                parent=self.winfo_toplevel(),
            )

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    # --------------------------------------------------
    # ARCHIVE
    # --------------------------------------------------

    def archive_selected(self):
        if self.user.get("role") != "admin":
            messagebox.showerror(
                "Permission Denied",
                "Only administrators can archive documents.",
                parent=self.winfo_toplevel(),
            )
            return

        document = self.get_selected_document()

        if document is None:
            return

        if document.get("status") == "archived":
            messagebox.showinfo(
                "Already Archived",
                "This document is already archived.",
                parent=self.winfo_toplevel(),
            )
            return

        confirmed = messagebox.askyesno(
            "Archive Document",
            (
                f"Archive '{document.get('title') or 'this document'}'?\n\n"
                "The document will no longer appear in the active list. "
                "Its stored file will be retained."
            ),
            parent=self.winfo_toplevel(),
        )

        if not confirmed:
            return

        try:
            archive_document(
                document["id"],
                actor_user_id=self.actor_user_id,
            )

        except Exception:
            messagebox.showerror(
                "Archive Failed",
                "The document could not be archived.",
                parent=self.winfo_toplevel(),
            )
            return

        self.load_documents()
