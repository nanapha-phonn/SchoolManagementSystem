import unittest

from models.document import (
    Document,
    MAX_DOCUMENT_SIZE_BYTES,
    VALID_CATEGORIES_BY_OWNER,
)


def sample_document(**overrides):
    data = {
        "title": "Birth Certificate",
        "category": "birth_certificate",
        "original_filename": "birth_certificate.pdf",
        "storage_key": "student/1/7f3c2a91.pdf",
        "mime_type": "application/pdf",
        "file_extension": ".pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
        "uploaded_by": 1,
        "student_id": 1,
    }
    data.update(overrides)
    return data


class DocumentModelTests(unittest.TestCase):

    def test_01_valid_student_document(self):
        document = Document(**sample_document()).validate()

        self.assertEqual(document.owner_type, "student")
        self.assertEqual(document.status, "active")
        self.assertEqual(document.title, "Birth Certificate")

    def test_02_valid_document_for_each_owner_type(self):
        cases = [
            (
                "student",
                {
                    "student_id": 1,
                    "category": "birth_certificate",
                },
            ),
            (
                "teacher",
                {
                    "teacher_id": 1,
                    "category": "qualification_certificate",
                },
            ),
            (
                "transport_staff",
                {
                    "transport_staff_id": 1,
                    "category": "drivers_license",
                },
            ),
        ]

        for owner_type, owner_data in cases:
            with self.subTest(owner=owner_type):
                data = sample_document(
                    storage_key=f"{owner_type}/1/document.pdf",
                )
                data["student_id"] = None
                data.update(owner_data)

                document = Document(**data).validate()
                self.assertEqual(document.owner_type, owner_type)

    def test_03_document_requires_exactly_one_owner(self):
        data = sample_document(student_id=None)

        with self.assertRaisesRegex(ValueError, "exactly one"):
            Document(**data).validate()

    def test_04_document_rejects_multiple_owners(self):
        data = sample_document(teacher_id=2)

        with self.assertRaisesRegex(ValueError, "exactly one"):
            Document(**data).validate()

    def test_05_owner_id_must_be_positive_integer(self):
        invalid_ids = (0, -1, True, "invalid")

        for owner_id in invalid_ids:
            with self.subTest(owner_id=owner_id):
                data = sample_document(student_id=owner_id)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_06_category_must_match_owner_type(self):
        invalid_categories = (
            "drivers_license",
            "qualification_certificate",
            "unknown",
        )

        for category in invalid_categories:
            with self.subTest(category=category):
                data = sample_document(category=category)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_07_all_configured_categories_are_valid(self):
        for owner_type, categories in VALID_CATEGORIES_BY_OWNER.items():
            owner_field = f"{owner_type}_id"

            for category in categories:
                with self.subTest(
                    owner=owner_type,
                    category=category,
                ):
                    data = sample_document(
                        student_id=None,
                        category=category,
                        storage_key=f"{owner_type}/1/file.pdf",
                    )
                    data[owner_field] = 1

                    document = Document(**data).validate()
                    self.assertEqual(document.category, category)

    def test_08_title_is_required(self):
        data = sample_document(title=" ")

        with self.assertRaisesRegex(ValueError, "required"):
            Document(**data).validate()

    def test_09_title_length_is_limited(self):
        data = sample_document(title="A" * 151)

        with self.assertRaisesRegex(ValueError, "150"):
            Document(**data).validate()

    def test_10_title_rejects_control_characters(self):
        data = sample_document(title="Certificate\nInvalid")

        with self.assertRaises(ValueError):
            Document(**data).validate()

    def test_11_original_filename_is_required(self):
        data = sample_document(original_filename=" ")

        with self.assertRaisesRegex(ValueError, "required"):
            Document(**data).validate()

    def test_12_original_filename_rejects_directory_paths(self):
        unsafe_names = (
            "../certificate.pdf",
            "folder/certificate.pdf",
            r"folder\certificate.pdf",
        )

        for filename in unsafe_names:
            with self.subTest(filename=filename):
                data = sample_document(original_filename=filename)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_13_storage_key_rejects_unsafe_paths(self):
        unsafe_paths = (
            "../outside.pdf",
            "student/1/../outside.pdf",
            "/absolute/path.pdf",
            r"student\1\file.pdf",
            ".",
            "student/1/file:alternate.pdf",
            "student/1/file\x00.pdf",
            "student/1/file..pdf",
            "student/./1/file.pdf",
        )

        for storage_key in unsafe_paths:
            with self.subTest(storage_key=repr(storage_key)):
                data = sample_document(storage_key=storage_key)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_14_storage_key_accepts_safe_relative_path(self):
        data = sample_document(
            storage_key="student/1/generated-file.pdf"
        )

        document = Document(**data).validate()

        self.assertEqual(
            document.storage_key,
            "student/1/generated-file.pdf",
        )

    def test_15_pdf_file_type_is_valid(self):
        data = sample_document()

        document = Document(**data).validate()

        self.assertEqual(document.mime_type, "application/pdf")

    def test_16_jpeg_and_png_file_types_are_valid(self):
        cases = (
            ("image/jpeg", ".jpg"),
            ("image/jpeg", ".jpeg"),
            ("image/png", ".png"),
        )

        for mime_type, extension in cases:
            with self.subTest(extension=extension):
                data = sample_document(
                    mime_type=mime_type,
                    file_extension=extension,
                )

                Document(**data).validate()

    def test_17_mime_type_and_extension_must_match(self):
        data = sample_document(file_extension=".png")

        with self.assertRaisesRegex(ValueError, "does not match"):
            Document(**data).validate()

    def test_18_unsupported_mime_type_is_rejected(self):
        data = sample_document(
            mime_type="application/zip",
            file_extension=".zip",
        )

        with self.assertRaisesRegex(ValueError, "Unsupported"):
            Document(**data).validate()

    def test_19_document_size_must_be_positive(self):
        data = sample_document(size_bytes=0)

        with self.assertRaises(ValueError):
            Document(**data).validate()

    def test_20_document_size_cannot_exceed_ten_mb(self):
        data = sample_document(
            size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1
        )

        with self.assertRaisesRegex(ValueError, "10 MB"):
            Document(**data).validate()

    def test_21_document_size_must_be_integer(self):
        invalid_sizes = (True, 1.5, "1024")

        for size in invalid_sizes:
            with self.subTest(size=size):
                data = sample_document(size_bytes=size)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_22_sha256_must_contain_64_hexadecimal_characters(self):
        invalid_hashes = (
            "invalid",
            "a" * 63,
            "g" * 64,
        )

        for digest in invalid_hashes:
            with self.subTest(digest=digest):
                data = sample_document(sha256=digest)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_23_sha256_is_normalized_to_lowercase(self):
        data = sample_document(sha256="A" * 64)

        document = Document(**data).validate()

        self.assertEqual(document.sha256, "a" * 64)

    def test_24_uploader_id_must_be_positive_integer(self):
        invalid_ids = (0, -1, True, "invalid")

        for user_id in invalid_ids:
            with self.subTest(user_id=user_id):
                data = sample_document(uploaded_by=user_id)

                with self.assertRaises(ValueError):
                    Document(**data).validate()

    def test_25_description_length_is_limited(self):
        data = sample_document(description="A" * 1001)

        with self.assertRaisesRegex(ValueError, "1000"):
            Document(**data).validate()

    def test_26_active_document_cannot_have_archive_metadata(self):
        data = sample_document(archived_by=1)

        with self.assertRaisesRegex(ValueError, "Active"):
            Document(**data).validate()

    def test_27_archived_document_requires_archive_metadata(self):
        data = sample_document(status="archived")

        with self.assertRaisesRegex(ValueError, "require archive"):
            Document(**data).validate()

    def test_28_valid_archived_document(self):
        data = sample_document(
            status="archived",
            archived_by=1,
            archived_at="2026-11-10T18:00:00",
        )

        document = Document(**data).validate()

        self.assertEqual(document.status, "archived")
        self.assertEqual(document.archived_by, 1)

    def test_29_archived_document_rejects_invalid_timestamp(self):
        data = sample_document(
            status="archived",
            archived_by=1,
            archived_at="not-a-date",
        )

        with self.assertRaisesRegex(ValueError, "ISO"):
            Document(**data).validate()

    def test_30_invalid_document_status_is_rejected(self):
        data = sample_document(status="deleted")

        with self.assertRaisesRegex(ValueError, "Invalid"):
            Document(**data).validate()


if __name__ == "__main__":
    unittest.main()
