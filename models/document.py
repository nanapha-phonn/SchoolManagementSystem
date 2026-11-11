from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
import re


MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024

VALID_DOCUMENT_STATUSES = {
    "active",
    "archived",
}

ALLOWED_MIME_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}

VALID_CATEGORIES_BY_OWNER = {
    "student": {
        "birth_certificate",
        "identity_document",
        "enrollment_form",
        "previous_school_record",
        "transfer_certificate",
        "academic_record",
        "photograph",
        "other",
    },
    "teacher": {
        "identity_document",
        "cv_resume",
        "qualification_certificate",
        "employment_contract",
        "teaching_certificate",
        "professional_license",
        "photograph",
        "other",
    },
    "transport_staff": {
        "identity_document",
        "cv_resume",
        "employment_contract",
        "drivers_license",
        "safety_training_certificate",
        "other",
    },
}

VALID_DOCUMENT_CATEGORIES = set().union(
    *VALID_CATEGORIES_BY_OWNER.values()
)


@dataclass
class Document:
    title: str
    category: str
    original_filename: str
    storage_key: str
    mime_type: str
    file_extension: str
    size_bytes: int
    sha256: str
    uploaded_by: int

    student_id: int = None
    teacher_id: int = None
    transport_staff_id: int = None

    description: str = ""
    status: str = "active"
    archived_by: int = None
    archived_at: str = None

    def validate(self):
        self._validate_owner()
        self._validate_title()
        self._validate_category()
        self._validate_filename()
        self._validate_storage_key()
        self._validate_file_type()
        self._validate_file_size()
        self._validate_hash()
        self._validate_uploader()
        self._validate_description()
        self._validate_status()

        return self

    def _validate_owner(self):
        owner_fields = (
            "student_id",
            "teacher_id",
            "transport_staff_id",
        )

        selected_owners = []

        for field_name in owner_fields:
            value = getattr(self, field_name)

            if value is not None:
                validated_id = self._validate_id(
                    value,
                    field_name.replace("_id", "").replace("_", " ").title()
                    + " ID",
                )

                setattr(self, field_name, validated_id)
                selected_owners.append(field_name)

        if len(selected_owners) != 1:
            raise ValueError(
                "A document must belong to exactly one student, "
                "teacher, or transport staff member."
            )

        self.owner_type = selected_owners[0].replace("_id", "")

    def _validate_title(self):
        if not isinstance(self.title, str):
            raise ValueError("Document title must be text.")

        self.title = self.title.strip()

        if not self.title:
            raise ValueError("Document title is required.")

        if len(self.title) > 150:
            raise ValueError(
                "Document title cannot exceed 150 characters."
            )

        self._reject_control_characters(
            self.title,
            "Document title",
        )

    def _validate_category(self):
        if not isinstance(self.category, str):
            raise ValueError("Document category must be text.")

        self.category = self.category.strip().lower()

        allowed_categories = VALID_CATEGORIES_BY_OWNER[
            self.owner_type
        ]

        if self.category not in allowed_categories:
            raise ValueError(
                f"Invalid document category for {self.owner_type.replace('_', ' ')}."
            )

    def _validate_filename(self):
        if not isinstance(self.original_filename, str):
            raise ValueError("Original filename must be text.")

        self.original_filename = self.original_filename.strip()

        if not self.original_filename:
            raise ValueError("Original filename is required.")

        if len(self.original_filename) > 255:
            raise ValueError(
                "Original filename cannot exceed 255 characters."
            )

        if (
            "/" in self.original_filename
            or "\\" in self.original_filename
            or "\x00" in self.original_filename
        ):
            raise ValueError(
                "Original filename must not contain directory paths."
            )

        self._reject_control_characters(
            self.original_filename,
            "Original filename",
        )

    def _validate_storage_key(self):
        if not isinstance(self.storage_key, str):
            raise ValueError("Storage key must be text.")

        self.storage_key = self.storage_key.strip()

        if not self.storage_key:
            raise ValueError("Storage key is required.")

        if len(self.storage_key) > 255:
            raise ValueError(
                "Storage key cannot exceed 255 characters."
            )

        unsafe_characters = (chr(0), chr(92), ":")

        if any(character in self.storage_key for character in unsafe_characters):
            raise ValueError("Invalid storage key.")

        path = PurePosixPath(self.storage_key)
        parts = self.storage_key.split("/")

        if (
            path.is_absolute()
            or self.storage_key == "."
            or ".." in self.storage_key
            or "./" in self.storage_key
            or any(part in ("", ".", "..") for part in parts)
            or path.as_posix() != self.storage_key
        ):
            raise ValueError(
                "Storage key must be a safe relative path."
            )

    def _validate_file_type(self):
        if not isinstance(self.mime_type, str):
            raise ValueError("MIME type must be text.")

        if not isinstance(self.file_extension, str):
            raise ValueError("File extension must be text.")

        self.mime_type = self.mime_type.strip().lower()
        self.file_extension = self.file_extension.strip().lower()

        allowed_extensions = ALLOWED_MIME_TYPES.get(self.mime_type)

        if allowed_extensions is None:
            raise ValueError("Unsupported document file type.")

        if self.file_extension not in allowed_extensions:
            raise ValueError(
                "File extension does not match the document MIME type."
            )

    def _validate_file_size(self):
        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
        ):
            raise ValueError("File size must be an integer.")

        if not 0 < self.size_bytes <= MAX_DOCUMENT_SIZE_BYTES:
            raise ValueError(
                "Document size must be greater than zero "
                "and cannot exceed 10 MB."
            )

    def _validate_hash(self):
        if not isinstance(self.sha256, str):
            raise ValueError("SHA-256 hash must be text.")

        self.sha256 = self.sha256.strip().lower()

        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("Invalid SHA-256 hash.")

    def _validate_uploader(self):
        self.uploaded_by = self._validate_id(
            self.uploaded_by,
            "Uploader user ID",
        )

    def _validate_description(self):
        if not isinstance(self.description, str):
            raise ValueError("Document description must be text.")

        self.description = self.description.strip()

        if len(self.description) > 1000:
            raise ValueError(
                "Document description cannot exceed 1000 characters."
            )

    def _validate_status(self):
        if not isinstance(self.status, str):
            raise ValueError("Document status must be text.")

        self.status = self.status.strip().lower()

        if self.status not in VALID_DOCUMENT_STATUSES:
            raise ValueError("Invalid document status.")

        if self.status == "active":
            if self.archived_by is not None or self.archived_at is not None:
                raise ValueError(
                    "Active documents cannot contain archive information."
                )

        else:
            if self.archived_by is None or self.archived_at is None:
                raise ValueError(
                    "Archived documents require archive information."
                )

            self.archived_by = self._validate_id(
                self.archived_by,
                "Archiving user ID",
            )

            if not isinstance(self.archived_at, str):
                raise ValueError("Archive timestamp must be text.")

            try:
                datetime.fromisoformat(self.archived_at)
            except ValueError:
                raise ValueError(
                    "Archive timestamp must be a valid ISO date or datetime."
                )

    @staticmethod
    def _validate_id(value, field_name):
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be a positive integer."
            )

        return value

    @staticmethod
    def _reject_control_characters(value, field_name):
        if any(ord(character) < 32 or ord(character) == 127
               for character in value):
            raise ValueError(
                f"{field_name} contains invalid control characters."
            )
