import hashlib
from contextlib import closing
from dataclasses import asdict

from database.database import get_connection
from models.document import (
    Document,
    VALID_CATEGORIES_BY_OWNER,
    VALID_DOCUMENT_CATEGORIES,
    MAX_DOCUMENT_SIZE_BYTES,
)
from services.permission_service import require_permission
from storage.document_storage import DocumentStorage


OWNER_TABLES = {
    "student": "students",
    "teacher": "teachers",
    "transport_staff": "transport_staff",
}

OWNER_ID_COLUMNS = {
    "student": "student_id",
    "teacher": "teacher_id",
    "transport_staff": "transport_staff_id",
}


# --------------------------------------------------
# SHARED VALIDATION
# --------------------------------------------------

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


def _validate_owner(owner_type, owner_id):
    if not isinstance(owner_type, str):
        raise ValueError("Document owner type must be text.")

    owner_type = owner_type.strip().lower()

    if owner_type not in OWNER_TABLES:
        raise ValueError("Unsupported document owner type.")

    owner_id = _validate_id(owner_id, "Document owner ID")

    return owner_type, owner_id


def _get_document_storage(storage=None):
    return storage if storage is not None else DocumentStorage()


def _get_document_row(connection, document_id):
    return connection.execute(
        """
        SELECT *
        FROM documents
        WHERE id = ?
        """,
        (document_id,),
    ).fetchone()


# --------------------------------------------------
# DOCUMENT UPLOAD AND REGISTRATION
# --------------------------------------------------

def upload_document(
    source_path,
    owner_type,
    owner_id,
    category,
    title,
    description="",
    *,
    actor_user_id,
    storage=None,
):
    """
    Upload a file and register its metadata.

    If model validation or database registration fails after the file
    has been stored, the storage engine attempts safe compensation.
    """

    require_permission(actor_user_id, "documents.manage")

    actor_user_id = _validate_id(
        actor_user_id,
        "Actor user ID",
    )

    owner_type, owner_id = _validate_owner(
        owner_type,
        owner_id,
    )

    if not isinstance(category, str):
        raise ValueError("Document category must be text.")

    category = category.strip().lower()

    if category not in VALID_CATEGORIES_BY_OWNER[owner_type]:
        raise ValueError(
            "Invalid document category for this owner type."
        )

    # Confirm the owner exists before performing filesystem work.
    owner_table = OWNER_TABLES[owner_type]

    with closing(get_connection()) as connection:
        owner = connection.execute(
            f"SELECT id FROM {owner_table} WHERE id = ?",
            (owner_id,),
        ).fetchone()

    if owner is None:
        raise ValueError(
            f"The selected {owner_type.replace('_', ' ')} record was not found."
        )

    storage = _get_document_storage(storage)

    stored_file = storage.store_file(
        source_path,
        owner_type,
        owner_id,
    )

    try:
        owner_data = {
            "student_id": None,
            "teacher_id": None,
            "transport_staff_id": None,
        }

        owner_data[OWNER_ID_COLUMNS[owner_type]] = owner_id

        document = Document(
            title=title,
            category=category,
            original_filename=stored_file.original_filename,
            storage_key=stored_file.storage_key,
            mime_type=stored_file.mime_type,
            file_extension=stored_file.file_extension,
            size_bytes=stored_file.size_bytes,
            sha256=stored_file.sha256,
            uploaded_by=actor_user_id,
            description=description,
            **owner_data,
        ).validate()

        data = asdict(document)

        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO documents (
                        student_id,
                        teacher_id,
                        transport_staff_id,
                        category,
                        title,
                        description,
                        original_filename,
                        storage_key,
                        mime_type,
                        file_extension,
                        size_bytes,
                        sha256,
                        uploaded_by,
                        status
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active'
                    )
                    """,
                    (
                        data["student_id"],
                        data["teacher_id"],
                        data["transport_staff_id"],
                        data["category"],
                        data["title"],
                        data["description"],
                        data["original_filename"],
                        data["storage_key"],
                        data["mime_type"],
                        data["file_extension"],
                        data["size_bytes"],
                        data["sha256"],
                        data["uploaded_by"],
                    ),
                )

                document_id = cursor.lastrowid

                row = _get_document_row(
                    connection,
                    document_id,
                )

                result = dict(row)

        return result

    except Exception as registration_error:
        try:
            storage.discard_unregistered_file(stored_file)
        except Exception as cleanup_error:
            raise RuntimeError(
                "Document registration failed and the uploaded file "
                "could not be safely removed. Manual storage-integrity "
                f"review is required for: {stored_file.storage_key}"
            ) from cleanup_error

        raise registration_error


# --------------------------------------------------
# DOCUMENT RETRIEVAL
# --------------------------------------------------

def get_document(document_id, *, actor_user_id):
    require_permission(actor_user_id, "documents.view")

    document_id = _validate_id(
        document_id,
        "Document ID",
    )

    with closing(get_connection()) as connection:
        row = _get_document_row(connection, document_id)

        return dict(row) if row else None


def get_documents(
    search="",
    *,
    owner_type=None,
    owner_id=None,
    category=None,
    status="active",
    actor_user_id,
):
    """
    List and filter documents.

    By default, only active documents are returned.
    Use status=None to include active and archived documents.
    """

    require_permission(actor_user_id, "documents.view")

    if not isinstance(search, str):
        raise ValueError("Document search term must be text.")

    search = search.strip()

    if len(search) > 200:
        raise ValueError("Search term cannot exceed 200 characters.")

    conditions = []
    parameters = []

    if owner_type is not None:
        if not isinstance(owner_type, str):
            raise ValueError("Document owner type must be text.")

        owner_type = owner_type.strip().lower()

        if owner_type not in OWNER_ID_COLUMNS:
            raise ValueError("Unsupported document owner type.")

        owner_column = OWNER_ID_COLUMNS[owner_type]

        if owner_id is not None:
            owner_id = _validate_id(
                owner_id,
                "Document owner ID",
            )

            conditions.append(f"{owner_column} = ?")
            parameters.append(owner_id)
        else:
            conditions.append(f"{owner_column} IS NOT NULL")

    elif owner_id is not None:
        raise ValueError(
            "Owner type is required when filtering by owner ID."
        )

    if category is not None:
        if not isinstance(category, str):
            raise ValueError("Document category must be text.")

        category = category.strip().lower()

        if category not in VALID_DOCUMENT_CATEGORIES:
            raise ValueError("Invalid document category.")

        if owner_type is not None:
            if category not in VALID_CATEGORIES_BY_OWNER[owner_type]:
                raise ValueError(
                    "Document category does not match the owner type."
                )

        conditions.append("category = ?")
        parameters.append(category)

    if status is not None:
        if status not in ("active", "archived"):
            raise ValueError("Invalid document status filter.")

        conditions.append("status = ?")
        parameters.append(status)

    if search:
        conditions.append(
            """
            (
                title LIKE ?
                OR original_filename LIKE ?
                OR description LIKE ?
            )
            """
        )

        pattern = f"%{search}%"
        parameters.extend((pattern, pattern, pattern))

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    query = f"""
        SELECT *
        FROM documents
        {where_clause}
        ORDER BY created_at DESC, id DESC
    """

    with closing(get_connection()) as connection:
        rows = connection.execute(
            query,
            tuple(parameters),
        ).fetchall()

        return [dict(row) for row in rows]


# --------------------------------------------------
# VERIFIED FILE ACCESS
# --------------------------------------------------

def open_document(
    document_id,
    *,
    actor_user_id,
    storage=None,
):
    """
    Open a document only after checking its content hash and size.

    Verification and use operate on the same open file descriptor.
    The caller is responsible for closing the returned stream.
    """

    require_permission(actor_user_id, "documents.view")

    document_id = _validate_id(
        document_id,
        "Document ID",
    )

    with closing(get_connection()) as connection:
        row = _get_document_row(connection, document_id)
        document = dict(row) if row else None

    if document is None:
        raise ValueError("Document record was not found.")

    storage = _get_document_storage(storage)

    stream = storage.open_file(document["storage_key"])

    try:
        digest = hashlib.sha256()
        total_size = 0

        while True:
            chunk = stream.read(64 * 1024)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_DOCUMENT_SIZE_BYTES:
                raise ValueError(
                    "Stored document exceeds the permitted size."
                )

            digest.update(chunk)

        if (
            total_size != document["size_bytes"]
            or digest.hexdigest() != document["sha256"]
        ):
            raise ValueError(
                "Stored document failed integrity verification."
            )

        stream.seek(0)
        return stream

    except Exception:
        stream.close()
        raise


def verify_document(
    document_id,
    *,
    actor_user_id,
    storage=None,
):
    require_permission(actor_user_id, "documents.view")

    document_id = _validate_id(
        document_id,
        "Document ID",
    )

    with closing(get_connection()) as connection:
        row = _get_document_row(connection, document_id)
        document = dict(row) if row else None

    if document is None:
        raise ValueError("Document record was not found.")

    storage = _get_document_storage(storage)

    return storage.verify_file(
        document["storage_key"],
        document["sha256"],
        document["size_bytes"],
    )


# --------------------------------------------------
# ARCHIVING
# --------------------------------------------------

def archive_document(document_id, *, actor_user_id):
    """
    Archive a document without deleting its file or database history.
    """

    require_permission(actor_user_id, "documents.archive")

    document_id = _validate_id(
        document_id,
        "Document ID",
    )

    actor_user_id = _validate_id(
        actor_user_id,
        "Actor user ID",
    )

    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            row = _get_document_row(
                connection,
                document_id,
            )

            if row is None:
                raise ValueError("Document record was not found.")

            if row["status"] == "archived":
                raise ValueError("Document is already archived.")

            connection.execute(
                """
                UPDATE documents
                SET status = 'archived',
                    archived_by = ?,
                    archived_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (actor_user_id, document_id),
            )

            updated = _get_document_row(
                connection,
                document_id,
            )

            return dict(updated)
