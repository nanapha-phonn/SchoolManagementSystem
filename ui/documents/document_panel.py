import os
import shutil
import tempfile
import tkinter as tk

from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from services.document_service import (
    archive_document,
    get_documents,
    open_document,
)


OWNER_LABELS = {
    "student": "Student",
    "teacher": "Teacher",
    "transport_staff": "Transport Staff",
}


class DocumentPanel(ttk.Frame):
    """
    Displays documents belonging to one student, teacher, or transport
    staff member.

    All document operations go through document_service. The panel never
    accesses the database or document storage directory directly.
    """

    def __init__(self, master, owner_type, owner_id, user):
        super().__init__(master, padding=12)

        if owner_type not in OWNER_LABELS:
            raise ValueError("Unsupported document owner type.")

        self.owner_type = owner_type
        self.owner_id = owner_id
        self.user = user
        self.actor_user_id = user["id"]

        self.documents_by_id = {}

        self.status_var = tk.StringVar(master=self, value="Active")

        self.create_widgets()
        self.load_documents()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 12))

        ttk.Label(
            toolbar,
            text="Documents",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        ttk.Label(
            toolbar,
            text="Status:",
        ).pack(side="left", padx=(20, 5))

        status_filter = ttk.Combobox(
            toolbar,
            textvariable=self.status_var,
            state="readonly",
            width=12,
            values=("Active", "Archived", "All"),
        )
        status_filter.pack(side="left")
        status_filter.bind(
            "<<ComboboxSelected>>",
            self.on_status_changed,
        )

        ttk.Button(
            toolbar,
            text="Refresh",
            command=self.load_documents,
        ).pack(side="right", padx=(5, 0))

        ttk.Button(
            toolbar,
            text="Download Selected",
            command=self.download_selected,
        ).pack(side="right", padx=5)

        if self.user.get("role") == "admin":
            self.archive_button = ttk.Button(
                toolbar,
                text="Archive Selected",
                command=self.archive_selected,
            )
            self.archive_button.pack(side="right", padx=5)
        else:
            self.archive_button = None

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = (
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
            height=12,
        )

        headings = {
            "category": ("Category", 150, "w"),
            "title": ("Document Title", 190, "w"),
            "filename": ("Original Filename", 190, "w"),
            "size": ("Size", 90, "e"),
            "uploaded": ("Uploaded", 145, "center"),
            "status": ("Status", 90, "center"),
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

        self.tree.bind(
            "<Double-1>",
            lambda event: self.download_selected(),
        )

    # --------------------------------------------------
    # DATA
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

    def on_status_changed(self, event=None):
        self.load_documents()

    def load_documents(self):
        status_values = {
            "Active": "active",
            "Archived": "archived",
            "All": None,
        }

        status = status_values.get(self.status_var.get(), "active")

        try:
            documents = get_documents(
                owner_type=self.owner_type,
                owner_id=self.owner_id,
                status=status,
                actor_user_id=self.actor_user_id,
            )
        except Exception:
            messagebox.showerror(
                "Document Error",
                "Could not load documents. Please check your access "
                "and try again.",
                parent=self.winfo_toplevel(),
            )
            return

        self.documents_by_id = {}

        for item in self.tree.get_children():
            self.tree.delete(item)

        for document in documents:
            document_id = int(document["id"])
            self.documents_by_id[document_id] = document

            self.tree.insert(
                "",
                "end",
                iid=str(document_id),
                values=(
                    self.format_category(document.get("category")),
                    document.get("title") or "-",
                    document.get("original_filename") or "-",
                    self.format_size(document.get("size_bytes")),
                    document.get("created_at") or "-",
                    str(document.get("status") or "").title(),
                ),
                tags=(
                    "archived",
                ) if document.get("status") == "archived" else (),
            )

        self.tree.tag_configure(
            "archived",
            foreground="#777777",
        )

        if documents:
            self.empty_label.pack_forget()
        else:
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
    # DOWNLOAD
    # --------------------------------------------------

    def download_selected(self):
        document = self.get_selected_document()

        if document is None:
            return

        original_filename = document.get("original_filename") or "document"
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
            # open_document verifies the file's stored hash and size.
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

            # Replace the destination only after the verified copy completes.
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
