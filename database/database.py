import sqlite3
from config.settings import DB_PATH

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def initialize_database():
    with get_connection() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS academic_years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 0
                CHECK (is_current IN (0, 1))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_current_academic_year
            ON academic_years(is_current)
            WHERE is_current = 1;

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id)
                ON DELETE RESTRICT,
            UNIQUE (class_id, name)
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_no TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth TEXT,
            gender TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            guardian_name TEXT,
            guardian_phone TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'graduated', 'transferred')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            academic_year_id INTEGER NOT NULL,
            enrolled_on TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'enrolled',
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE RESTRICT,
            FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE RESTRICT,
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE RESTRICT,
            UNIQUE (student_id, academic_year_id)
        );

        CREATE TRIGGER IF NOT EXISTS trg_prevent_enrollment_delete
        BEFORE DELETE ON enrollments
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Enrollment history cannot be deleted.'
            );
        END;

        CREATE INDEX IF NOT EXISTS idx_students_name
            ON students(last_name, first_name);
        CREATE INDEX IF NOT EXISTS idx_enrollments_section
            ON enrollments(section_id, academic_year_id);
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_no TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth TEXT,
            gender TEXT CHECK (
                gender IS NULL OR
                gender IN ('Male', 'Female', 'Other')
            ),
            phone TEXT,
            email TEXT,
            address TEXT,
            qualification TEXT,
            specialization TEXT,
            department TEXT,
            employment_date TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (
                    status IN (
                        'active',
                        'inactive',
                        'resigned',
                        'terminated'
                    )
                ),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_teachers_name
            ON teachers(last_name, first_name);

        -- TRANSPORTATION MANAGEMENT

        CREATE TABLE IF NOT EXISTS transport_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER,
            employee_no TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            role TEXT NOT NULL
                CHECK (role IN ('driver', 'attendant')),
            license_number TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive', 'resigned', 'terminated')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER,
            registration_no TEXT NOT NULL UNIQUE,
            vehicle_type TEXT,
            model TEXT,
            capacity INTEGER NOT NULL
                CHECK (capacity > 0),
            driver_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'maintenance', 'retired')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (driver_id) REFERENCES transport_staff(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS transport_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER,
            route_code TEXT NOT NULL UNIQUE,
            route_name TEXT NOT NULL,
            description TEXT,
            vehicle_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS route_stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            stop_name TEXT NOT NULL,
            address TEXT,
            stop_order INTEGER NOT NULL
                CHECK (stop_order > 0),
            pickup_time TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (route_id) REFERENCES transport_routes(id)
                ON DELETE RESTRICT,
            UNIQUE (route_id, stop_order),
            UNIQUE (id, route_id)
        );

        CREATE TABLE IF NOT EXISTS student_transport_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            pickup_stop_id INTEGER,
            dropoff_stop_id INTEGER,
            start_date TEXT NOT NULL,
            end_date TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'completed', 'cancelled')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (route_id) REFERENCES transport_routes(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (pickup_stop_id, route_id)
                REFERENCES route_stops(id, route_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (dropoff_stop_id, route_id)
                REFERENCES route_stops(id, route_id)
                ON DELETE RESTRICT,
            CHECK (end_date IS NULL OR end_date >= start_date)
        );

        -- TRANSPORTATION INDEXES

        CREATE INDEX IF NOT EXISTS idx_transport_staff_name
            ON transport_staff(last_name, first_name);

        CREATE INDEX IF NOT EXISTS idx_vehicles_status
            ON vehicles(status);

        CREATE INDEX IF NOT EXISTS idx_transport_routes_status
            ON transport_routes(status);

        CREATE INDEX IF NOT EXISTS idx_route_stops_route
            ON route_stops(route_id, stop_order);

        CREATE INDEX IF NOT EXISTS idx_transport_assignments_route
            ON student_transport_assignments(route_id, status);

        CREATE INDEX IF NOT EXISTS idx_transport_assignments_student
            ON student_transport_assignments(student_id);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_transport_per_student
            ON student_transport_assignments(student_id)
            WHERE status = 'active';

        -- TRANSACTION MANAGEMENT: STUDENT FEE CHARGES

        CREATE TABLE IF NOT EXISTS fee_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER,
            charge_no TEXT NOT NULL UNIQUE,
            student_id INTEGER NOT NULL,
            fee_type TEXT NOT NULL
                CHECK (fee_type IN ('class', 'hostel', 'bus')),
            enrollment_id INTEGER,
            transport_assignment_id INTEGER,
            description TEXT NOT NULL,
            amount_minor INTEGER NOT NULL
                CHECK (amount_minor > 0),
            currency TEXT NOT NULL DEFAULT 'USD'
                CHECK (
                    length(currency) = 3
                    AND currency = upper(currency)
                ),
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'voided')),
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            voided_at TEXT,
            void_reason TEXT,

            FOREIGN KEY (school_id) REFERENCES schools(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (student_id) REFERENCES students(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (transport_assignment_id)
                REFERENCES student_transport_assignments(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (created_by) REFERENCES users(id)
                ON DELETE RESTRICT,

            CHECK (
                (fee_type = 'bus'
                    AND transport_assignment_id IS NOT NULL
                    AND enrollment_id IS NULL)
                OR
                (fee_type = 'class'
                    AND transport_assignment_id IS NULL)
                OR
                (fee_type = 'hostel'
                    AND transport_assignment_id IS NULL
                    AND enrollment_id IS NULL)
            ),

            CHECK (
                (status = 'open'
                    AND voided_at IS NULL
                    AND void_reason IS NULL)
                OR
                (status = 'voided'
                    AND voided_at IS NOT NULL
                    AND void_reason IS NOT NULL
                    AND length(trim(void_reason)) > 0)
            )
        );

        -- TRANSACTION MANAGEMENT: FEE PAYMENTS AND RECEIPTS

        CREATE TABLE IF NOT EXISTS fee_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            charge_id INTEGER NOT NULL,
            amount_minor INTEGER NOT NULL
                CHECK (amount_minor > 0),
            payment_date TEXT NOT NULL,
            payment_method TEXT NOT NULL
                CHECK (
                    payment_method IN (
                        'cash',
                        'bank_transfer',
                        'card',
                        'cheque',
                        'mobile_money',
                        'khqr',
                        'other'
                    )
                ),
            transaction_reference TEXT,
            received_by INTEGER,
            status TEXT NOT NULL DEFAULT 'posted'
                CHECK (status IN ('posted', 'voided')),
            voided_at TEXT,
            void_reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (charge_id) REFERENCES fee_charges(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (received_by) REFERENCES users(id)
                ON DELETE RESTRICT,

            CHECK (
                (status = 'posted'
                    AND voided_at IS NULL
                    AND void_reason IS NULL)
                OR
                (status = 'voided'
                    AND voided_at IS NOT NULL
                    AND void_reason IS NOT NULL
                    AND length(trim(void_reason)) > 0)
            )
        );

        -- TRANSACTION MANAGEMENT: EMPLOYEE SALARY SLIPS

        CREATE TABLE IF NOT EXISTS salary_slips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slip_no TEXT NOT NULL UNIQUE,
            school_id INTEGER,
            teacher_id INTEGER,
            transport_staff_id INTEGER,
            pay_period_start TEXT NOT NULL,
            pay_period_end TEXT NOT NULL,
            base_salary_minor INTEGER NOT NULL
                CHECK (base_salary_minor >= 0),
            allowances_minor INTEGER NOT NULL DEFAULT 0
                CHECK (allowances_minor >= 0),
            deductions_minor INTEGER NOT NULL DEFAULT 0
                CHECK (deductions_minor >= 0),
            net_salary_minor INTEGER NOT NULL
                CHECK (net_salary_minor >= 0),
            currency TEXT NOT NULL DEFAULT 'USD'
                CHECK (
                    length(currency) = 3
                    AND currency = upper(currency)
                ),
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'issued', 'paid', 'voided')),
            payment_date TEXT,
            payment_method TEXT
                CHECK (
                    payment_method IS NULL
                    OR payment_method IN (
                        'cash',
                        'bank_transfer',
                        'card',
                        'cheque',
                        'mobile_money',
                        'khqr',
                        'other'
                    )
                ),
            transaction_reference TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            issued_at TEXT,
            paid_at TEXT,
            voided_at TEXT,
            void_reason TEXT,

            FOREIGN KEY (school_id) REFERENCES schools(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (transport_staff_id) REFERENCES transport_staff(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (created_by) REFERENCES users(id)
                ON DELETE RESTRICT,

            CHECK (
                (teacher_id IS NOT NULL AND transport_staff_id IS NULL)
                OR
                (teacher_id IS NULL AND transport_staff_id IS NOT NULL)
            ),

            CHECK (pay_period_end >= pay_period_start),

            CHECK (
                net_salary_minor =
                    base_salary_minor
                    + allowances_minor
                    - deductions_minor
            ),

            CHECK (
                (status = 'draft'
                    AND issued_at IS NULL
                    AND payment_date IS NULL
                    AND payment_method IS NULL
                    AND paid_at IS NULL
                    AND voided_at IS NULL
                    AND void_reason IS NULL)
                OR
                (status = 'issued'
                    AND issued_at IS NOT NULL
                    AND payment_date IS NULL
                    AND payment_method IS NULL
                    AND paid_at IS NULL
                    AND voided_at IS NULL
                    AND void_reason IS NULL)
                OR
                (status = 'paid'
                    AND issued_at IS NOT NULL
                    AND payment_date IS NOT NULL
                    AND payment_method IS NOT NULL
                    AND paid_at IS NOT NULL
                    AND voided_at IS NULL
                    AND void_reason IS NULL)
                OR
                (status = 'voided'
                    AND voided_at IS NOT NULL
                    AND void_reason IS NOT NULL
                    AND length(trim(void_reason)) > 0)
            )
        );

        -- TRANSACTION MANAGEMENT INDEXES

        CREATE INDEX IF NOT EXISTS idx_fee_charges_student
            ON fee_charges(student_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_fee_charges_type_status
            ON fee_charges(fee_type, status, due_date);

        CREATE INDEX IF NOT EXISTS idx_fee_payments_charge_status
            ON fee_payments(charge_id, status);

        CREATE INDEX IF NOT EXISTS idx_fee_payments_date
            ON fee_payments(payment_date);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_salary_slip_teacher_period
            ON salary_slips(
                teacher_id,
                pay_period_start,
                pay_period_end
            )
            WHERE teacher_id IS NOT NULL AND status != 'voided';

        CREATE UNIQUE INDEX IF NOT EXISTS idx_salary_slip_transport_staff_period
            ON salary_slips(
                transport_staff_id,
                pay_period_start,
                pay_period_end
            )
            WHERE transport_staff_id IS NOT NULL AND status != 'voided';


        -- ACADEMIC RECORDS: SUBJECT CATALOGUE

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- ACADEMIC RECORDS: TEACHER SUBJECT ASSIGNMENTS

        CREATE TABLE IF NOT EXISTS teacher_subject_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            academic_year_id INTEGER NOT NULL,
            assigned_on TEXT NOT NULL,
            ended_on TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'inactive')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (teacher_id) REFERENCES teachers(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (section_id) REFERENCES sections(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (academic_year_id) REFERENCES academic_years(id)
                ON DELETE RESTRICT,

            CHECK (
                ended_on IS NULL OR ended_on >= assigned_on
            ),

            CHECK (
                (status = 'active' AND ended_on IS NULL)
                OR
                (status = 'inactive' AND ended_on IS NOT NULL)
            )
        );

        -- ACADEMIC RECORDS INDEXES

        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_one_active_teacher_subject_assignment
        ON teacher_subject_assignments(
            subject_id,
            section_id,
            academic_year_id
        )
        WHERE status = 'active';

        CREATE INDEX IF NOT EXISTS
            idx_teacher_subject_assignments_teacher
        ON teacher_subject_assignments(
            teacher_id,
            academic_year_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_teacher_subject_assignments_section
        ON teacher_subject_assignments(
            section_id,
            academic_year_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_teacher_subject_assignments_subject
        ON teacher_subject_assignments(
            subject_id,
            academic_year_id
        );

        -- ACADEMIC RECORDS HISTORY PROTECTION

        CREATE TRIGGER IF NOT EXISTS trg_prevent_subject_delete
        BEFORE DELETE ON subjects
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Subjects cannot be deleted. Deactivate the subject instead.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_teacher_subject_assignment_delete
        BEFORE DELETE ON teacher_subject_assignments
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Teacher assignment history cannot be deleted.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_teacher_subject_assignment_core_update
        BEFORE UPDATE OF
            teacher_id,
            subject_id,
            section_id,
            academic_year_id,
            assigned_on
        ON teacher_subject_assignments
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assignment history details cannot be changed.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_ended_teacher_subject_assignment_update
        BEFORE UPDATE ON teacher_subject_assignments
        FOR EACH ROW
        WHEN OLD.status = 'inactive'
        BEGIN
            SELECT RAISE(
                ABORT,
                'Ended assignment history cannot be changed.'
            );
        END;


        -- ACADEMIC RECORDS: ASSESSMENT PERIODS

        CREATE TABLE IF NOT EXISTS assessment_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            period_type TEXT NOT NULL
                CHECK (
                    period_type IN (
                        'midterm',
                        'final',
                        'term',
                        'semester',
                        'other'
                    )
                ),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (
                    status IN ('planned', 'active', 'completed')
                ),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (academic_year_id)
                REFERENCES academic_years(id)
                ON DELETE RESTRICT,

            CHECK (length(trim(name)) BETWEEN 1 AND 150),

            CHECK (
                length(start_date) = 10
                AND start_date GLOB
                    '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                AND date(julianday(start_date)) = start_date
            ),

            CHECK (
                length(end_date) = 10
                AND end_date GLOB
                    '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                AND date(julianday(end_date)) = end_date
            ),

            CHECK (end_date >= start_date)
        );

        -- ASSESSMENT PERIOD INDEXES

        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_assessment_period_year_name
        ON assessment_periods(
            academic_year_id,
            name COLLATE NOCASE
        );

        CREATE INDEX IF NOT EXISTS
            idx_assessment_period_year_dates
        ON assessment_periods(
            academic_year_id,
            start_date,
            end_date
        );

        CREATE INDEX IF NOT EXISTS
            idx_assessment_period_status
        ON assessment_periods(status, start_date);

        -- ASSESSMENT PERIOD ACADEMIC-YEAR BOUNDARY PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_year_boundary_insert
        BEFORE INSERT ON assessment_periods
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM academic_years
            WHERE id = NEW.academic_year_id
              AND NEW.start_date >= start_date
              AND NEW.end_date <= end_date
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment dates must fall within the academic year.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_year_boundary_update
        BEFORE UPDATE OF
            academic_year_id,
            start_date,
            end_date
        ON assessment_periods
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM academic_years
            WHERE id = NEW.academic_year_id
              AND NEW.start_date >= start_date
              AND NEW.end_date <= end_date
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment dates must fall within the academic year.'
            );
        END;

        -- ASSESSMENT PERIOD OVERLAP PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_no_overlap_insert
        BEFORE INSERT ON assessment_periods
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM assessment_periods
            WHERE academic_year_id = NEW.academic_year_id
              AND NEW.start_date <= end_date
              AND NEW.end_date >= start_date
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment periods cannot overlap within an academic year.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_no_overlap_update
        BEFORE UPDATE OF
            academic_year_id,
            start_date,
            end_date
        ON assessment_periods
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM assessment_periods
            WHERE academic_year_id = NEW.academic_year_id
              AND id != OLD.id
              AND NEW.start_date <= end_date
              AND NEW.end_date >= start_date
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment periods cannot overlap within an academic year.'
            );
        END;

        -- ASSESSMENT PERIOD LIFECYCLE PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_initial_status
        BEFORE INSERT ON assessment_periods
        FOR EACH ROW
        WHEN NEW.status != 'planned'
        BEGIN
            SELECT RAISE(
                ABORT,
                'New assessment periods must start as planned.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_assessment_period_status_transition
        BEFORE UPDATE OF status ON assessment_periods
        FOR EACH ROW
        WHEN NEW.status != OLD.status
         AND NOT (
             (OLD.status = 'planned' AND NEW.status = 'active')
             OR
             (OLD.status = 'active' AND NEW.status = 'completed')
         )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Invalid assessment-period status transition.'
            );
        END;

        -- ASSESSMENT PERIOD HISTORY PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_assessment_period_delete
        BEFORE DELETE ON assessment_periods
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment period history cannot be deleted.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_completed_assessment_period_update
        BEFORE UPDATE ON assessment_periods
        FOR EACH ROW
        WHEN OLD.status = 'completed'
        BEGIN
            SELECT RAISE(
                ABORT,
                'Completed assessment periods cannot be changed.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_assessment_period_year_change
        BEFORE UPDATE OF academic_year_id ON assessment_periods
        FOR EACH ROW
        WHEN NEW.academic_year_id != OLD.academic_year_id
        BEGIN
            SELECT RAISE(
                ABORT,
                'An assessment period cannot be moved to another academic year.'
            );
        END;

        -- ACADEMIC YEAR DATE PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_invalid_academic_year_date_update
        BEFORE UPDATE OF start_date, end_date ON academic_years
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM assessment_periods
            WHERE academic_year_id = OLD.id
              AND (
                  start_date < NEW.start_date
                  OR end_date > NEW.end_date
              )
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Academic-year dates cannot invalidate existing assessment periods.'
            );
        END;


        -- ACADEMIC RECORDS: GRADING SCHEMES

        CREATE TABLE IF NOT EXISTS grading_schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            academic_year_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            version_no INTEGER NOT NULL CHECK (version_no > 0),
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'active', 'archived')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (class_id)
                REFERENCES classes(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (academic_year_id)
                REFERENCES academic_years(id)
                ON DELETE RESTRICT,

            UNIQUE (class_id, academic_year_id, version_no),

            CHECK (length(trim(name)) BETWEEN 1 AND 150)
        );

        CREATE TABLE IF NOT EXISTS grade_bands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grading_scheme_id INTEGER NOT NULL,
            grade_label TEXT NOT NULL,
            min_percentage REAL NOT NULL
                CHECK (min_percentage >= 0 AND min_percentage <= 100),
            grade_point REAL
                CHECK (grade_point IS NULL OR grade_point >= 0),
            remark TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (grading_scheme_id)
                REFERENCES grading_schemes(id)
                ON DELETE RESTRICT,

            UNIQUE (grading_scheme_id, grade_label COLLATE NOCASE),
            UNIQUE (grading_scheme_id, min_percentage),

            CHECK (length(trim(grade_label)) BETWEEN 1 AND 20),
            CHECK (length(remark) <= 300)
        );

        -- GRADING SCHEME INDEXES

        CREATE INDEX IF NOT EXISTS idx_grading_schemes_class_year
        ON grading_schemes(class_id, academic_year_id, version_no);

        CREATE UNIQUE INDEX IF NOT EXISTS
            idx_one_active_grading_scheme_per_class_year
        ON grading_schemes(class_id, academic_year_id)
        WHERE status = 'active';

        CREATE INDEX IF NOT EXISTS idx_grade_bands_scheme_threshold
        ON grade_bands(grading_scheme_id, min_percentage DESC);

        -- GRADING SCHEME HISTORY PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_grading_scheme_identity_immutable
        BEFORE UPDATE OF class_id, academic_year_id, version_no
        ON grading_schemes
        FOR EACH ROW
        WHEN NEW.class_id != OLD.class_id
          OR NEW.academic_year_id != OLD.academic_year_id
          OR NEW.version_no != OLD.version_no
        BEGIN
            SELECT RAISE(
                ABORT,
                'Grading scheme identity and version cannot be changed.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grading_scheme_name_draft_only
        BEFORE UPDATE OF name ON grading_schemes
        FOR EACH ROW
        WHEN OLD.status != 'draft'
        BEGIN
            SELECT RAISE(
                ABORT,
                'Only draft grading schemes can be renamed.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grading_scheme_initial_status
        BEFORE INSERT ON grading_schemes
        FOR EACH ROW
        WHEN NEW.status != 'draft'
        BEGIN
            SELECT RAISE(
                ABORT,
                'New grading schemes must start as draft.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grading_scheme_status_transition
        BEFORE UPDATE OF status ON grading_schemes
        FOR EACH ROW
        WHEN NEW.status != OLD.status
         AND NOT (
             (OLD.status = 'draft' AND NEW.status = 'active')
             OR
             (OLD.status = 'draft' AND NEW.status = 'archived')
             OR
             (OLD.status = 'active' AND NEW.status = 'archived')
         )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Invalid grading scheme status transition.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grading_scheme_activation_requirements
        BEFORE UPDATE OF status ON grading_schemes
        FOR EACH ROW
        WHEN OLD.status = 'draft'
         AND NEW.status = 'active'
         AND (
             (
                 SELECT COUNT(*)
                 FROM grade_bands
                 WHERE grading_scheme_id = NEW.id
             ) < 2
             OR
             (
                 SELECT COUNT(*)
                 FROM grade_bands
                 WHERE grading_scheme_id = NEW.id
                   AND min_percentage = 0
             ) != 1
         )
        BEGIN
            SELECT RAISE(
                ABORT,
                'An active grading scheme requires at least two grade bands and exactly one 0 percent threshold.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_grading_scheme_delete
        BEFORE DELETE ON grading_schemes
        FOR EACH ROW
        BEGIN
            SELECT RAISE(
                ABORT,
                'Grading scheme history cannot be deleted.'
            );
        END;

        -- GRADE BAND DRAFT-ONLY PROTECTION

        CREATE TRIGGER IF NOT EXISTS
            trg_grade_band_insert_draft_only
        BEFORE INSERT ON grade_bands
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM grading_schemes
            WHERE id = NEW.grading_scheme_id
              AND status = 'draft'
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Grade bands can only be added to an existing draft grading scheme.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grade_band_scheme_immutable
        BEFORE UPDATE OF grading_scheme_id ON grade_bands
        FOR EACH ROW
        WHEN NEW.grading_scheme_id != OLD.grading_scheme_id
        BEGIN
            SELECT RAISE(
                ABORT,
                'A grade band cannot be moved to another grading scheme.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grade_band_update_draft_only
        BEFORE UPDATE ON grade_bands
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM grading_schemes
            WHERE id = OLD.grading_scheme_id
              AND status = 'draft'
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Only draft grading schemes can have their grade bands changed.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_grade_band_delete_draft_only
        BEFORE DELETE ON grade_bands
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM grading_schemes
            WHERE id = OLD.grading_scheme_id
              AND status = 'draft'
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Grade bands in active or archived schemes cannot be deleted.'
            );
        END;


        -- ACADEMIC RECORDS: STUDENT SUBJECT RESULTS

        CREATE TABLE IF NOT EXISTS student_subject_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            enrollment_id INTEGER NOT NULL,
            assessment_period_id INTEGER NOT NULL,
            teacher_subject_assignment_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            grading_scheme_id INTEGER NOT NULL,

            marks_obtained REAL NOT NULL,
            maximum_marks REAL NOT NULL,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (enrollment_id)
                REFERENCES enrollments(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (assessment_period_id)
                REFERENCES assessment_periods(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (teacher_subject_assignment_id)
                REFERENCES teacher_subject_assignments(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (subject_id)
                REFERENCES subjects(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (grading_scheme_id)
                REFERENCES grading_schemes(id)
                ON DELETE RESTRICT,

            UNIQUE (
                enrollment_id,
                assessment_period_id,
                subject_id
            ),

            CHECK (
                typeof(marks_obtained) IN ('integer', 'real')
                AND marks_obtained >= 0
            ),

            CHECK (
                typeof(maximum_marks) IN ('integer', 'real')
                AND maximum_marks > 0
            ),

            CHECK (marks_obtained <= maximum_marks)
        );

        -- RESULT SEARCH INDEXES

        CREATE INDEX IF NOT EXISTS
            idx_student_subject_results_period_enrollment
        ON student_subject_results(
            assessment_period_id,
            enrollment_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_student_subject_results_assignment
        ON student_subject_results(
            teacher_subject_assignment_id
        );

        CREATE INDEX IF NOT EXISTS
            idx_student_subject_results_grading_scheme
        ON student_subject_results(
            grading_scheme_id
        );

        -- VALIDATE ALL ACADEMIC REFERENCES ON RESULT CREATION

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_validate_insert
        BEFORE INSERT ON student_subject_results
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM enrollments AS e

            JOIN sections AS sec
                ON sec.id = e.section_id

            JOIN assessment_periods AS ap
                ON ap.id = NEW.assessment_period_id

            JOIN teacher_subject_assignments AS tsa
                ON tsa.id = NEW.teacher_subject_assignment_id

            JOIN grading_schemes AS gs
                ON gs.id = NEW.grading_scheme_id

            WHERE e.id = NEW.enrollment_id

              AND e.academic_year_id = ap.academic_year_id

              AND e.section_id = tsa.section_id
              AND e.academic_year_id = tsa.academic_year_id

              AND tsa.subject_id = NEW.subject_id

              AND e.enrolled_on <= ap.end_date

              AND tsa.assigned_on <= ap.end_date
              AND (
                  tsa.ended_on IS NULL
                  OR tsa.ended_on >= ap.start_date
              )

              AND ap.status = 'active'

              AND gs.class_id = sec.class_id
              AND gs.academic_year_id = e.academic_year_id
              AND gs.status = 'active'
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Student result references do not match the enrollment, assessment period, teacher assignment, subject, or active grading scheme.'
            );
        END;

        -- KEEP ONE GRADING SCHEME VERSION PER CLASS AND PERIOD

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_consistent_scheme
        BEFORE INSERT ON student_subject_results
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM student_subject_results AS existing

            JOIN enrollments AS existing_enrollment
                ON existing_enrollment.id = existing.enrollment_id

            JOIN sections AS existing_section
                ON existing_section.id = existing_enrollment.section_id

            JOIN enrollments AS new_enrollment
                ON new_enrollment.id = NEW.enrollment_id

            JOIN sections AS new_section
                ON new_section.id = new_enrollment.section_id

            WHERE existing.assessment_period_id = NEW.assessment_period_id
              AND existing_section.class_id = new_section.class_id
              AND existing.grading_scheme_id != NEW.grading_scheme_id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'All student results for the same class and assessment period must use the same grading scheme.'
            );
        END;

        -- RESULT ACADEMIC IDENTITY IS IMMUTABLE

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_identity_immutable
        BEFORE UPDATE OF
            enrollment_id,
            assessment_period_id,
            teacher_subject_assignment_id,
            subject_id,
            grading_scheme_id
        ON student_subject_results
        FOR EACH ROW
        WHEN NEW.enrollment_id != OLD.enrollment_id
          OR NEW.assessment_period_id != OLD.assessment_period_id
          OR NEW.teacher_subject_assignment_id != OLD.teacher_subject_assignment_id
          OR NEW.subject_id != OLD.subject_id
          OR NEW.grading_scheme_id != OLD.grading_scheme_id
        BEGIN
            SELECT RAISE(
                ABORT,
                'Student result academic references cannot be changed.'
            );
        END;

        -- MARKS MAY ONLY CHANGE WHILE THE ASSESSMENT IS ACTIVE

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_update_active_only
        BEFORE UPDATE OF marks_obtained, maximum_marks
        ON student_subject_results
        FOR EACH ROW
        WHEN (
            SELECT status
            FROM assessment_periods
            WHERE id = OLD.assessment_period_id
        ) != 'active'
        BEGIN
            SELECT RAISE(
                ABORT,
                'Results can only be changed while the assessment period is active.'
            );
        END;

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_delete_active_only
        BEFORE DELETE ON student_subject_results
        FOR EACH ROW
        WHEN (
            SELECT status
            FROM assessment_periods
            WHERE id = OLD.assessment_period_id
        ) != 'active'
        BEGIN
            SELECT RAISE(
                ABORT,
                'Results cannot be deleted after the assessment period is completed.'
            );
        END;

        -- UPDATE RESULT TIMESTAMP AUTOMATICALLY

        CREATE TRIGGER IF NOT EXISTS
            trg_student_subject_result_updated_at
        AFTER UPDATE OF marks_obtained, maximum_marks
        ON student_subject_results
        FOR EACH ROW
        BEGIN
            UPDATE student_subject_results
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END;

        -- PROTECT RESULT VALIDITY IF AN ASSIGNMENT ENDS

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_assignment_end_invalidating_results
        BEFORE UPDATE OF ended_on ON teacher_subject_assignments
        FOR EACH ROW
        WHEN NEW.ended_on IS NOT NULL
         AND EXISTS (
             SELECT 1
             FROM student_subject_results AS r
             JOIN assessment_periods AS ap
                 ON ap.id = r.assessment_period_id
             WHERE r.teacher_subject_assignment_id = OLD.id
               AND NEW.ended_on < ap.start_date
         )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assignment end date cannot invalidate existing student results.'
            );
        END;

        -- PROTECT RESULT VALIDITY IF ASSESSMENT DATES CHANGE

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_assessment_date_invalidating_results
        BEFORE UPDATE OF start_date, end_date
        ON assessment_periods
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM student_subject_results AS r

            JOIN enrollments AS e
                ON e.id = r.enrollment_id

            JOIN teacher_subject_assignments AS tsa
                ON tsa.id = r.teacher_subject_assignment_id

            WHERE r.assessment_period_id = OLD.id
              AND (
                  e.enrolled_on > NEW.end_date
                  OR tsa.assigned_on > NEW.end_date
                  OR (
                      tsa.ended_on IS NOT NULL
                      AND tsa.ended_on < NEW.start_date
                  )
              )
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Assessment dates cannot invalidate existing student results.'
            );
        END;

        -- PROTECT ENROLLMENT IDENTITY AFTER RESULTS EXIST

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_enrollment_result_identity_change
        BEFORE UPDATE OF
            student_id,
            section_id,
            academic_year_id,
            enrolled_on
        ON enrollments
        FOR EACH ROW
        WHEN (
            NEW.student_id != OLD.student_id
            OR NEW.section_id != OLD.section_id
            OR NEW.academic_year_id != OLD.academic_year_id
            OR NEW.enrolled_on != OLD.enrolled_on
        )
        AND EXISTS (
            SELECT 1
            FROM student_subject_results
            WHERE enrollment_id = OLD.id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'Enrollment identity cannot change after student results have been recorded.'
            );
        END;

        -- PROTECT THE CLASS OF A SECTION WITH EXISTING RESULTS

        CREATE TRIGGER IF NOT EXISTS
            trg_prevent_section_class_change_with_results
        BEFORE UPDATE OF class_id ON sections
        FOR EACH ROW
        WHEN NEW.class_id != OLD.class_id
         AND EXISTS (
             SELECT 1
             FROM enrollments AS e
             JOIN student_subject_results AS r
                 ON r.enrollment_id = e.id
             WHERE e.section_id = OLD.id
         )
        BEGIN
            SELECT RAISE(
                ABORT,
                'A section class cannot change after student results have been recorded.'
            );


        END;

        -- DOCUMENT MANAGEMENT

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER,
            teacher_id INTEGER,
            transport_staff_id INTEGER,

            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',

            original_filename TEXT NOT NULL,
            storage_key TEXT NOT NULL UNIQUE,

            mime_type TEXT NOT NULL,
            file_extension TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,

            uploaded_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            status TEXT NOT NULL DEFAULT 'active',
            archived_by INTEGER,
            archived_at TEXT,

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (teacher_id)
                REFERENCES teachers(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (transport_staff_id)
                REFERENCES transport_staff(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (uploaded_by)
                REFERENCES users(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (archived_by)
                REFERENCES users(id)
                ON DELETE RESTRICT,

            CHECK (
                (
                    student_id IS NOT NULL
                    AND teacher_id IS NULL
                    AND transport_staff_id IS NULL
                    AND category IN (
                        'birth_certificate',
                        'identity_document',
                        'enrollment_form',
                        'previous_school_record',
                        'transfer_certificate',
                        'academic_record',
                        'photograph',
                        'other'
                    )
                )
                OR
                (
                    student_id IS NULL
                    AND teacher_id IS NOT NULL
                    AND transport_staff_id IS NULL
                    AND category IN (
                        'identity_document',
                        'cv_resume',
                        'qualification_certificate',
                        'employment_contract',
                        'teaching_certificate',
                        'professional_license',
                        'photograph',
                        'other'
                    )
                )
                OR
                (
                    student_id IS NULL
                    AND teacher_id IS NULL
                    AND transport_staff_id IS NOT NULL
                    AND category IN (
                        'identity_document',
                        'cv_resume',
                        'employment_contract',
                        'drivers_license',
                        'safety_training_certificate',
                        'other'
                    )
                )
            ),

            CHECK (
                length(trim(title)) BETWEEN 1 AND 150
            ),

            CHECK (
                length(description) <= 1000
            ),

            CHECK (
                length(trim(original_filename)) BETWEEN 1 AND 255
                AND instr(original_filename, '/') = 0
                AND instr(original_filename, char(92)) = 0
                AND instr(original_filename, char(0)) = 0
            ),

            CHECK (
                length(trim(storage_key)) BETWEEN 1 AND 255
                AND substr(storage_key, 1, 1) <> '/'
                AND instr(storage_key, '..') = 0
                AND instr(storage_key, './') = 0
                AND storage_key <> '.'
                AND substr(storage_key, -2) <> '/.'
                AND instr(storage_key, char(92)) = 0
                AND instr(storage_key, char(58)) = 0
                AND instr(storage_key, char(0)) = 0
            ),

            CHECK (
                (
                    mime_type = 'application/pdf'
                    AND file_extension = '.pdf'
                )
                OR
                (
                    mime_type = 'image/jpeg'
                    AND file_extension IN ('.jpg', '.jpeg')
                )
                OR
                (
                    mime_type = 'image/png'
                    AND file_extension = '.png'
                )
            ),

            CHECK (
                size_bytes BETWEEN 1 AND 10485760
            ),

            CHECK (
                length(sha256) = 64
                AND sha256 NOT GLOB '*[^0-9a-f]*'
            ),

            CHECK (
                status IN ('active', 'archived')
            ),

            CHECK (
                (
                    status = 'active'
                    AND archived_by IS NULL
                    AND archived_at IS NULL
                )
                OR
                (
                    status = 'archived'
                    AND archived_by IS NOT NULL
                    AND archived_at IS NOT NULL
                    AND length(trim(archived_at)) > 0
                )
            )
        );

        -- DOCUMENT LOOKUP INDEXES

        CREATE INDEX IF NOT EXISTS
            idx_documents_student_status_created_at
        ON documents(student_id, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS
            idx_documents_teacher_status_created_at
        ON documents(teacher_id, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS
            idx_documents_transport_staff_status_created_at
        ON documents(transport_staff_id, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS
            idx_documents_category_status_created_at
        ON documents(category, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS
            idx_documents_sha256
        ON documents(sha256);

        CREATE INDEX IF NOT EXISTS
            idx_documents_uploaded_by_created_at
        ON documents(uploaded_by, created_at DESC);

        """)
