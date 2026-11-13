import tkinter as tk

from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from services.backup_service import (
    create_backup as create_backup_service,
    restore_backup as restore_backup_service,
)
from ui.settings.school_profile_section import SchoolProfileSection


class SettingsFrame(ttk.Frame):
    """Administrator settings and data-protection controls."""

    def __init__(self, master, user, on_restored=None):
        super().__init__(master, padding=22)

        self.user = user
        self.actor_user_id = user["id"]
        self.on_restored = on_restored

        self.is_admin = user.get("role") == "admin"

        self.create_widgets()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def create_widgets(self):
        ttk.Label(
            self,
            text="Settings",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Application administration and data protection.",
            foreground="#64748B",
        ).pack(anchor="w", pady=(4, 20))

        school_profile_section = SchoolProfileSection(
            self,
            user=self.user,
        )
        school_profile_section.pack(
            fill="x",
            pady=(0, 16),
        )

        backup_section = ttk.LabelFrame(
            self,
            text="Database and Document Backup",
            padding=18,
        )
        backup_section.pack(fill="x", pady=(0, 16))

        ttk.Label(
            backup_section,
            text="Create Backup",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            backup_section,
            text=(
                "Create a portable backup containing the SQLite database "
                "and all uploaded documents. The backup is stored in the "
                "application's backups directory."
            ),
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))

        self.backup_button = ttk.Button(
            backup_section,
            text="Create Backup",
            command=self.create_backup,
            state="normal" if self.is_admin else "disabled",
        )
        self.backup_button.pack(anchor="w")

        restore_section = ttk.LabelFrame(
            self,
            text="Restore Data",
            padding=18,
        )
        restore_section.pack(fill="x", pady=(0, 16))

        ttk.Label(
            restore_section,
            text="Restore from Backup",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            restore_section,
            text=(
                "Restore the database and uploaded documents from a "
                "previously created backup archive."
            ),
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))

        self.restore_button = ttk.Button(
            restore_section,
            text="Select Backup to Restore...",
            command=self.restore_backup,
            state="normal" if self.is_admin else "disabled",
        )
        self.restore_button.pack(anchor="w")

        warning_text = (
            "Important: Restoring a backup replaces the current database "
            "and document storage. The current data will be replaced by "
            "the contents of the selected archive. The application will "
            "return to the login screen after a successful restore."
        )

        ttk.Label(
            self,
            text=warning_text,
            foreground="#A16207",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        if not self.is_admin:
            ttk.Label(
                self,
                text="Administrator permission is required for these operations.",
                foreground="#B91C1C",
            ).pack(anchor="w", pady=(12, 0))

    # --------------------------------------------------
    # AUTHORIZATION
    # --------------------------------------------------

    def require_admin(self):
        if not self.is_admin:
            messagebox.showerror(
                "Permission Denied",
                "Only administrators can manage application backups.",
                parent=self.winfo_toplevel(),
            )
            return False

        return True

    # --------------------------------------------------
    # CREATE BACKUP
    # --------------------------------------------------

    def create_backup(self):
        if not self.require_admin():
            return

        try:
            backup_path = create_backup_service(
                actor_user_id=self.actor_user_id,
            )

        except Exception:
            messagebox.showerror(
                "Backup Failed",
                "The backup could not be created. "
                "Check the application data and backup directory.",
                parent=self.winfo_toplevel(),
            )
            return

        filename = Path(backup_path).name

        messagebox.showinfo(
            "Backup Complete",
            f"The backup was created successfully:\n\n{filename}",
            parent=self.winfo_toplevel(),
        )

    # --------------------------------------------------
    # RESTORE BACKUP
    # --------------------------------------------------

    def restore_backup(self):
        if not self.require_admin():
            return

        archive_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select Backup Archive",
            filetypes=(
                ("School Management System backups", "*.zip"),
                ("ZIP archives", "*.zip"),
                ("All files", "*.*"),
            ),
        )

        if not archive_path:
            return

        filename = Path(archive_path).name

        confirmed = messagebox.askyesno(
            "Confirm Data Restore",
            (
                f"Restore from '{filename}'?\n\n"
                "WARNING: This operation replaces the current database "
                "and document storage with the selected backup.\n\n"
                "The existing data will be replaced. The operation cannot "
                "be undone from this screen.\n\n"
                "Continue with the restore?"
            ),
            parent=self.winfo_toplevel(),
        )

        if not confirmed:
            return

        try:
            restore_backup_service(
                archive_path,
                actor_user_id=self.actor_user_id,
            )

        except Exception:
            messagebox.showerror(
                "Restore Failed",
                (
                    "The backup could not be restored. The archive may be "
                    "invalid, corrupted, or incompatible with this version."
                ),
                parent=self.winfo_toplevel(),
            )
            return

        messagebox.showinfo(
            "Restore Complete",
            (
                "The database and document storage were restored "
                "successfully.\n\n"
                "You will now return to the login screen."
            ),
            parent=self.winfo_toplevel(),
        )

        if self.on_restored is not None:
            self.on_restored()
