import hashlib
import os
import re
import stat
import tempfile
import uuid

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from config.settings import DOCUMENT_STORAGE_DIR
from models.document import (
    ALLOWED_MIME_TYPES,
    MAX_DOCUMENT_SIZE_BYTES,
)


CHUNK_SIZE = 64 * 1024

VALID_OWNER_TYPES = {
    "student",
    "teacher",
    "transport_staff",
}

STORAGE_FILENAME_PATTERN = re.compile(
    r"^[0-9a-f]{32}\.(pdf|jpg|jpeg|png)$"
)

MIME_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_filename: str
    mime_type: str
    file_extension: str
    size_bytes: int
    sha256: str


class DocumentStorage:
    """Secure filesystem storage for uploaded school documents."""

    def __init__(self, storage_root=None):
        self.storage_root = Path(
            storage_root
            if storage_root is not None
            else DOCUMENT_STORAGE_DIR
        ).expanduser()

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def store_file(self, source_path, owner_type, owner_id):
        """
        Validate and store a document.

        Returns StoredFile metadata. The original filename is never
        used as the physical storage filename.
        """

        owner_type, owner_id = self._validate_owner(
            owner_type,
            owner_id,
        )

        source_path = Path(source_path)
        original_filename = source_path.name

        self._validate_original_filename(original_filename)

        # Reject source symlinks before opening.
        try:
            source_info = source_path.lstat()
        except OSError as error:
            raise ValueError(
                "The selected document cannot be accessed."
            ) from error

        if stat.S_ISLNK(source_info.st_mode):
            raise ValueError(
                "Symbolic links cannot be uploaded."
            )

        source_flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
        )

        try:
            source_fd = os.open(source_path, source_flags)
        except OSError as error:
            raise ValueError(
                "The selected document could not be opened safely."
            ) from error

        # Verify the opened descriptor before fdopen().
        # Opening a directory can succeed on Linux, but fdopen()
        # would otherwise raise an unexpected IsADirectoryError.
        try:
            opened_info = os.fstat(source_fd)

            if not stat.S_ISREG(opened_info.st_mode):
                raise ValueError(
                    "Only regular files can be uploaded."
                )
        except Exception:
            os.close(source_fd)
            raise

        temporary_path = None
        final_path = None
        published = False

        try:
            with os.fdopen(source_fd, "rb") as source:
                initial_info = os.fstat(source.fileno())

                if not stat.S_ISREG(initial_info.st_mode):
                    raise ValueError(
                        "Only regular files can be uploaded."
                    )

                if initial_info.st_size <= 0:
                    raise ValueError(
                        "Empty documents cannot be uploaded."
                    )

                if initial_info.st_size > MAX_DOCUMENT_SIZE_BYTES:
                    raise ValueError(
                        "Document exceeds the maximum size of 10 MB."
                    )

                prefix = source.read(8)
                mime_type = self._detect_mime_type(prefix)

                if mime_type is None:
                    raise ValueError(
                        "File content is not a supported PDF, JPEG, or PNG."
                    )

                file_extension = Path(
                    original_filename
                ).suffix.lower()

                allowed_extensions = ALLOWED_MIME_TYPES[mime_type]

                if file_extension not in allowed_extensions:
                    raise ValueError(
                        "File extension does not match its actual content."
                    )

                owner_directory = self._prepare_owner_directory(
                    owner_type,
                    owner_id,
                )

                temporary_fd, temporary_name = tempfile.mkstemp(
                    prefix=".upload-",
                    suffix=".tmp",
                    dir=owner_directory,
                )

                temporary_path = Path(temporary_name)

                digest = hashlib.sha256()
                total_size = 0

                with os.fdopen(temporary_fd, "wb") as destination:

                    # Write the signature bytes already read.
                    if prefix:
                        destination.write(prefix)
                        digest.update(prefix)
                        total_size += len(prefix)

                    # Stream the remaining source in bounded chunks.
                    while True:
                        chunk = source.read(CHUNK_SIZE)

                        if not chunk:
                            break

                        total_size += len(chunk)

                        if total_size > MAX_DOCUMENT_SIZE_BYTES:
                            raise ValueError(
                                "Document exceeds the maximum size of 10 MB."
                            )

                        destination.write(chunk)
                        digest.update(chunk)

                    if total_size <= 0:
                        raise ValueError(
                            "Empty documents cannot be uploaded."
                        )

                    final_source_info = os.fstat(source.fileno())

                    # Detect modifications while the file was copied.
                    if (
                        final_source_info.st_size != initial_info.st_size
                        or total_size != initial_info.st_size
                        or final_source_info.st_mtime_ns
                        != initial_info.st_mtime_ns
                        or final_source_info.st_ctime_ns
                        != initial_info.st_ctime_ns
                    ):
                        raise ValueError(
                            "The source document changed during upload."
                        )

                    destination.flush()
                    os.fsync(destination.fileno())

                file_hash = digest.hexdigest()

            # Publish without overwriting an existing generated filename.
            for _ in range(5):
                generated_name = (
                    f"{uuid.uuid4().hex}{file_extension}"
                )

                candidate = owner_directory / generated_name

                try:
                    os.link(temporary_path, candidate)
                except FileExistsError:
                    continue

                final_path = candidate
                published = True
                break

            if not published:
                raise OSError(
                    "Could not allocate a unique document storage filename."
                )

            # The published file and temporary file are hard links to
            # the same completed content. Remove the temporary name.
            temporary_path.unlink()
            temporary_path = None

            self._fsync_directory(owner_directory)

            storage_key = (
                f"{owner_type}/{owner_id}/{final_path.name}"
            )

            return StoredFile(
                storage_key=storage_key,
                original_filename=original_filename,
                mime_type=mime_type,
                file_extension=file_extension,
                size_bytes=total_size,
                sha256=file_hash,
            )

        except Exception:
            # If publication succeeded but a later step failed,
            # remove the published file to avoid an orphan.
            if published and final_path is not None:
                try:
                    final_path.unlink(missing_ok=True)
                except OSError:
                    pass

            raise

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def discard_unregistered_file(self, stored_file):
        """
        Remove an uploaded file when its database registration fails.

        This is an internal compensation operation, not a document
        deletion feature. Only an unchanged StoredFile can be removed.
        """

        if not isinstance(stored_file, StoredFile):
            raise ValueError(
                "A valid StoredFile result is required."
            )

        file_path = self._resolve_existing_file(
            stored_file.storage_key
        )

        if not self.verify_file(
            stored_file.storage_key,
            stored_file.sha256,
            stored_file.size_bytes,
        ):
            raise ValueError(
                "Cannot discard a file that no longer matches "
                "its original integrity metadata."
            )

        file_path.unlink()
        self._fsync_directory(file_path.parent)

        return True

    def open_file(self, storage_key) -> BinaryIO:
        """
        Open a stored document for reading.

        Only application-generated storage keys are accepted.
        Symlinks, traversal paths, and non-regular files are rejected.
        """

        file_path = self._resolve_existing_file(storage_key)

        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
        )

        file_fd = os.open(file_path, flags)

        try:
            file_info = os.fstat(file_fd)

            if not stat.S_ISREG(file_info.st_mode):
                raise ValueError(
                    "Stored document is not a regular file."
                )

            return os.fdopen(file_fd, "rb")

        except Exception:
            os.close(file_fd)
            raise

    def verify_file(self, storage_key, expected_sha256, expected_size):
        """
        Verify the stored file against its database metadata.

        Returns False when the content or size does not match.
        Raises an exception when the file cannot be safely accessed.
        """

        if not isinstance(expected_sha256, str):
            raise ValueError("Expected SHA-256 hash must be text.")

        expected_sha256 = expected_sha256.strip().lower()

        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("Invalid expected SHA-256 hash.")

        if (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or not 0 < expected_size <= MAX_DOCUMENT_SIZE_BYTES
        ):
            raise ValueError("Invalid expected document size.")

        digest = hashlib.sha256()
        total_size = 0

        with self.open_file(storage_key) as source:
            while True:
                chunk = source.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_DOCUMENT_SIZE_BYTES:
                    return False

                digest.update(chunk)

        return (
            total_size == expected_size
            and digest.hexdigest() == expected_sha256
        )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    @staticmethod
    def _validate_owner(owner_type, owner_id):
        if (
            not isinstance(owner_type, str)
            or owner_type not in VALID_OWNER_TYPES
        ):
            raise ValueError("Invalid document owner type.")

        if isinstance(owner_id, bool) or not isinstance(
            owner_id, int
        ):
            raise ValueError(
                "Document owner ID must be a positive integer."
            )

        if owner_id <= 0:
            raise ValueError(
                "Document owner ID must be a positive integer."
            )

        return owner_type, owner_id

    @staticmethod
    def _validate_original_filename(filename):
        if not isinstance(filename, str) or not filename:
            raise ValueError("Original filename is required.")

        if len(filename) > 255:
            raise ValueError(
                "Original filename cannot exceed 255 characters."
            )

        if (
            "/" in filename
            or "\\" in filename
            or any(ord(character) < 32 or ord(character) == 127
                   for character in filename)
        ):
            raise ValueError("Invalid original filename.")

    @staticmethod
    def _detect_mime_type(prefix):
        for signature, mime_type in MIME_SIGNATURES:
            if prefix.startswith(signature):
                return mime_type

        return None

    # --------------------------------------------------
    # DIRECTORY MANAGEMENT
    # --------------------------------------------------

    @staticmethod
    def _ensure_private_directory(path):
        path = Path(path)

        path.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        info = path.lstat()

        if stat.S_ISLNK(info.st_mode):
            raise ValueError(
                "Storage directories cannot be symbolic links."
            )

        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(
                "Storage path is not a directory."
            )

        # Uploaded documents are private application data.
        os.chmod(path, 0o700)

        return path.resolve(strict=True)

    def _prepare_owner_directory(self, owner_type, owner_id):
        root = self._ensure_private_directory(
            self.storage_root
        )

        owner_directory = self._ensure_private_directory(
            root / owner_type
        )

        return self._ensure_private_directory(
            owner_directory / str(owner_id)
        )

    @staticmethod
    def _fsync_directory(directory):
        try:
            flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
            )

            directory_fd = os.open(directory, flags)

            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except OSError:
            # Some filesystems do not support directory fsync.
            pass

    # --------------------------------------------------
    # SAFE STORAGE-KEY RESOLUTION
    # --------------------------------------------------

    @staticmethod
    def _parse_storage_key(storage_key):
        if not isinstance(storage_key, str):
            raise ValueError("Storage key must be text.")

        if not storage_key or len(storage_key) > 255:
            raise ValueError("Invalid storage key.")

        if any(
            character in storage_key
            for character in (chr(0), chr(92), ":")
        ):
            raise ValueError("Invalid storage key.")

        parts = storage_key.split("/")

        if len(parts) != 3:
            raise ValueError("Invalid storage key structure.")

        owner_type, owner_id_text, filename = parts

        if owner_type not in VALID_OWNER_TYPES:
            raise ValueError("Invalid storage owner directory.")

        if (
            not owner_id_text.isdigit()
            or owner_id_text.startswith("0")
            or int(owner_id_text) <= 0
        ):
            raise ValueError("Invalid storage owner ID.")

        if not STORAGE_FILENAME_PATTERN.fullmatch(filename):
            raise ValueError("Invalid generated storage filename.")

        return owner_type, owner_id_text, filename

    def _resolve_existing_file(self, storage_key):
        parts = self._parse_storage_key(storage_key)

        root = Path(self.storage_root)

        root_info = root.lstat()

        if stat.S_ISLNK(root_info.st_mode):
            raise ValueError(
                "Storage root cannot be a symbolic link."
            )

        if not stat.S_ISDIR(root_info.st_mode):
            raise ValueError("Storage root is not a directory.")

        root = root.resolve(strict=True)
        current = root

        # Check every path component to reject symlink traversal.
        for index, part in enumerate(parts):
            current = current / part
            info = current.lstat()

            if stat.S_ISLNK(info.st_mode):
                raise ValueError(
                    "Symbolic links are not allowed in document storage."
                )

            is_last = index == len(parts) - 1

            if is_last:
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError(
                        "Stored document is not a regular file."
                    )
            elif not stat.S_ISDIR(info.st_mode):
                raise ValueError(
                    "Invalid document storage directory."
                )

        resolved = current.resolve(strict=True)

        if not resolved.is_relative_to(root):
            raise ValueError(
                "Document path escapes the storage directory."
            )

        return resolved
