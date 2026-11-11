import hashlib
import os
import shutil
import stat
import tempfile
import unittest
import uuid

from pathlib import Path
from unittest.mock import patch

from storage.document_storage import DocumentStorage


PDF_CONTENT = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"%%EOF\n"
)

PNG_CONTENT = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
)

JPEG_CONTENT = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01"


class DocumentStorageTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="document_storage_test_"
        )

        self.test_root = Path(self.temp_dir.name)
        self.storage_root = self.test_root / "documents"
        self.input_dir = self.test_root / "input"

        self.input_dir.mkdir()

        self.storage = DocumentStorage(self.storage_root)

        self.addCleanup(self.temp_dir.cleanup)

    def create_source(self, name="certificate.pdf", content=PDF_CONTENT):
        path = self.input_dir / name
        path.write_bytes(content)
        return path

    # --------------------------------------------------
    # UPLOAD
    # --------------------------------------------------

    def test_01_store_valid_pdf(self):
        source = self.create_source(
            "birth_certificate.pdf"
        )

        stored = self.storage.store_file(
            source,
            "student",
            1,
        )

        self.assertEqual(stored.original_filename, "birth_certificate.pdf")
        self.assertEqual(stored.mime_type, "application/pdf")
        self.assertEqual(stored.file_extension, ".pdf")
        self.assertEqual(stored.size_bytes, len(PDF_CONTENT))
        self.assertEqual(
            stored.sha256,
            hashlib.sha256(PDF_CONTENT).hexdigest(),
        )

        self.assertRegex(
            stored.storage_key,
            r"^student/1/[0-9a-f]{32}\.pdf$",
        )

        self.assertTrue(
            (self.storage_root / stored.storage_key).is_file()
        )

        self.assertFalse(
            (self.storage_root / stored.storage_key).name
            == stored.original_filename
        )

    def test_02_store_valid_png_and_jpeg(self):
        cases = (
            ("photo.png", PNG_CONTENT, "image/png", ".png"),
            ("photo.jpg", JPEG_CONTENT, "image/jpeg", ".jpg"),
            ("photo.jpeg", JPEG_CONTENT, "image/jpeg", ".jpeg"),
        )

        for name, content, mime_type, extension in cases:
            with self.subTest(filename=name):
                stored = self.storage.store_file(
                    self.create_source(name, content),
                    "teacher",
                    3,
                )

                self.assertEqual(stored.mime_type, mime_type)
                self.assertEqual(stored.file_extension, extension)

    def test_03_reject_extension_that_does_not_match_signature(self):
        source = self.create_source(
            "fake.png",
            PDF_CONTENT,
        )

        with self.assertRaisesRegex(ValueError, "extension"):
            self.storage.store_file(source, "student", 1)

        self.assertFalse(self.storage_root.exists())

    def test_04_reject_unsupported_file_signature(self):
        source = self.create_source(
            "unknown.pdf",
            b"THIS IS NOT A PDF",
        )

        with self.assertRaisesRegex(ValueError, "content"):
            self.storage.store_file(source, "student", 1)

    def test_05_reject_unsupported_extension(self):
        source = self.create_source(
            "archive.zip",
            PDF_CONTENT,
        )

        with self.assertRaisesRegex(ValueError, "extension"):
            self.storage.store_file(source, "student", 1)

    def test_06_reject_empty_file(self):
        source = self.create_source("empty.pdf", b"")

        with self.assertRaisesRegex(ValueError, "Empty"):
            self.storage.store_file(source, "student", 1)

    def test_07_reject_file_over_ten_mb(self):
        source = self.input_dir / "large.pdf"

        with source.open("wb") as file:
            file.write(b"%PDF-1.4\n")
            file.seek(10 * 1024 * 1024)
            file.write(b"x")

        with self.assertRaisesRegex(ValueError, "10 MB"):
            self.storage.store_file(source, "student", 1)

        self.assertFalse(self.storage_root.exists())

    def test_08_reject_source_symbolic_link(self):
        source = self.create_source()
        link = self.input_dir / "linked.pdf"

        try:
            link.symlink_to(source)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable.")

        with self.assertRaisesRegex(ValueError, "Symbolic"):
            self.storage.store_file(link, "student", 1)

    def test_09_reject_directory_as_source(self):
        with self.assertRaises(ValueError):
            self.storage.store_file(
                self.input_dir,
                "student",
                1,
            )

    def test_10_reject_invalid_owner_type_and_id(self):
        source = self.create_source()

        invalid_cases = (
            ("unknown", 1),
            ("student", 0),
            ("student", -1),
            ("student", True),
            ("student", "1"),
        )

        for owner_type, owner_id in invalid_cases:
            with self.subTest(
                owner_type=owner_type,
                owner_id=owner_id,
            ):
                with self.assertRaises(ValueError):
                    self.storage.store_file(
                        source,
                        owner_type,
                        owner_id,
                    )

        self.assertFalse(self.storage_root.exists())

    # --------------------------------------------------
    # RETRIEVAL
    # --------------------------------------------------

    def test_11_open_stored_file(self):
        source = self.create_source()

        stored = self.storage.store_file(
            source,
            "student",
            12,
        )

        with self.storage.open_file(stored.storage_key) as file:
            content = file.read()

        self.assertEqual(content, PDF_CONTENT)

    def test_12_reject_traversal_and_malformed_storage_keys(self):
        invalid_keys = (
            "../outside.pdf",
            "/absolute/path.pdf",
            "student/1/../outside.pdf",
            "student/1/not-a-uuid.pdf",
            "unknown/1/" + uuid.uuid4().hex + ".pdf",
            "student/0/" + uuid.uuid4().hex + ".pdf",
            "student/1/" + uuid.uuid4().hex + ".exe",
            "student\\1\\" + uuid.uuid4().hex + ".pdf",
        )

        for key in invalid_keys:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.storage.open_file(key)

    def test_13_reject_symlinked_storage_directory(self):
        external_dir = self.test_root / "external"
        external_owner_dir = external_dir / "1"
        external_owner_dir.mkdir(parents=True)

        filename = uuid.uuid4().hex + ".pdf"
        external_file = external_owner_dir / filename
        external_file.write_bytes(PDF_CONTENT)

        self.storage_root.mkdir()
        owner_link = self.storage_root / "student"

        try:
            owner_link.symlink_to(external_dir)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable.")

        key = f"student/1/{filename}"

        with self.assertRaises(ValueError):
            self.storage.open_file(key)

    # --------------------------------------------------
    # INTEGRITY
    # --------------------------------------------------

    def test_14_verify_valid_file(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        self.assertTrue(
            self.storage.verify_file(
                stored.storage_key,
                stored.sha256,
                stored.size_bytes,
            )
        )

    def test_15_detect_modified_file(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        stored_path = self.storage_root / stored.storage_key
        stored_path.write_bytes(b"%PDF-1.4\nmodified")

        self.assertFalse(
            self.storage.verify_file(
                stored.storage_key,
                stored.sha256,
                stored.size_bytes,
            )
        )

    def test_16_missing_file_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.open_file(
                "student/1/" + uuid.uuid4().hex + ".pdf"
            )

    def test_17_invalid_verification_metadata_is_rejected(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        with self.assertRaises(ValueError):
            self.storage.verify_file(
                stored.storage_key,
                "invalid-hash",
                stored.size_bytes,
            )

        with self.assertRaises(ValueError):
            self.storage.verify_file(
                stored.storage_key,
                stored.sha256,
                True,
            )

    # --------------------------------------------------
    # FAILURE CLEANUP AND ISOLATION
    # --------------------------------------------------

    def test_18_failed_publication_cleans_temporary_file(self):
        source = self.create_source()

        with patch(
            "storage.document_storage.os.link",
            side_effect=OSError("Simulated publication failure"),
        ):
            with self.assertRaises(OSError):
                self.storage.store_file(
                    source,
                    "student",
                    1,
                )

        temporary_files = list(
            self.storage_root.rglob(".upload-*.tmp")
        )

        self.assertEqual(temporary_files, [])

    def test_19_storage_files_are_private(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        file_path = self.storage_root / stored.storage_key

        if os.name == "posix":
            self.assertEqual(
                stat.S_IMODE(file_path.stat().st_mode),
                0o600,
            )

            self.assertEqual(
                stat.S_IMODE(file_path.parent.stat().st_mode),
                0o700,
            )

    def test_20_tests_use_only_temporary_storage(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        self.assertTrue(
            (self.test_root.resolve())
            in (self.storage_root / stored.storage_key).resolve().parents
        )


    def test_21_discard_unregistered_file_for_database_rollback(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        stored_path = self.storage_root / stored.storage_key
        self.assertTrue(stored_path.is_file())

        result = self.storage.discard_unregistered_file(stored)

        self.assertTrue(result)
        self.assertFalse(stored_path.exists())

    def test_22_discard_refuses_modified_file(self):
        stored = self.storage.store_file(
            self.create_source(),
            "student",
            1,
        )

        stored_path = self.storage_root / stored.storage_key
        stored_path.write_bytes(b"%PDF-1.4\\nmodified")

        with self.assertRaisesRegex(ValueError, "integrity"):
            self.storage.discard_unregistered_file(stored)

        self.assertTrue(stored_path.is_file())

    def test_23_discard_rejects_arbitrary_storage_key_object(self):
        with self.assertRaisesRegex(ValueError, "StoredFile"):
            self.storage.discard_unregistered_file(
                "../outside.pdf"
            )


if __name__ == "__main__":
    unittest.main()
