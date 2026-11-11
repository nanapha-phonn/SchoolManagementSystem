import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.database as database_module

from services.auth_service import (
    create_initial_admin,
    authenticate_user,
)
from services.user_service import create_user

from database.database import initialize_database
from services.subject_service import (
    create_subject,
    update_subject_status,
)
from services.teacher_subject_assignment_service import (
    create_teacher_subject_assignment,
    end_teacher_subject_assignment,
    get_teacher_subject_assignment,
    get_teacher_subject_assignments,
    reassign_teacher_subject_assignment,
)


def sample_assignment(**overrides):
    data = {
        "teacher_id": 1,
        "subject_id": 1,
        "section_id": 1,
        "academic_year_id": 1,
        "assigned_on": "2025-09-01",
    }
    data.update(overrides)
    return data


class TeacherSubjectAssignmentServiceTests(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = (
            Path(self.temp_directory.name) / "test_school.db"
        )

        self.db_path_patcher = patch.object(
            database_module,
            "DB_PATH",
            self.database_path,
        )
        self.db_path_patcher.start()

        self.addCleanup(self.db_path_patcher.stop)
        self.addCleanup(self.temp_directory.cleanup)

        initialize_database()

        create_initial_admin(
            "admin1", "AdminPass123", "Test Administrator"
        )
        admin = authenticate_user("admin1", "AdminPass123")
        self.admin_id = admin["id"]
        self.staff_id = create_user(
            "staff1", "StaffPass123", "Test Staff",
            "staff", self.admin_id
        )

        with closing(database_module.get_connection()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO teachers (
                        employee_no, first_name, last_name, status
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        ("T001", "Alice", "Teacher", "active"),
                        ("T002", "Bob", "Teacher", "active"),
                        ("T003", "Inactive", "Teacher", "inactive"),
                    ],
                )

                connection.execute(
                    """
                    INSERT INTO academic_years (
                        name, start_date, end_date
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        "2025-2026",
                        "2025-09-01",
                        "2026-08-31",
                    ),
                )

                connection.execute(
                    "INSERT INTO classes (name) VALUES (?)",
                    ("Grade 1",),
                )

                connection.executemany(
                    """
                    INSERT INTO sections (class_id, name)
                    VALUES (1, ?)
                    """,
                    [("A",), ("B",)],
                )

        self.subject_id = create_subject({
            "subject_code": "MATH101",
            "name": "Mathematics",
        }, actor_user_id=self.admin_id)

        self.second_subject_id = create_subject({
            "subject_code": "SCI101",
            "name": "Science",
        }, actor_user_id=self.admin_id)

    def test_01_create_and_retrieve_assignment(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        assignment = get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)

        self.assertIsNotNone(assignment)
        self.assertEqual(assignment["teacher_id"], 1)
        self.assertEqual(assignment["subject_id"], self.subject_id)
        self.assertEqual(assignment["section_id"], 1)
        self.assertEqual(assignment["academic_year_id"], 1)
        self.assertEqual(assignment["teacher_name"], "Alice Teacher")
        self.assertEqual(assignment["subject_name"], "Mathematics")
        self.assertEqual(assignment["class_name"], "Grade 1")
        self.assertEqual(assignment["section_name"], "A")
        self.assertEqual(assignment["academic_year_name"], "2025-2026")
        self.assertEqual(assignment["status"], "active")

    def test_02_retrieve_missing_assignment(self):
        self.assertIsNone(
            get_teacher_subject_assignment(999999, actor_user_id=self.admin_id)
        )

    def test_03_reject_invalid_assignment_ids(self):
        for invalid_id in (0, -1, "invalid", None, True):
            with self.subTest(assignment_id=invalid_id):
                with self.assertRaises(ValueError):
                    get_teacher_subject_assignment(invalid_id, actor_user_id=self.admin_id)

    def test_04_reject_invalid_assignment_data(self):
        invalid_cases = [
            ("invalid teacher ID", {"teacher_id": 0}),
            ("boolean teacher ID", {"teacher_id": True}),
            ("invalid subject ID", {"subject_id": "invalid"}),
            ("invalid section ID", {"section_id": -1}),
            ("invalid year ID", {"academic_year_id": None}),
            ("missing assignment date", {"assigned_on": ""}),
            ("invalid assignment date", {"assigned_on": "2025-13-01"}),
        ]

        for label, overrides in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    create_teacher_subject_assignment(
                        sample_assignment(**overrides),
                        actor_user_id=self.admin_id,
                    )

        self.assertEqual(get_teacher_subject_assignments(actor_user_id=self.admin_id), [])

    def test_05_reject_missing_teacher(self):
        with self.assertRaisesRegex(ValueError, "teacher was not found"):
            create_teacher_subject_assignment(
                sample_assignment(teacher_id=999),
                actor_user_id=self.admin_id,
            )

    def test_06_reject_inactive_teacher(self):
        with self.assertRaisesRegex(ValueError, "Only active teachers"):
            create_teacher_subject_assignment(
                sample_assignment(teacher_id=3),
                actor_user_id=self.admin_id,
            )

    def test_07_reject_missing_subject(self):
        with self.assertRaisesRegex(ValueError, "subject was not found"):
            create_teacher_subject_assignment(
                sample_assignment(subject_id=999),
                actor_user_id=self.admin_id,
            )

    def test_08_reject_inactive_subject(self):
        update_subject_status(self.subject_id, "inactive", actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "Only active subjects"):
            create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

    def test_09_reject_missing_section(self):
        with self.assertRaisesRegex(ValueError, "section was not found"):
            create_teacher_subject_assignment(
                sample_assignment(section_id=999),
                actor_user_id=self.admin_id,
            )

    def test_10_reject_missing_academic_year(self):
        with self.assertRaisesRegex(ValueError, "academic year was not found"):
            create_teacher_subject_assignment(
                sample_assignment(academic_year_id=999),
                actor_user_id=self.admin_id,
            )

    def test_11_reject_duplicate_active_assignment(self):
        create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "already has an active teacher",
        ):
            create_teacher_subject_assignment(
                sample_assignment(teacher_id=2),
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            len(get_teacher_subject_assignments(status="active", actor_user_id=self.admin_id)),
            1,
        )

    def test_12_allow_different_subject_or_section(self):
        first_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        second_id = create_teacher_subject_assignment(
            sample_assignment(
                subject_id=self.second_subject_id,
            ),
            actor_user_id=self.admin_id,
        )

        third_id = create_teacher_subject_assignment(
            sample_assignment(
                section_id=2,
            ),
            actor_user_id=self.admin_id,
        )

        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(second_id, third_id)
        self.assertEqual(len(get_teacher_subject_assignments(actor_user_id=self.admin_id)), 3)

    def test_13_reject_inactive_status_for_new_assignment(self):
        with self.assertRaisesRegex(ValueError, "must be active"):
            create_teacher_subject_assignment(
                sample_assignment(
                    ended_on="2026-01-01",
                    status="inactive",
                ),
                actor_user_id=self.admin_id,
            )

    def test_14_search_assignments(self):
        create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

        results = get_teacher_subject_assignments("Alice", actor_user_id=self.admin_id)
        self.assertEqual(len(results), 1)

        results = get_teacher_subject_assignments("MATH101", actor_user_id=self.admin_id)
        self.assertEqual(len(results), 1)

        results = get_teacher_subject_assignments("Grade 1", actor_user_id=self.admin_id)
        self.assertEqual(len(results), 1)

        results = get_teacher_subject_assignments("not-found", actor_user_id=self.admin_id)
        self.assertEqual(results, [])

    def test_15_filter_assignments(self):
        create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

        create_teacher_subject_assignment(
            sample_assignment(
                subject_id=self.second_subject_id,
                section_id=2,
            ),
            actor_user_id=self.admin_id,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(teacher_id=1, actor_user_id=self.admin_id)),
            2,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(subject_id=self.subject_id, actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(section_id=2, actor_user_id=self.admin_id)),
            1,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(academic_year_id=1, actor_user_id=self.admin_id)),
            2,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(status="active", actor_user_id=self.admin_id)),
            2,
        )

    def test_16_reject_invalid_assignment_filters(self):
        with self.assertRaises(ValueError):
            get_teacher_subject_assignments(teacher_id=0, actor_user_id=self.admin_id)

        with self.assertRaisesRegex(ValueError, "status filter"):
            get_teacher_subject_assignments(status="deleted", actor_user_id=self.admin_id)

    def test_17_end_assignment(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        end_teacher_subject_assignment(
            assignment_id,
            "2026-02-01",
            actor_user_id=self.admin_id,
        )

        assignment = get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)

        self.assertEqual(assignment["status"], "inactive")
        self.assertEqual(assignment["ended_on"], "2026-02-01")

        self.assertEqual(
            len(get_teacher_subject_assignments(status="active", actor_user_id=self.admin_id)),
            0,
        )

        self.assertEqual(
            len(get_teacher_subject_assignments(status="inactive", actor_user_id=self.admin_id)),
            1,
        )

    def test_18_reject_end_date_before_assignment_date(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "earlier"):
            end_teacher_subject_assignment(
                assignment_id,
                "2025-08-31",
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_19_reject_ending_missing_assignment(self):
        with self.assertRaisesRegex(
            ValueError,
            "was not found",
        ):
            end_teacher_subject_assignment(999999, "2026-02-01", actor_user_id=self.admin_id)

    def test_20_reject_ending_assignment_twice(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        end_teacher_subject_assignment(
            assignment_id,
            "2026-02-01",
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "already ended"):
            end_teacher_subject_assignment(
                assignment_id,
                "2026-03-01",
                actor_user_id=self.admin_id,
            )

    def test_21_reassign_teacher_and_preserve_history(self):
        old_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        new_id = reassign_teacher_subject_assignment(
            old_id,
            new_teacher_id=2,
            ended_on="2026-02-01",
            assigned_on="2026-02-02",
            actor_user_id=self.admin_id,
        )

        old_assignment = get_teacher_subject_assignment(old_id, actor_user_id=self.admin_id)
        new_assignment = get_teacher_subject_assignment(new_id, actor_user_id=self.admin_id)

        self.assertEqual(old_assignment["status"], "inactive")
        self.assertEqual(old_assignment["teacher_id"], 1)
        self.assertEqual(old_assignment["ended_on"], "2026-02-01")

        self.assertEqual(new_assignment["status"], "active")
        self.assertEqual(new_assignment["teacher_id"], 2)
        self.assertEqual(new_assignment["assigned_on"], "2026-02-02")

        self.assertEqual(len(get_teacher_subject_assignments(actor_user_id=self.admin_id)), 2)

    def test_22_reject_reassignment_to_same_teacher(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "different teacher"):
            reassign_teacher_subject_assignment(
                assignment_id,
                1,
                "2026-02-01",
                "2026-02-02",
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_23_reject_reassignment_with_invalid_date_order(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "must be after"):
            reassign_teacher_subject_assignment(
                assignment_id,
                2,
                "2026-02-01",
                "2026-02-01",
                actor_user_id=self.admin_id,
            )

        self.assertEqual(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_24_reassignment_failure_rolls_back_previous_assignment(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaisesRegex(ValueError, "Only active teachers"):
            reassign_teacher_subject_assignment(
                assignment_id,
                3,
                "2026-02-01",
                "2026-02-02",
                actor_user_id=self.admin_id,
            )

        old_assignment = get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)

        self.assertEqual(old_assignment["status"], "active")
        self.assertIsNone(old_assignment["ended_on"])
        self.assertEqual(len(get_teacher_subject_assignments(actor_user_id=self.admin_id)), 1)

    def test_25_new_teacher_can_be_assigned_after_previous_assignment_ends(self):
        old_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        end_teacher_subject_assignment(
            old_id,
            "2026-02-01",
            actor_user_id=self.admin_id,
        )

        new_id = create_teacher_subject_assignment(
            sample_assignment(
                teacher_id=2,
                assigned_on="2026-02-02",
            ),
            actor_user_id=self.admin_id,
        )

        self.assertEqual(
            get_teacher_subject_assignment(new_id, actor_user_id=self.admin_id)["status"],
            "active",
        )

    def test_26_active_assignment_prevents_subject_deactivation(self):
        create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

        with self.assertRaisesRegex(
            ValueError,
            "End all active teacher assignments",
        ):
            update_subject_status(self.subject_id, "inactive", actor_user_id=self.admin_id)

    def test_27_database_prevents_assignment_deletion(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        DELETE FROM teacher_subject_assignments
                        WHERE id = ?
                        """,
                        (assignment_id,),
                    )

        self.assertIsNotNone(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)
        )

    def test_28_database_prevents_core_assignment_changes(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        UPDATE teacher_subject_assignments
                        SET teacher_id = 2
                        WHERE id = ?
                        """,
                        (assignment_id,),
                    )

        self.assertEqual(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)["teacher_id"],
            1,
        )

    def test_29_database_prevents_ended_history_modification(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        end_teacher_subject_assignment(
            assignment_id,
            "2026-02-01",
            actor_user_id=self.admin_id,
        )

        with closing(database_module.get_connection()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute(
                        """
                        UPDATE teacher_subject_assignments
                        SET status = 'active',
                            ended_on = NULL
                        WHERE id = ?
                        """,
                        (assignment_id,),
                    )

        self.assertEqual(
            get_teacher_subject_assignment(assignment_id, actor_user_id=self.admin_id)["status"],
            "inactive",
        )

    def test_30_sqlite_database_integrity(self):
        create_teacher_subject_assignment(sample_assignment(), actor_user_id=self.admin_id)

        with closing(database_module.get_connection()) as connection:
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])


    def test_staff_can_manage_assignment_lifecycle(self):
        old_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.staff_id,
        )

        assignment = get_teacher_subject_assignment(
            old_id,
            actor_user_id=self.staff_id,
        )
        self.assertEqual(assignment["teacher_id"], 1)

        self.assertEqual(
            len(get_teacher_subject_assignments(
                teacher_id=1,
                actor_user_id=self.staff_id,
            )),
            1,
        )

        new_id = reassign_teacher_subject_assignment(
            old_id,
            new_teacher_id=2,
            ended_on="2026-02-01",
            assigned_on="2026-02-02",
            actor_user_id=self.staff_id,
        )

        old_assignment = get_teacher_subject_assignment(
            old_id,
            actor_user_id=self.staff_id,
        )
        new_assignment = get_teacher_subject_assignment(
            new_id,
            actor_user_id=self.staff_id,
        )

        self.assertEqual(old_assignment["status"], "inactive")
        self.assertEqual(new_assignment["teacher_id"], 2)
        self.assertEqual(new_assignment["status"], "active")

        end_teacher_subject_assignment(
            new_id,
            "2026-03-01",
            actor_user_id=self.staff_id,
        )

        self.assertEqual(
            get_teacher_subject_assignment(
                new_id,
                actor_user_id=self.staff_id,
            )["status"],
            "inactive",
        )

    def test_invalid_actor_cannot_access_or_change_assignments(self):
        assignment_id = create_teacher_subject_assignment(
            sample_assignment(),
            actor_user_id=self.admin_id,
        )

        with self.assertRaises(PermissionError):
            create_teacher_subject_assignment(
                sample_assignment(
                    subject_id=self.second_subject_id,
                ),
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            get_teacher_subject_assignment(
                assignment_id,
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            get_teacher_subject_assignments(
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            end_teacher_subject_assignment(
                assignment_id,
                "2026-02-01",
                actor_user_id=None,
            )

        with self.assertRaises(PermissionError):
            reassign_teacher_subject_assignment(
                assignment_id,
                new_teacher_id=2,
                ended_on="2026-02-01",
                assigned_on="2026-02-02",
                actor_user_id=None,
            )

        # Rejected calls must leave the active assignment unchanged.
        assignment = get_teacher_subject_assignment(
            assignment_id,
            actor_user_id=self.admin_id,
        )
        self.assertEqual(assignment["status"], "active")
        self.assertIsNone(assignment["ended_on"])
        self.assertEqual(
            len(get_teacher_subject_assignments(
                actor_user_id=self.admin_id,
            )),
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
