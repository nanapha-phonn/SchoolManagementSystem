import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import database.database as database_module

from config.settings import BACKUP_DIR, DOCUMENT_STORAGE_DIR
from services.permission_service import require_permission


BACKUP_FORMAT = "school-management-system-backup"
BACKUP_VERSION = 1

DATABASE_ARCHIVE_PATH = "database/school_management.db"
MANIFEST_ARCHIVE_PATH = "manifest.json"

MAX_MANIFEST_SIZE = 2 * 1024 * 1024
MAX_DATABASE_SIZE = 2 * 1024 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
MAX_TOTAL_SIZE = 5 * 1024 * 1024 * 1024
MAX_ENTRIES = 100_000

CHUNK_SIZE = 64 * 1024


# --------------------------------------------------
# VALIDATION HELPERS
# --------------------------------------------------

def _resolve_paths(db_path=None, document_storage_dir=None):
    database_path = Path(
        db_path if db_path is not None else database_module.DB_PATH
    ).expanduser()

    documents_path = Path(
        document_storage_dir
        if document_storage_dir is not None
        else DOCUMENT_STORAGE_DIR
    ).expanduser()

    return database_path, documents_path


def _safe_relative_path(value):
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
        or ":" in value
    ):
        raise ValueError("Backup contains an unsafe relative path.")

    path = PurePosixPath(value)
    parts = value.split("/")

    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise ValueError("Backup contains an unsafe relative path.")

    return parts


def _validate_hash(value):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Backup contains invalid SHA-256 metadata.")

    return value


def _validate_size(value, maximum, description):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise ValueError(f"Backup contains an invalid {description} size.")

    return value


def _sha256_file(path):
    digest = hashlib.sha256()
    total = 0

    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_SIZE)

            if not chunk:
                break

            total += len(chunk)
            digest.update(chunk)

    return total, digest.hexdigest()


# --------------------------------------------------
# DOCUMENT STORAGE ENUMERATION
# --------------------------------------------------

def _raise_walk_error(error):
    raise error


def _iter_document_files(document_root):
    root = Path(document_root)

    if not root.exists():
        return

    root_info = root.lstat()

    if (
        stat.S_ISLNK(root_info.st_mode)
        or not stat.S_ISDIR(root_info.st_mode)
    ):
        raise ValueError(
            "Document storage root must be a real directory."
        )

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=_raise_walk_error,
    ):
        current_path = Path(current)

        for name in directories:
            directory = current_path / name
            info = directory.lstat()

            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISDIR(info.st_mode)
            ):
                raise ValueError(
                    "Document storage contains an unsafe directory."
                )

        directories.sort()

        for name in sorted(filenames):
            file_path = current_path / name
            info = file_path.lstat()

            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISREG(info.st_mode)
            ):
                raise ValueError(
                    "Document storage contains a non-regular file."
                )

            yield file_path


# --------------------------------------------------
# DATABASE VALIDATION
# --------------------------------------------------

def _create_database_snapshot(source_path, destination_path):
    source_path = Path(source_path)

    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError(
            "The application database is not a regular file."
        )

    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(destination_path)

    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    if not Path(destination_path).is_file():
        raise RuntimeError("Could not create database snapshot.")


def _read_and_validate_database(database_path):
    connection = sqlite3.connect(
        Path(database_path).resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise ValueError(
                "Backup database failed SQLite integrity verification."
            )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise ValueError(
                "Backup database contains foreign-key violations."
            )

        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'documents'
            """
        ).fetchone()

        if table is None:
            raise ValueError(
                "Backup database does not contain the documents table."
            )

        rows = connection.execute(
            """
            SELECT storage_key, size_bytes, sha256
            FROM documents
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def _validate_database_document_entries(database_path, entries):
    rows = _read_and_validate_database(database_path)

    entries_by_path = {
        entry["path"]: entry
        for entry in entries
    }

    for row in rows:
        parts = _safe_relative_path(row["storage_key"])
        archive_path = "documents/" + "/".join(parts)

        entry = entries_by_path.get(archive_path)

        if entry is None:
            raise ValueError(
                "A registered document is missing from the backup."
            )

        if (
            entry["size_bytes"] != row["size_bytes"]
            or entry["sha256"] != row["sha256"]
        ):
            raise ValueError(
                "Document metadata does not match its backup file."
            )


def _validate_restored_document_files(database_path, document_root):
    rows = _read_and_validate_database(database_path)

    for row in rows:
        parts = _safe_relative_path(row["storage_key"])
        file_path = Path(document_root).joinpath(*parts)

        if file_path.is_symlink() or not file_path.is_file():
            raise ValueError(
                "A registered document is missing from the backup."
            )

        size, digest = _sha256_file(file_path)

        if size != row["size_bytes"] or digest != row["sha256"]:
            raise ValueError(
                "A restored document failed integrity verification."
            )


# --------------------------------------------------
# ARCHIVE FILE CREATION
# --------------------------------------------------

def _add_file_to_archive(archive, source_path, document_root):
    source_path = Path(source_path)
    document_root = Path(document_root)

    relative_path = source_path.relative_to(
        document_root
    ).as_posix()

    parts = _safe_relative_path(relative_path)
    archive_path = "documents/" + "/".join(parts)

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source_path, flags)

    digest = hashlib.sha256()
    total = 0

    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())

        if not stat.S_ISREG(before.st_mode):
            raise ValueError(
                "A document changed into a non-regular file."
            )

        info = zipfile.ZipInfo(archive_path)
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o600) << 16

        with archive.open(info, "w") as destination:
            while True:
                chunk = source.read(CHUNK_SIZE)

                if not chunk:
                    break

                total += len(chunk)
                digest.update(chunk)
                destination.write(chunk)

        after = os.fstat(source.fileno())

        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )

        if (
            before_identity != after_identity
            or total != before.st_size
        ):
            raise RuntimeError(
                "A document changed while the backup was being created."
            )

    return {
        "path": archive_path,
        "size_bytes": total,
        "sha256": digest.hexdigest(),
    }


# --------------------------------------------------
# CREATE BACKUP
# --------------------------------------------------

def create_backup(
    *,
    actor_user_id,
    backup_dir=None,
    db_path=None,
    document_storage_dir=None,
):
    """Create an administrator-only database and document backup."""

    require_permission(actor_user_id, "system.manage")

    database_path, documents_path = _resolve_paths(
        db_path,
        document_storage_dir,
    )

    destination_dir = Path(
        backup_dir if backup_dir is not None else BACKUP_DIR
    ).expanduser()

    if destination_dir.is_symlink():
        raise ValueError(
            "Backup directory must not be a symbolic link."
        )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    if not destination_dir.is_dir():
        raise ValueError("Backup destination must be a directory.")

    os.chmod(destination_dir, 0o700)

    with tempfile.TemporaryDirectory(
        prefix=".sms-backup-staging-",
        dir=destination_dir,
    ) as temporary_directory:
        staging = Path(temporary_directory)
        snapshot = staging / "school_management.db"
        temporary_archive = staging / "backup.zip"

        _create_database_snapshot(database_path, snapshot)

        database_size, database_hash = _sha256_file(snapshot)

        if database_size > MAX_DATABASE_SIZE:
            raise ValueError("Database is too large to back up.")

        entries = []
        total_size = database_size

        with zipfile.ZipFile(
            temporary_archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.write(
                snapshot,
                DATABASE_ARCHIVE_PATH,
            )

            for source_file in _iter_document_files(documents_path):
                entry = _add_file_to_archive(
                    archive,
                    source_file,
                    documents_path,
                )

                if entry["size_bytes"] > MAX_DOCUMENT_SIZE:
                    raise ValueError(
                        "A stored document exceeds the 10 MB limit."
                    )

                total_size += entry["size_bytes"]

                if total_size > MAX_TOTAL_SIZE:
                    raise ValueError(
                        "Total backup exceeds the configured size limit."
                    )

                entries.append(entry)

                if len(entries) > MAX_ENTRIES:
                    raise ValueError(
                        "Backup contains too many document files."
                    )

            _validate_database_document_entries(snapshot, entries)

            manifest = {
                "format": BACKUP_FORMAT,
                "version": BACKUP_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "database": {
                    "path": DATABASE_ARCHIVE_PATH,
                    "size_bytes": database_size,
                    "sha256": database_hash,
                },
                "documents": entries,
            }

            archive.writestr(
                MANIFEST_ARCHIVE_PATH,
                json.dumps(
                    manifest,
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
            )

        with temporary_archive.open("rb") as stream:
            os.fsync(stream.fileno())

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d_%H%M%S_%f"
        )
        random_suffix = uuid.uuid4().hex[:8]

        destination = destination_dir / (
            f"school_management_backup_{timestamp}_{random_suffix}.zip"
        )

        os.chmod(temporary_archive, 0o600)
        os.replace(temporary_archive, destination)

        return destination


# --------------------------------------------------
# BACKUP ARCHIVE VALIDATION
# --------------------------------------------------

def _validate_archive_member(info):
    name = info.filename

    if name.endswith("/"):
        raise ValueError(
            "Backup must not contain directory entries."
        )

    if "\\" in name or "\x00" in name:
        raise ValueError("Backup contains an unsafe archive path.")

    if name not in (
        MANIFEST_ARCHIVE_PATH,
        DATABASE_ARCHIVE_PATH,
    ):
        if not (
            name.startswith("documents/")
            or name == DATABASE_ARCHIVE_PATH
        ):
            raise ValueError(
                "Backup contains an unexpected archive entry."
            )

        parts = _safe_relative_path(name)

        if name.startswith("documents/") and len(parts) < 2:
            raise ValueError(
                "Backup contains an invalid document path."
            )

        if name.startswith("database/") and name != DATABASE_ARCHIVE_PATH:
            raise ValueError(
                "Backup contains an unexpected database entry."
            )

    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)

    if file_type not in (0, stat.S_IFREG):
        raise ValueError(
            "Backup contains a non-regular archive entry."
        )

    if info.flag_bits & 0x1:
        raise ValueError(
            "Encrypted backup entries are not supported."
        )


def _extract_verified_entry(archive, info, target, expected):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    total = 0

    with archive.open(info, "r") as source:
        with target.open("xb") as destination:
            while True:
                chunk = source.read(CHUNK_SIZE)

                if not chunk:
                    break

                total += len(chunk)

                if total > expected["size_bytes"]:
                    raise ValueError(
                        "Backup entry exceeds its declared size."
                    )

                digest.update(chunk)
                destination.write(chunk)

    if (
        total != expected["size_bytes"]
        or digest.hexdigest() != expected["sha256"]
    ):
        raise ValueError(
            "Backup entry failed size or SHA-256 verification."
        )

    os.chmod(target, 0o600)


def _extract_and_validate_backup(
    archive_path,
    staged_database,
    staged_documents,
):
    archive_path = Path(archive_path)

    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError(
            "Backup archive must be a regular file."
        )

    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()

            if not infos or len(infos) > MAX_ENTRIES + 2:
                raise ValueError(
                    "Backup contains an invalid number of entries."
                )

            names = [info.filename for info in infos]

            if len(names) != len(set(names)):
                raise ValueError(
                    "Backup contains duplicate archive entries."
                )

            for info in infos:
                _validate_archive_member(info)

            if MANIFEST_ARCHIVE_PATH not in names:
                raise ValueError("Backup manifest is missing.")

            if DATABASE_ARCHIVE_PATH not in names:
                raise ValueError("Backup database is missing.")

            manifest_info = archive.getinfo(MANIFEST_ARCHIVE_PATH)

            if manifest_info.file_size > MAX_MANIFEST_SIZE:
                raise ValueError("Backup manifest is too large.")

            manifest = json.loads(
                archive.read(manifest_info).decode("utf-8")
            )

            if (
                not isinstance(manifest, dict)
                or manifest.get("format") != BACKUP_FORMAT
                or manifest.get("version") != BACKUP_VERSION
            ):
                raise ValueError(
                    "Unsupported backup format or version."
                )

            database_metadata = manifest.get("database")

            if (
                not isinstance(database_metadata, dict)
                or database_metadata.get("path") != DATABASE_ARCHIVE_PATH
            ):
                raise ValueError(
                    "Backup database metadata is invalid."
                )

            database_size = _validate_size(
                database_metadata.get("size_bytes"),
                MAX_DATABASE_SIZE,
                "database",
            )
            database_hash = _validate_hash(
                database_metadata.get("sha256")
            )

            if archive.getinfo(
                DATABASE_ARCHIVE_PATH
            ).file_size != database_size:
                raise ValueError(
                    "Backup database size does not match its manifest."
                )

            documents = manifest.get("documents")

            if not isinstance(documents, list) or len(documents) > MAX_ENTRIES:
                raise ValueError(
                    "Backup document manifest is invalid."
                )

            expected_paths = {
                MANIFEST_ARCHIVE_PATH,
                DATABASE_ARCHIVE_PATH,
            }

            normalized_entries = []
            total_size = database_size

            for entry in documents:
                if not isinstance(entry, dict):
                    raise ValueError(
                        "Backup document metadata is invalid."
                    )

                path = entry.get("path")

                if (
                    not isinstance(path, str)
                    or not path.startswith("documents/")
                ):
                    raise ValueError(
                        "Backup document path is invalid."
                    )

                _safe_relative_path(path)

                if path in expected_paths:
                    raise ValueError(
                        "Backup contains duplicate document metadata."
                    )

                info = archive.getinfo(path)
                _validate_archive_member(info)

                parts = _safe_relative_path(path)
                storage_key = "/".join(parts[1:])
                _safe_relative_path(storage_key)

                size = _validate_size(
                    entry.get("size_bytes"),
                    MAX_DOCUMENT_SIZE,
                    "document",
                )
                digest = _validate_hash(entry.get("sha256"))

                if info.file_size != size:
                    raise ValueError(
                        "Document archive size does not match its manifest."
                    )

                expected_paths.add(path)
                total_size += size

                normalized_entries.append({
                    "path": path,
                    "storage_key": storage_key,
                    "size_bytes": size,
                    "sha256": digest,
                })

            if total_size > MAX_TOTAL_SIZE:
                raise ValueError(
                    "Backup exceeds the configured size limit."
                )

            if set(names) != expected_paths:
                raise ValueError(
                    "Backup contains missing or unexpected entries."
                )

            _extract_verified_entry(
                archive,
                archive.getinfo(DATABASE_ARCHIVE_PATH),
                staged_database,
                {
                    "size_bytes": database_size,
                    "sha256": database_hash,
                },
            )

            for entry in normalized_entries:
                target = Path(staged_documents).joinpath(
                    *_safe_relative_path(entry["storage_key"])
                )

                _extract_verified_entry(
                    archive,
                    archive.getinfo(entry["path"]),
                    target,
                    entry,
                )

    except (
        zipfile.BadZipFile,
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
    ) as error:
        raise ValueError(
            "Backup archive is invalid or corrupted."
        ) from error

    _validate_restored_document_files(
        staged_database,
        staged_documents,
    )


# --------------------------------------------------
# RESTORE BACKUP
# --------------------------------------------------

def restore_backup(
    archive_path,
    *,
    actor_user_id,
    db_path=None,
    document_storage_dir=None,
):
    """
    Restore database and documents after complete staging and validation.

    Existing paths are moved aside before replacement and restored if
    either replacement fails.
    """

    require_permission(actor_user_id, "system.manage")

    database_path, documents_path = _resolve_paths(
        db_path,
        document_storage_dir,
    )

    archive_path = Path(archive_path).expanduser()

    database_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.parent.mkdir(parents=True, exist_ok=True)

    if database_path.is_symlink() or documents_path.is_symlink():
        raise ValueError(
            "Restore targets must not be symbolic links."
        )

    if database_path.exists() and not database_path.is_file():
        raise ValueError(
            "Database restore target is not a regular file."
        )

    if documents_path.exists() and not documents_path.is_dir():
        raise ValueError(
            "Document restore target is not a directory."
        )

    archive_resolved = archive_path.resolve()
    database_resolved = database_path.resolve()
    documents_resolved = documents_path.resolve()

    if archive_resolved in (database_resolved, documents_resolved):
        raise ValueError(
            "Backup archive cannot be a restore target."
        )

    if documents_path.exists():
        try:
            archive_resolved.relative_to(documents_resolved)
        except ValueError:
            pass
        else:
            raise ValueError(
                "Backup archive must not be inside document storage."
            )

    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(database_path) + suffix)

        if sidecar.exists():
            raise RuntimeError(
                "Database sidecar files exist. Close database activity "
                "and retry the restore."
            )

    descriptor, database_stage_name = tempfile.mkstemp(
        prefix=f".{database_path.name}.restore-",
        dir=database_path.parent,
    )
    os.close(descriptor)

    database_stage = Path(database_stage_name)

    # mkstemp creates the file, but verified extraction uses exclusive
    # creation ("xb"). Remove the empty placeholder before extraction.
    database_stage.unlink()

    documents_stage = Path(
        tempfile.mkdtemp(
            prefix=f".{documents_path.name}.restore-",
            dir=documents_path.parent,
        )
    )

    token = uuid.uuid4().hex

    old_database = database_path.with_name(
        f".{database_path.name}.pre-restore-{token}"
    )
    old_documents = documents_path.with_name(
        f".{documents_path.name}.pre-restore-{token}"
    )

    old_database_moved = False
    old_documents_moved = False
    new_database_installed = False
    new_documents_installed = False

    try:
        _extract_and_validate_backup(
            archive_path,
            database_stage,
            documents_stage,
        )

        if database_path.exists():
            os.replace(database_path, old_database)
            old_database_moved = True

        if documents_path.exists():
            os.replace(documents_path, old_documents)
            old_documents_moved = True

        os.replace(documents_stage, documents_path)
        new_documents_installed = True

        os.replace(database_stage, database_path)
        new_database_installed = True

    except Exception:
        rollback_errors = []

        try:
            if new_database_installed and database_path.exists():
                database_path.unlink()

            if old_database_moved and old_database.exists():
                os.replace(old_database, database_path)

        except OSError as error:
            rollback_errors.append(error)

        try:
            if new_documents_installed and documents_path.exists():
                shutil.rmtree(documents_path)

            if old_documents_moved and old_documents.exists():
                os.replace(old_documents, documents_path)

        except OSError as error:
            rollback_errors.append(error)

        if rollback_errors:
            raise RuntimeError(
                "Restore failed and rollback was incomplete. "
                "Review the database and document directories immediately."
            ) from rollback_errors[0]

        raise

    else:
        if old_database.exists():
            old_database.unlink()

        if old_documents.exists():
            shutil.rmtree(old_documents)

        return {
            "database_path": database_path,
            "document_storage_dir": documents_path,
        }

    finally:
        if database_stage.exists():
            database_stage.unlink()

        if documents_stage.exists():
            shutil.rmtree(documents_stage)
