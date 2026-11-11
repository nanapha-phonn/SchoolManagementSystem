import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from models.document import VALID_CATEGORIES_BY_OWNER
from services.document_service import upload_document
from services.student_service import get_students
from services.teacher_service import get_teachers
from services.transport_staff_service import get_transport_staff_list


OWNER_OPTIONS = {
    "Student": "student",
    "Teacher": "teacher",
    "Transport Staff": "transport_staff",
}


class DocumentUploadDialog(tk.Toplevel):
    """Modal dialog for uploading a document to an existing record."""

    def __init__(self, master, user, on_uploaded=None):
        super().__init__(master)

        self.user = user
        self.actor_user_id = user["id"]
        self.on_uploaded = on_uploaded

        self.title("Upload Document")
        self.geometry("620x610")
        self.minsize(560, 560)
        self.resizable(True, True)

        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.owner_type_var = tk.StringVar(
            master=self,
            value="Student",
        )
        self.owner_search_var = tk.StringVar(master=self)
        self.owner_var = tk.StringVar(master=self)
        self.category_var = tk.StringVar(master=self)
        self.title_var = tk.StringVar(master=self)
        self.file_var = tk.StringVar(
            master=self,
            value="No file selected",
        )

        self.selected_file_path = None
        self.owner_records = {}
        self.category_codes = {}

        self.create_widgets()
        self.load_categories()
        self.load_owners()

        self.grab_set()
        self.focus_set()

    @property
    def selected_owner_type(self):
        return OWNER_OPTIONS.get(self.owner_type_var.get())

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def create_widgets(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Upload a Document",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            container,
            text=(
                "Attach a PDF, JPG, or PNG file to a student, "
                "teacher, or transport staff record."
            ),
            wraplength=550,
        ).pack(anchor="w", pady=(5, 18))

        form = ttk.Frame(container)
        form.pack(fill="both", expand=True)

        form.columnconfigure(1, weight=1)

        ttk.Label(
            form,
            text="Record Type:",
        ).grid(row=0, column=0, sticky="w", pady=7, padx=(0, 12))

        self.owner_type_combo = ttk.Combobox(
            form,
            textvariable=self.owner_type_var,
            values=tuple(OWNER_OPTIONS),
            state="readonly",
            width=24,
        )
        self.owner_type_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=7,
        )
        self.owner_type_combo.bind(
            "<<ComboboxSelected>>",
            self.on_owner_type_changed,
        )

        ttk.Label(
            form,
            text="Find Record:",
        ).grid(row=1, column=0, sticky="w", pady=7, padx=(0, 12))

        owner_search_frame = ttk.Frame(form)
        owner_search_frame.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=7,
        )
        owner_search_frame.columnconfigure(0, weight=1)

        self.owner_search_entry = ttk.Entry(
            owner_search_frame,
            textvariable=self.owner_search_var,
        )
        self.owner_search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        self.owner_search_entry.bind(
            "<Return>",
            lambda event: self.load_owners(),
        )

        ttk.Button(
            owner_search_frame,
            text="Find",
            command=self.load_owners,
        ).grid(row=0, column=1, padx=(7, 0))

        ttk.Label(
            form,
            text="Select Record:",
        ).grid(row=2, column=0, sticky="w", pady=7, padx=(0, 12))

        self.owner_combo = ttk.Combobox(
            form,
            textvariable=self.owner_var,
            state="readonly",
        )
        self.owner_combo.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="Category:",
        ).grid(row=3, column=0, sticky="w", pady=7, padx=(0, 12))

        self.category_combo = ttk.Combobox(
            form,
            textvariable=self.category_var,
            state="readonly",
        )
        self.category_combo.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="Document Title:",
        ).grid(row=4, column=0, sticky="w", pady=7, padx=(0, 12))

        ttk.Entry(
            form,
            textvariable=self.title_var,
        ).grid(
            row=4,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="Description:",
        ).grid(row=5, column=0, sticky="nw", pady=7, padx=(0, 12))

        self.description_text = tk.Text(
            form,
            height=4,
            width=35,
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.description_text.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="File:",
        ).grid(row=6, column=0, sticky="w", pady=7, padx=(0, 12))

        file_frame = ttk.Frame(form)
        file_frame.grid(
            row=6,
            column=1,
            sticky="ew",
            pady=7,
        )
        file_frame.columnconfigure(0, weight=1)

        ttk.Label(
            file_frame,
            textvariable=self.file_var,
            wraplength=330,
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Button(
            file_frame,
            text="Browse...",
            command=self.browse_file,
        ).grid(row=0, column=1, padx=(7, 0))

        ttk.Label(
            form,
            text="Accepted: PDF, JPG, JPEG, PNG. Maximum size: 10 MB.",
            foreground="#64748B",
        ).grid(
            row=7,
            column=1,
            sticky="w",
            pady=(3, 12),
        )

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", pady=(15, 0))

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(side="right")

        self.upload_button = ttk.Button(
            buttons,
            text="Upload Document",
            command=self.submit_upload,
        )
        self.upload_button.pack(side="right", padx=(0, 8))

    # --------------------------------------------------
    # OWNER SELECTION
    # --------------------------------------------------

    def on_owner_type_changed(self, event=None):
        self.owner_var.set("")
        self.load_categories()
        self.load_owners()

    def load_owners(self):
        owner_type = self.selected_owner_type

        if owner_type is None:
            return

        search = self.owner_search_var.get().strip()

        try:
            if owner_type == "student":
                records = get_students(
                    search=search,
                    actor_user_id=self.actor_user_id,
                )

            elif owner_type == "teacher":
                records = get_teachers(
                    search=search,
                    actor_user_id=self.actor_user_id,
                )

            else:
                records = get_transport_staff_list(search=search)

        except Exception:
            self.owner_records = {}
            self.owner_combo.configure(values=())
            self.owner_var.set("")

            messagebox.showerror(
                "Record Lookup Failed",
                "Could not load the selected records. "
                "Please check your access and try again.",
                parent=self,
            )
            return

        self.owner_records = {}

        for record in records:
            record_id = int(record["id"])

            if owner_type == "student":
                reference = record.get("admission_no") or "Student"
            else:
                reference = record.get("employee_no") or "Employee"

            full_name = " ".join(
                str(record.get(field) or "").strip()
                for field in ("first_name", "last_name")
            ).strip()

            display = (
                f"{reference} — {full_name} (ID: {record_id})"
                if full_name
                else f"{reference} (ID: {record_id})"
            )

            self.owner_records[display] = record_id

        values = tuple(self.owner_records)

        self.owner_combo.configure(values=values)

        if values:
            self.owner_var.set(values[0])
        else:
            self.owner_var.set("")

    # --------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------

    @staticmethod
    def format_category(category):
        return str(category).replace("_", " ").title()

    def load_categories(self):
        owner_type = self.selected_owner_type

        if owner_type is None:
            return

        categories = sorted(
            VALID_CATEGORIES_BY_OWNER[owner_type]
        )

        self.category_codes = {
            self.format_category(category): category
            for category in categories
        }

        values = tuple(self.category_codes)

        self.category_combo.configure(values=values)

        default_category = next(
            (
                label
                for label, code in self.category_codes.items()
                if code == "other"
            ),
            values[0] if values else "",
        )

        self.category_var.set(default_category)

    # --------------------------------------------------
    # FILE SELECTION
    # --------------------------------------------------

    def browse_file(self):
        selected = filedialog.askopenfilename(
            parent=self,
            title="Select Document",
            filetypes=(
                ("Supported documents", "*.pdf *.jpg *.jpeg *.png"),
                ("PDF files", "*.pdf"),
                ("JPEG images", "*.jpg *.jpeg"),
                ("PNG images", "*.png"),
                ("All files", "*.*"),
            ),
        )

        if not selected:
            return

        self.selected_file_path = Path(selected)
        self.file_var.set(self.selected_file_path.name)

        if not self.title_var.get().strip():
            self.title_var.set(self.selected_file_path.stem)

    # --------------------------------------------------
    # UPLOAD
    # --------------------------------------------------

    def submit_upload(self):
        if self.selected_file_path is None:
            messagebox.showwarning(
                "File Required",
                "Please select a document file.",
                parent=self,
            )
            return

        owner_type = self.selected_owner_type
        owner_display = self.owner_var.get()
        owner_id = self.owner_records.get(owner_display)

        if owner_id is None:
            messagebox.showwarning(
                "Record Required",
                "Please select a valid owner record.",
                parent=self,
            )
            return

        category = self.category_codes.get(
            self.category_var.get()
        )

        if category is None:
            messagebox.showwarning(
                "Category Required",
                "Please select a valid document category.",
                parent=self,
            )
            return

        title = self.title_var.get().strip()

        if not title:
            messagebox.showwarning(
                "Title Required",
                "Please enter a document title.",
                parent=self,
            )
            return

        description = self.description_text.get(
            "1.0",
            "end-1c",
        ).strip()

        try:
            upload_document(
                self.selected_file_path,
                owner_type,
                owner_id,
                category,
                title,
                description,
                actor_user_id=self.actor_user_id,
            )

        except (ValueError, PermissionError) as error:
            messagebox.showerror(
                "Upload Failed",
                str(error),
                parent=self,
            )
            return

        except Exception:
            messagebox.showerror(
                "Upload Failed",
                "The document could not be uploaded. "
                "Please check the file and try again.",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Upload Complete",
            "The document was uploaded successfully.",
            parent=self,
        )

        if self.on_uploaded is not None:
            self.on_uploaded()

        self.destroy()
