import tkinter as tk
from tkinter import ttk, messagebox

from services.dashboard_service import get_dashboard_summary
from services.permission_service import require_permission
from services.user_service import get_user
from services.student_service import get_student
from ui.students.student_form import StudentForm
from ui.students.student_list import StudentListFrame
from services.student_service import get_student

from ui.students.student_list import StudentListFrame
from ui.students.student_form import StudentForm
from ui.students.student_profile import StudentProfile
from services.teacher_service import get_teacher
from ui.teachers.teacher_form import TeacherForm
from ui.teachers.teacher_list import TeacherListFrame
from ui.teachers.teacher_profile import TeacherProfile

from services.vehicle_service import get_vehicle
from ui.transport.vehicle_form import VehicleForm
from ui.transport.vehicle_list import VehicleListFrame
from ui.transport.vehicle_profile import VehicleProfile

from services.transport_staff_service import get_transport_staff
from ui.transport.staff_form import TransportStaffForm
from ui.transport.staff_list import TransportStaffListFrame
from ui.transport.staff_profile import TransportStaffProfile
from ui.documents.document_list_frame import DocumentListFrame
from ui.settings.settings_frame import SettingsFrame

from services.transport_route_service import get_transport_route
from ui.transport.route_form import TransportRouteForm
from ui.transport.route_list import TransportRouteListFrame
from ui.transport.route_profile import TransportRouteProfile

from services.student_transport_assignment_service import (
    get_student_transport_assignment,
)
from ui.transport.assignment_form import StudentTransportAssignmentForm
from ui.transport.assignment_list import StudentTransportAssignmentListFrame
from ui.transport.assignment_profile import StudentTransportAssignmentProfile

from ui.transactions.fee_charge_form import FeeChargeForm
from ui.transactions.fee_charge_list import FeeChargeListFrame

from services.fee_charge_service import get_fee_charge
from services.fee_payment_service import get_fee_payment

from ui.transactions.fee_payment_form import FeePaymentForm
from ui.transactions.fee_payment_history import FeePaymentHistoryFrame
from ui.transactions.fee_receipt_window import FeeReceiptWindow

from ui.transactions.salary_slip_form import SalarySlipForm
from ui.transactions.salary_slip_list import SalarySlipListFrame

from ui.transactions.transaction_reports import TransactionReportsFrame

from services.academic_year_service import get_academic_year
from ui.academic_years.academic_year_form import AcademicYearForm
from ui.academic_years.academic_year_list import AcademicYearListFrame

from services.assessment_period_service import get_assessment_period
from ui.assessment_periods.assessment_period_form import AssessmentPeriodForm
from ui.assessment_periods.assessment_period_list import AssessmentPeriodListFrame

from services.class_service import get_class
from ui.classes.class_form import ClassForm
from ui.classes.class_list import ClassListFrame

from services.section_service import get_section
from ui.sections.section_form import SectionForm
from ui.sections.section_list import SectionListFrame

from services.enrollment_service import get_enrollment
from ui.enrollments.enrollment_form import EnrollmentForm
from ui.enrollments.enrollment_list import EnrollmentListFrame

from services.subject_service import get_subject
from ui.subjects.subject_form import SubjectForm
from ui.subjects.subject_list import SubjectListFrame

from services.teacher_subject_assignment_service import (
    get_teacher_subject_assignment,
)
from ui.teacher_subject_assignments.assignment_form import (
    TeacherSubjectAssignmentForm,
)
from ui.teacher_subject_assignments.assignment_list import (
    TeacherSubjectAssignmentListFrame,
)

from services.grading_scheme_service import (
    get_grading_scheme,
    get_grade_band,
)
from ui.grading_schemes.grading_scheme_form import GradingSchemeForm
from ui.grading_schemes.grading_scheme_list import GradingSchemeListFrame
from ui.grading_schemes.grade_band_form import GradeBandForm
from ui.grading_schemes.grade_band_list import GradeBandListFrame
from services.student_subject_result_service import (
    get_student_subject_result,
)
from ui.student_results.student_result_form import StudentResultForm
from ui.student_results.student_result_list import StudentResultListFrame
from ui.student_results.student_report_card import StudentReportCardFrame

from ui.users.user_list import UserListFrame
from ui.users.user_form import UserForm







class DashboardWindow(tk.Toplevel):

    def __init__(self, master, user, on_logout):
        super().__init__(master)

        self.user = user
        self.on_logout = on_logout

        self.title("School Management System - Dashboard")
        self.geometry("1150x720")
        self.minsize(950, 600)
        self.configure(bg="#F3F5F9")

        self.protocol("WM_DELETE_WINDOW", self.logout)

        self.setup_styles()
        self.create_header()
        self.create_sidebar()
        self.create_content()

        self.show_dashboard()

    # --------------------------------------------------
    # STYLES
    # --------------------------------------------------

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Card.TFrame",
            background="white",
            relief="flat"
        )

        style.configure(
            "CardTitle.TLabel",
            background="white",
            foreground="#64748B",
            font=("Segoe UI", 10)
        )

        style.configure(
            "CardValue.TLabel",
            background="white",
            foreground="#172033",
            font=("Segoe UI", 24, "bold")
        )

        style.configure(
            "Sidebar.TButton",
            font=("Segoe UI", 10),
            anchor="w",
            padding=(15, 11),
            background="#1E293B",
            foreground="white",
            borderwidth=0
        )

        style.map(
            "Sidebar.TButton",
            background=[("active", "#334155")],
            foreground=[("active", "white")]
        )

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    def create_header(self):
        header = tk.Frame(
            self,
            bg="#FFFFFF",
            height=65,
            highlightbackground="#E2E8F0",
            highlightthickness=1
        )
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SCHOOL MANAGEMENT SYSTEM",
            font=("Segoe UI", 15, "bold"),
            bg="white",
            fg="#172033"
        ).pack(side="left", padx=25)

        user_frame = tk.Frame(header, bg="white")
        user_frame.pack(side="right", padx=25)

        tk.Label(
            user_frame,
            text=self.user["full_name"],
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#172033"
        ).pack(side="left", padx=10)

        tk.Label(
            user_frame,
            text=self.user["role"].upper(),
            font=("Segoe UI", 8, "bold"),
            bg="#DBEAFE",
            fg="#1D4ED8",
            padx=8,
            pady=5
        ).pack(side="left")

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------

    def create_sidebar(self):
        sidebar = tk.Frame(
            self,
            bg="#1E293B",
            width=220
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Fixed sidebar heading.
        tk.Label(
            sidebar,
            text="MAIN MENU",
            font=("Segoe UI", 9, "bold"),
            bg="#1E293B",
            fg="#94A3B8"
        ).pack(anchor="w", padx=18, pady=(25, 12))

        # Scrollable navigation container.
        navigation_container = tk.Frame(
            sidebar,
            bg="#1E293B"
        )
        navigation_container.pack(fill="both", expand=True)

        navigation_canvas = tk.Canvas(
            navigation_container,
            bg="#1E293B",
            highlightthickness=0,
            borderwidth=0
        )

        # Invisible scrollbar: scrolling remains available through
        # the mouse wheel and touchpad without displaying a grey bar.
        navigation_canvas.configure(
            yscrollcommand=lambda first, last: None
        )

        navigation_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        navigation_frame = tk.Frame(
            navigation_canvas,
            bg="#1E293B"
        )

        navigation_window = navigation_canvas.create_window(
            (0, 0),
            window=navigation_frame,
            anchor="nw"
        )

        def update_scroll_region(event=None):
            navigation_canvas.configure(
                scrollregion=navigation_canvas.bbox("all")
            )

        def update_navigation_width(event):
            navigation_canvas.itemconfigure(
                navigation_window,
                width=event.width
            )

        navigation_frame.bind(
            "<Configure>",
            update_scroll_region
        )

        navigation_canvas.bind(
            "<Configure>",
            update_navigation_width
        )

        # Mouse-wheel scrolling (Windows, macOS and Linux).
        def on_mousewheel(event):
            widget = event.widget

            # Only scroll when the pointer is over the navigation area.
            while widget is not None:
                if widget == navigation_frame:
                    if event.num == 4:
                        navigation_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        navigation_canvas.yview_scroll(1, "units")
                    else:
                        direction = -1 if event.delta > 0 else 1
                        navigation_canvas.yview_scroll(direction, "units")
                    return "break"

                if widget == navigation_canvas:
                    break

                widget = getattr(widget, "master", None)

            return

        self.bind_all("<MouseWheel>", on_mousewheel)
        self.bind_all("<Button-4>", on_mousewheel)
        self.bind_all("<Button-5>", on_mousewheel)

        navigation = [
            ("Dashboard", self.show_dashboard, "dashboard.view"),

            ("Academic Years", self.show_academic_years, "academics.manage"),
            ("Assessment Periods", self.show_assessment_periods, "academics.manage"),
            ("Grading Schemes", self.show_grading_schemes, "academics.manage"),
            ("Student Results", self.show_student_results, "academics.manage"),

            ("Students", self.show_students, "students.manage"),
            ("Teachers", self.show_teachers, "teachers.manage"),
            ("Documents", self.show_documents, "documents.view"),
            ("User Management", self.show_users, "users.manage"),

            ("Transportation", self.show_vehicles, "transportation.manage"),
            ("Transport Staff", self.show_transport_staff, "transportation.manage"),
            ("Bus Routes", self.show_transport_routes, "transportation.manage"),
            ("Student Transportation", self.show_student_transport_assignments, "transportation.manage"),

            ("Classes", self.show_classes, "academics.manage"),
            ("Sections", self.show_sections, "academics.manage"),
            ("Subjects", self.show_subjects, "academics.manage"),
            ("Teacher–Subject Assignments", self.show_teacher_subject_assignments, "academics.manage"),
            ("Enrollments", self.show_enrollments, "academics.manage"),
            ("Attendance", lambda: self.show_placeholder("Attendance"), "academics.manage"),

            ("Fees", self.show_fee_charges, "fees.manage"),
            ("Salary Slips", self.show_salary_slips, "payroll.manage"),
            ("Examinations", lambda: self.show_placeholder("Examinations"), "academics.manage"),
            ("Reports", self.show_transaction_reports, "fees.reports.view"),
            ("Settings", self.show_settings, "system.manage"),
        ]

        for label, command, permission in navigation:
            try:
                require_permission(self.user["id"], permission)
            except PermissionError:
                continue

            ttk.Button(
                navigation_frame,
                text=label,
                style="Sidebar.TButton",
                command=command
            ).pack(fill="x", padx=8, pady=2)

        # Fixed logout button at the bottom.
        ttk.Button(
            sidebar,
            text="Logout",
            style="Sidebar.TButton",
            command=self.logout
        ).pack(fill="x", padx=8, pady=(5, 18))

    def _check_permission(self, permission):
        try:
            require_permission(self.user["id"], permission)
            return True
        except PermissionError as error:
            messagebox.showerror("Access denied", str(error))
            return False

    def show_protected_placeholder(self, module_name, permission):
        if not self._check_permission(permission):
            return

        self.show_placeholder(module_name)

    # --------------------------------------------------
    # MAIN CONTENT
    # --------------------------------------------------

    def create_content(self):
        self.content = tk.Frame(
            self,
            bg="#F3F5F9"
        )
        self.content.pack(
            side="left",
            fill="both",
            expand=True
        )

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    def show_dashboard(self):
        self.clear_content()

        tk.Label(
            self.content,
            text="Dashboard",
            font=("Segoe UI", 23, "bold"),
            bg="#F3F5F9",
            fg="#172033"
        ).pack(anchor="w", padx=30, pady=(28, 5))

        tk.Label(
            self.content,
            text=f"Welcome back, {self.user['full_name']}.",
            font=("Segoe UI", 11),
            bg="#F3F5F9",
            fg="#64748B"
        ).pack(anchor="w", padx=30, pady=(0, 25))

        try:
            summary = get_dashboard_summary()
        except Exception as error:
            messagebox.showerror(
                "Dashboard Error",
                f"Could not load dashboard statistics:\n{error}",
                parent=self
            )
            return

        cards_frame = tk.Frame(
            self.content,
            bg="#F3F5F9"
        )
        cards_frame.pack(fill="x", padx=25)

        cards = [
            ("Total Students", summary["students"]),
            ("Total Classes", summary["classes"]),
            ("Enrollments", summary["enrollments"]),
            ("User Accounts", summary["users"])
        ]

        for index, (title, value) in enumerate(cards):
            card = ttk.Frame(
                cards_frame,
                style="Card.TFrame",
                padding=20
            )

            card.grid(
                row=0,
                column=index,
                padx=7,
                pady=5,
                sticky="nsew"
            )

            ttk.Label(
                card,
                text=title,
                style="CardTitle.TLabel"
            ).pack(anchor="w")

            ttk.Label(
                card,
                text=str(value),
                style="CardValue.TLabel"
            ).pack(anchor="w", pady=(12, 0))

            cards_frame.columnconfigure(
                index,
                weight=1
            )

        # Recent activity section

        activity_frame = tk.Frame(
            self.content,
            bg="white",
            highlightbackground="#E2E8F0",
            highlightthickness=1
        )

        activity_frame.pack(
            fill="both",
            expand=True,
            padx=32,
            pady=25
        )

        tk.Label(
            activity_frame,
            text="Recent Activities",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#172033"
        ).pack(anchor="w", padx=22, pady=(20, 10))

        tk.Label(
            activity_frame,
            text="Activity tracking will be available in a future stage.",
            font=("Segoe UI", 10),
            bg="white",
            fg="#64748B"
        ).pack(anchor="w", padx=22, pady=10)

    # --------------------------------------------------
    # ACADEMIC YEAR MANAGEMENT
    # --------------------------------------------------

    def show_academic_years(self):
        self.clear_content()

        academic_year_page = AcademicYearListFrame(
            self.content,
            on_create=self.show_academic_year_form,
            on_edit=self.show_academic_year_form,
            user=self.user,
        )

        academic_year_page.pack(
            fill="both",
            expand=True
        )

    def show_academic_year_form(self, academic_year_id=None):
        if not self._check_permission("academics.configure"):
            return

        self.clear_content()
        academic_year = None

        if academic_year_id is not None:
            academic_year = get_academic_year(
                academic_year_id,
                actor_user_id=self.user["id"]
            )

            if not academic_year:
                messagebox.showerror(
                    "Academic Year Not Found",
                    "The selected academic year could not be found.",
                    parent=self
                )
                self.show_academic_years()
                return

        form = AcademicYearForm(
            self.content,
            on_back=self.show_academic_years,
            on_saved=self.show_academic_years,
            academic_year=academic_year,
            user=self.user
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # ASSESSMENT PERIOD MANAGEMENT
    # --------------------------------------------------

    def show_assessment_periods(self):
        self.clear_content()

        assessment_period_page = AssessmentPeriodListFrame(
            self.content,
            on_create=self.show_assessment_period_form,
            on_edit=self.show_assessment_period_form,
            user=self.user,
        )

        assessment_period_page.pack(
            fill="both",
            expand=True,
        )

    def show_assessment_period_form(self, assessment_period_id=None):
        self.clear_content()
        assessment_period = None

        if assessment_period_id is not None:
            assessment_period = get_assessment_period(
                assessment_period_id,
                actor_user_id=self.user["id"],
            )

            if not assessment_period:
                messagebox.showerror(
                    "Assessment Period Not Found",
                    "The selected assessment period could not be found.",
                    parent=self,
                )
                self.show_assessment_periods()
                return

        form = AssessmentPeriodForm(
            self.content,
            on_back=self.show_assessment_periods,
            on_saved=self.show_assessment_periods,
            assessment_period=assessment_period,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True,
        )

    # --------------------------------------------------
    # GRADING SCHEME MANAGEMENT
    # --------------------------------------------------

    def show_grading_schemes(self):
        self.clear_content()

        grading_scheme_page = GradingSchemeListFrame(
            self.content,
            on_create=self.show_grading_scheme_form,
            on_edit=self.show_grading_scheme_form,
            on_manage_bands=self.show_grade_bands,
            user=self.user,
        )

        grading_scheme_page.pack(
            fill="both",
            expand=True,
        )

    def show_grading_scheme_form(self, scheme_id=None):
        self.clear_content()
        grading_scheme = None

        if scheme_id is not None:
            grading_scheme = get_grading_scheme(scheme_id, actor_user_id=self.user["id"])

            if not grading_scheme:
                messagebox.showerror(
                    "Grading Scheme Not Found",
                    "The selected grading scheme could not be found.",
                    parent=self,
                )
                self.show_grading_schemes()
                return

        form = GradingSchemeForm(
            self.content,
            on_back=self.show_grading_schemes,
            on_saved=self.show_grading_schemes,
            grading_scheme=grading_scheme,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True,
        )

    def show_grade_bands(self, scheme_id):
        self.clear_content()

        grading_scheme = get_grading_scheme(scheme_id, actor_user_id=self.user["id"])

        if not grading_scheme:
            messagebox.showerror(
                "Grading Scheme Not Found",
                "The selected grading scheme could not be found.",
                parent=self,
            )
            self.show_grading_schemes()
            return

        grade_band_page = GradeBandListFrame(
            self.content,
            grading_scheme=grading_scheme,
            on_add=lambda: self.show_grade_band_form(scheme_id),
            on_edit=lambda band_id: self.show_grade_band_form(
                scheme_id,
                band_id,
            ),
            on_back=self.show_grading_schemes,
            on_scheme_changed=self.show_grading_schemes,
            user=self.user,
        )

        grade_band_page.pack(
            fill="both",
            expand=True,
        )

    def show_grade_band_form(self, scheme_id, band_id=None):
        self.clear_content()

        grading_scheme = get_grading_scheme(scheme_id, actor_user_id=self.user["id"])

        if not grading_scheme:
            messagebox.showerror(
                "Grading Scheme Not Found",
                "The selected grading scheme could not be found.",
                parent=self,
            )
            self.show_grading_schemes()
            return

        grade_band = None

        if band_id is not None:
            grade_band = get_grade_band(band_id, actor_user_id=self.user["id"])

            if (
                not grade_band
                or grade_band["grading_scheme_id"] != scheme_id
            ):
                messagebox.showerror(
                    "Grade Band Not Found",
                    "The selected grade band could not be found "
                    "in this grading scheme.",
                    parent=self,
                )
                self.show_grade_bands(scheme_id)
                return

        form = GradeBandForm(
            self.content,
            grading_scheme=grading_scheme,
            on_back=lambda: self.show_grade_bands(scheme_id),
            on_saved=lambda: self.show_grade_bands(scheme_id),
            grade_band=grade_band,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True,
        )

    # --------------------------------------------------
    # --------------------------------------------------
    # STUDENT RESULTS AND REPORT CARDS
    # --------------------------------------------------

    def show_student_results(self):
        self.clear_content()

        result_page = StudentResultListFrame(
            self.content,
            on_create=self.show_student_result_form,
            on_edit=self.show_student_result_form,
            on_view_report_card=self.show_student_report_card,
            user=self.user,
        )

        result_page.pack(
            fill="both",
            expand=True,
        )

    def show_student_result_form(self, result=None):
        self.clear_content()

        existing_result = None

        if result is not None:
            result_id = (
                result["id"] if isinstance(result, dict) else result
            )

            existing_result = get_student_subject_result(result_id)

            if not existing_result:
                messagebox.showerror(
                    "Student Result Not Found",
                    "The selected student result could not be found.",
                    parent=self,
                )
                self.show_student_results()
                return

        form = StudentResultForm(
            self.content,
            on_back=self.show_student_results,
            on_saved=self.show_student_results,
            result=existing_result,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True,
        )

    def show_student_report_card(
        self,
        enrollment_id,
        assessment_period_id,
    ):
        self.clear_content()

        try:
            report_page = StudentReportCardFrame(
                self.content,
                enrollment_id=enrollment_id,
                assessment_period_id=assessment_period_id,
                on_back=self.show_student_results,
            )
        except Exception as error:
            messagebox.showerror(
                "Report Card Error",
                str(error),
                parent=self,
            )
            self.show_student_results()
            return

        report_page.pack(
            fill="both",
            expand=True,
        )

    # CLASS MANAGEMENT
    # --------------------------------------------------

    def show_classes(self):
        self.clear_content()

        class_page = ClassListFrame(
            self.content,
            on_create=self.show_class_form,
            on_edit=self.show_class_form,
            user=self.user,
        )

        class_page.pack(
            fill="both",
            expand=True
        )

    def show_class_form(self, class_id=None):
        self.clear_content()
        school_class = None

        if class_id is not None:
            school_class = get_class(class_id, actor_user_id=self.user["id"])

            if not school_class:
                messagebox.showerror(
                    "Class Not Found",
                    "The selected class record could not be found.",
                    parent=self
                )
                self.show_classes()
                return

        form = ClassForm(
            self.content,
            on_back=self.show_classes,
            on_saved=self.show_classes,
            school_class=school_class,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # SECTION MANAGEMENT
    # --------------------------------------------------

    def show_sections(self):
        self.clear_content()

        section_page = SectionListFrame(
            self.content,
            on_create=self.show_section_form,
            on_edit=self.show_section_form,
            user=self.user,
        )

        section_page.pack(
            fill="both",
            expand=True
        )

    def show_section_form(self, section_id=None):
        self.clear_content()
        section = None

        if section_id is not None:
            section = get_section(section_id, actor_user_id=self.user["id"])

            if not section:
                messagebox.showerror(
                    "Section Not Found",
                    "The selected section record could not be found.",
                    parent=self
                )
                self.show_sections()
                return

        form = SectionForm(
            self.content,
            on_back=self.show_sections,
            on_saved=self.show_sections,
            section=section,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # SUBJECT MANAGEMENT
    # --------------------------------------------------

    def show_subjects(self):
        self.clear_content()

        subject_page = SubjectListFrame(
            self.content,
            on_create=self.show_subject_form,
            on_edit=self.show_subject_form,
            user=self.user,
        )

        subject_page.pack(
            fill="both",
            expand=True
        )

    def show_subject_form(self, subject_id=None):
        self.clear_content()
        subject = None

        if subject_id is not None:
            subject = get_subject(subject_id, actor_user_id=self.user["id"])

            if not subject:
                messagebox.showerror(
                    "Subject Not Found",
                    "The selected subject could not be found.",
                    parent=self
                )
                self.show_subjects()
                return

        form = SubjectForm(
            self.content,
            on_back=self.show_subjects,
            on_saved=self.show_subjects,
            subject=subject,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TEACHER–SUBJECT ASSIGNMENT MANAGEMENT
    # --------------------------------------------------

    def show_teacher_subject_assignments(self):
        self.clear_content()

        assignment_page = TeacherSubjectAssignmentListFrame(
            self.content,
            on_create=self.show_teacher_subject_assignment_form,
            on_reassign=lambda assignment_id: (
                self.show_teacher_subject_assignment_form(
                    assignment_id=assignment_id,
                    reassign=True,
                )
            ),
            user=self.user,
        )

        assignment_page.pack(
            fill="both",
            expand=True,
        )

    def show_teacher_subject_assignment_form(
        self,
        assignment_id=None,
        reassign=False,
    ):
        self.clear_content()
        assignment = None

        if assignment_id is not None:
            assignment = get_teacher_subject_assignment(
                assignment_id,
                actor_user_id=self.user["id"],
            )

            if not assignment:
                messagebox.showerror(
                    "Assignment Not Found",
                    "The selected assignment could not be found.",
                    parent=self,
                )
                self.show_teacher_subject_assignments()
                return

        form = TeacherSubjectAssignmentForm(
            self.content,
            on_back=self.show_teacher_subject_assignments,
            on_saved=self.show_teacher_subject_assignments,
            assignment=assignment,
            reassign=reassign,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True,
        )

    # --------------------------------------------------
    # STUDENT ENROLLMENT MANAGEMENT
    # --------------------------------------------------

    def show_enrollments(self):
        self.clear_content()

        enrollment_page = EnrollmentListFrame(
            self.content,
            on_create=self.show_enrollment_form,
            on_edit=self.show_enrollment_form,
            on_promote=self.show_enrollment_promotion,
            user=self.user,
        )

        enrollment_page.pack(
            fill="both",
            expand=True
        )

    def show_enrollment_form(
        self,
        enrollment_id=None,
        promote_student_id=None,
        initial_class_id=None,
        initial_section_id=None,
    ):
        self.clear_content()
        enrollment = None

        if enrollment_id is not None:
            enrollment = get_enrollment(
                enrollment_id, actor_user_id=self.user["id"]
            )

            if not enrollment:
                messagebox.showerror(
                    "Enrollment Not Found",
                    "The selected enrollment record could not be found.",
                    parent=self
                )
                self.show_enrollments()
                return

        form = EnrollmentForm(
            self.content,
            user=self.user,
            on_back=self.show_enrollments,
            on_saved=self.show_enrollments,
            enrollment=enrollment,
            promote_student_id=promote_student_id,
            initial_class_id=initial_class_id,
            initial_section_id=initial_section_id,
        )

        form.pack(
            fill="both",
            expand=True
        )

    def show_enrollment_promotion(self, enrollment_id):
        source_enrollment = get_enrollment(
            enrollment_id, actor_user_id=self.user["id"]
        )

        if not source_enrollment:
            messagebox.showerror(
                "Enrollment Not Found",
                "The selected enrollment record could not be found.",
                parent=self
            )
            self.show_enrollments()
            return

        self.show_enrollment_form(
            promote_student_id=source_enrollment["student_id"],
            initial_class_id=source_enrollment["class_id"],
            initial_section_id=source_enrollment["section_id"],
        )

    # --------------------------------------------------
    # STUDENT MANAGEMENT
    # --------------------------------------------------

    def show_documents(self):
        if not self._check_permission("documents.view"):
            return

        self.clear_content()

        page = DocumentListFrame(
            self.content,
            user=self.user,
        )

        page.pack(
            fill="both",
            expand=True,
        )

    def show_settings(self):
        if not self._check_permission("system.manage"):
            return

        self.clear_content()

        page = SettingsFrame(
            self.content,
            user=self.user,
            on_restored=self._handle_restore_completed,
        )

        page.pack(
            fill="both",
            expand=True,
        )

    def _handle_restore_completed(self):
        # A restore may replace user accounts and permissions.
        # Destroy the current dashboard and require a fresh login.
        self.destroy()
        self.on_logout()

    def show_students(self):
        self.clear_content()
        student_page = StudentListFrame(
            self.content,
            user=self.user,
            on_register=self.show_student_form,
            on_profile=self.show_student_profile,
            on_edit=self.show_student_form
        )
        student_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # STUDENT REGISTRATION / EDITING
    # --------------------------------------------------

    def show_student_form(self, student_id=None):
        self.clear_content()
        student = None

        if student_id is not None:
            student = get_student(
                student_id, actor_user_id=self.user["id"]
            )
            if not student:
                messagebox.showerror(
                    "Student Not Found",
                    "The selected student record could not be found.",
                    parent=self
                )
                self.show_students()
                return

        form = StudentForm(
            self.content,
            user=self.user,
            on_back=self.show_students,
            on_saved=self.show_students,
            student=student
        )
        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # STUDENT PROFILE
    # --------------------------------------------------

    def show_student_profile(self, student_id):
        self.clear_content()

        student = get_student(
            student_id,
            actor_user_id=self.user["id"],
        )

        if not student:
            messagebox.showerror(
                "Student Not Found",
                "The selected student record could not be found.",
                parent=self,
            )
            self.show_students()
            return

        profile = StudentProfile(
            self.content,
            student=student,
            on_back=self.show_students,
            on_edit=lambda: self.show_student_form(student_id),
            user=self.user,
        )

        profile.pack(
            fill="both",
            expand=True,
        )

    # --------------------------------------------------
    # TEACHER / EMPLOYEE MANAGEMENT
    # --------------------------------------------------

    def show_teachers(self):
        self.clear_content()

        teacher_page = TeacherListFrame(
            self.content,
            on_register=self.show_teacher_form,
            on_profile=self.show_teacher_profile,
            on_edit=self.show_teacher_form,
            user=self.user,
        )

        teacher_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TEACHER REGISTRATION / EDITING
    # --------------------------------------------------

    def show_teacher_form(self, teacher_id=None):
        self.clear_content()
        teacher = None

        if teacher_id is not None:
            teacher = get_teacher(
                teacher_id,
                actor_user_id=self.user["id"],
            )

            if not teacher:
                messagebox.showerror(
                    "Teacher Not Found",
                    "The selected employee record could not be found.",
                    parent=self
                )
                self.show_teachers()
                return

        form = TeacherForm(
            self.content,
            on_back=self.show_teachers,
            on_saved=self.show_teachers,
            teacher=teacher,
            user=self.user,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TEACHER PROFILE
    # --------------------------------------------------

    def show_teacher_profile(self, teacher_id):
        self.clear_content()

        teacher = get_teacher(
            teacher_id,
            actor_user_id=self.user["id"],
        )

        if not teacher:
            messagebox.showerror(
                "Teacher Not Found",
                "The selected employee record could not be found.",
                parent=self
            )
            self.show_teachers()
            return

        profile = TeacherProfile(
            self.content,
            teacher=teacher,
            on_back=self.show_teachers,
            on_edit=lambda: self.show_teacher_form(teacher_id),
            user=self.user,
        )

        profile.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # USER MANAGEMENT
    # --------------------------------------------------

    def show_users(self):
        if not self._check_permission("users.manage"):
            return

        self.clear_content()

        page = UserListFrame(
            self.content,
            on_create=self.show_user_form,
            on_edit=self.show_user_form,
            user=self.user,
        )

        page.pack(fill="both", expand=True)

    def show_user_form(self, user_id=None):
        if not self._check_permission("users.manage"):
            return

        account = None

        if user_id is not None:
            try:
                account = get_user(
                    user_id,
                    actor_user_id=self.user["id"],
                )
            except (ValueError, PermissionError) as error:
                messagebox.showerror(
                    "User Account Error",
                    str(error),
                    parent=self,
                )
                self.show_users()
                return

            if not account:
                messagebox.showerror(
                    "User Not Found",
                    "The selected account could not be found.",
                    parent=self,
                )
                self.show_users()
                return

        self.clear_content()

        form = UserForm(
            self.content,
            on_back=self.show_users,
            on_saved=self.show_users,
            account=account,
            user=self.user,
        )

        form.pack(fill="both", expand=True)

    # --------------------------------------------------
    # TRANSPORTATION / VEHICLE MANAGEMENT
    # --------------------------------------------------

    def show_vehicles(self):
        self.clear_content()

        vehicle_page = VehicleListFrame(
            self.content,
            on_register=self.show_vehicle_form,
            on_profile=self.show_vehicle_profile,
            on_edit=self.show_vehicle_form,
        )

        vehicle_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # VEHICLE REGISTRATION / EDITING
    # --------------------------------------------------

    def show_vehicle_form(self, vehicle_id=None):
        self.clear_content()
        vehicle = None

        if vehicle_id is not None:
            vehicle = get_vehicle(vehicle_id)

            if not vehicle:
                messagebox.showerror(
                    "Vehicle Not Found",
                    "The selected vehicle record could not be found.",
                    parent=self
                )
                self.show_vehicles()
                return

        form = VehicleForm(
            self.content,
            on_back=self.show_vehicles,
            on_saved=self.show_vehicles,
            vehicle=vehicle
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # VEHICLE PROFILE
    # --------------------------------------------------

    def show_vehicle_profile(self, vehicle_id):
        self.clear_content()

        vehicle = get_vehicle(vehicle_id)

        if not vehicle:
            messagebox.showerror(
                "Vehicle Not Found",
                "The selected vehicle record could not be found.",
                parent=self
            )
            self.show_vehicles()
            return

        profile = VehicleProfile(
            self.content,
            vehicle=vehicle,
            on_back=self.show_vehicles,
            on_edit=lambda: self.show_vehicle_form(vehicle_id)
        )

        profile.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TRANSPORT STAFF MANAGEMENT
    # --------------------------------------------------

    def show_transport_staff(self):
        self.clear_content()

        staff_page = TransportStaffListFrame(
            self.content,
            on_register=self.show_transport_staff_form,
            on_profile=self.show_transport_staff_profile,
            on_edit=self.show_transport_staff_form,
        )

        staff_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TRANSPORT STAFF REGISTRATION / EDITING
    # --------------------------------------------------

    def show_transport_staff_form(self, staff_id=None):
        self.clear_content()
        staff = None

        if staff_id is not None:
            staff = get_transport_staff(staff_id)

            if not staff:
                messagebox.showerror(
                    "Transport Staff Not Found",
                    "The selected transport staff record could not be found.",
                    parent=self
                )
                self.show_transport_staff()
                return

        form = TransportStaffForm(
            self.content,
            on_back=self.show_transport_staff,
            on_saved=self.show_transport_staff,
            staff=staff
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TRANSPORT STAFF PROFILE
    # --------------------------------------------------

    def show_transport_staff_profile(self, staff_id):
        self.clear_content()

        staff = get_transport_staff(staff_id)

        if not staff:
            messagebox.showerror(
                "Transport Staff Not Found",
                "The selected transport staff record could not be found.",
                parent=self
            )
            self.show_transport_staff()
            return

        profile = TransportStaffProfile(
            self.content,
            staff=staff,
            on_back=self.show_transport_staff,
            on_edit=lambda: self.show_transport_staff_form(staff_id),
            user=self.user,
        )

        profile.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # BUS ROUTE MANAGEMENT
    # --------------------------------------------------

    def show_transport_routes(self):
        self.clear_content()

        route_page = TransportRouteListFrame(
            self.content,
            on_register=self.show_transport_route_form,
            on_profile=self.show_transport_route_profile,
            on_edit=self.show_transport_route_form,
        )

        route_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # ROUTE REGISTRATION / EDITING
    # --------------------------------------------------

    def show_transport_route_form(self, route_id=None):
        self.clear_content()
        route = None

        if route_id is not None:
            route = get_transport_route(route_id)

            if not route:
                messagebox.showerror(
                    "Route Not Found",
                    "The selected bus route could not be found.",
                    parent=self
                )
                self.show_transport_routes()
                return

        form = TransportRouteForm(
            self.content,
            on_back=self.show_transport_routes,
            on_saved=self.show_transport_routes,
            route=route
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # ROUTE PROFILE AND STOP MANAGEMENT
    # --------------------------------------------------

    def show_transport_route_profile(self, route_id):
        self.clear_content()

        route = get_transport_route(route_id)

        if not route:
            messagebox.showerror(
                "Route Not Found",
                "The selected bus route could not be found.",
                parent=self
            )
            self.show_transport_routes()
            return

        profile = TransportRouteProfile(
            self.content,
            route=route,
            on_back=self.show_transport_routes,
            on_edit=lambda: self.show_transport_route_form(route_id)
        )

        profile.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # STUDENT TRANSPORTATION ASSIGNMENTS
    # --------------------------------------------------

    def show_student_transport_assignments(self):
        self.clear_content()

        assignment_page = StudentTransportAssignmentListFrame(
            self.content,
            on_register=self.show_student_transport_assignment_form,
            on_profile=self.show_student_transport_assignment_profile,
            on_edit=self.show_student_transport_assignment_form,
        )

        assignment_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # ASSIGNMENT REGISTRATION / EDITING
    # --------------------------------------------------

    def show_student_transport_assignment_form(self, assignment_id=None):
        self.clear_content()
        assignment = None

        if assignment_id is not None:
            assignment = get_student_transport_assignment(assignment_id)

            if not assignment:
                messagebox.showerror(
                    "Assignment Not Found",
                    "The selected transportation assignment could not be found.",
                    parent=self
                )
                self.show_student_transport_assignments()
                return

        form = StudentTransportAssignmentForm(
            self.content,
            user=self.user,
            on_back=self.show_student_transport_assignments,
            on_saved=self.show_student_transport_assignments,
            assignment=assignment
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # ASSIGNMENT PROFILE AND HISTORY
    # --------------------------------------------------

    def show_student_transport_assignment_profile(self, assignment_id):
        self.clear_content()

        assignment = get_student_transport_assignment(assignment_id)

        if not assignment:
            messagebox.showerror(
                "Assignment Not Found",
                "The selected transportation assignment could not be found.",
                parent=self
            )
            self.show_student_transport_assignments()
            return

        profile = StudentTransportAssignmentProfile(
            self.content,
            assignment=assignment,
            on_back=self.show_student_transport_assignments,
            on_edit=lambda: self.show_student_transport_assignment_form(
                assignment_id
            )
        )

        profile.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # FEE CHARGE MANAGEMENT
    # --------------------------------------------------

    def show_fee_charges(self):
        self.clear_content()

        fee_page = FeeChargeListFrame(
            self.content,
            on_create=self.show_fee_charge_form,
            on_record_payment=self.show_fee_payment_form,
            on_view_payments=self.show_fee_payment_history,
            user=self.user,
        )

        fee_page.pack(
            fill="both",
            expand=True
        )

    def show_fee_charge_form(self):
        self.clear_content()

        form = FeeChargeForm(
            self.content,
            user=self.user,
            on_back=self.show_fee_charges,
            on_saved=self.show_fee_charges,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # FEE PAYMENT
    # --------------------------------------------------

    def show_fee_payment_form(self, charge_id):
        charge = get_fee_charge(
            charge_id,
            actor_user_id=self.user["id"],
        )

        if not charge:
            messagebox.showerror(
                "Fee Charge Not Found",
                "The selected fee charge could not be found.",
                parent=self
            )
            self.show_fee_charges()
            return

        if charge["status"] != "open" or charge["balance_minor"] <= 0:
            messagebox.showwarning(
                "Payment Not Available",
                "This fee charge has no outstanding balance.",
                parent=self
            )
            self.show_fee_charges()
            return

        self.clear_content()

        form = FeePaymentForm(
            self.content,
            charge=charge,
            user=self.user,
            on_back=self.show_fee_charges,
            on_saved=self.show_fee_payment_receipt,
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # PAYMENT RECEIPT
    # --------------------------------------------------

    def show_fee_payment_receipt(self, payment_id):
        payment = get_fee_payment(
            payment_id, actor_user_id=self.user["id"]
        )

        if not payment:
            messagebox.showerror(
                "Receipt Not Found",
                "The payment was recorded, but its receipt could not be loaded.",
                parent=self
            )
            self.show_fee_charges()
            return

        self.show_fee_charges()

        FeeReceiptWindow(
            self,
            payment
        )

    # --------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------

    def show_fee_payment_history(self):
        self.clear_content()

        history_page = FeePaymentHistoryFrame(
            self.content,
            user=self.user,
            on_back=self.show_fee_charges,
        )

        history_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # SALARY SLIP MANAGEMENT
    # --------------------------------------------------

    def show_salary_slips(self):
        if not self._check_permission("payroll.manage"):
            return
        self.clear_content()

        salary_page = SalarySlipListFrame(
            self.content,
            on_create=self.show_salary_slip_form,
            on_back=self.show_dashboard,
            user=self.user,
        )

        salary_page.pack(
            fill="both",
            expand=True
        )

    def show_salary_slip_form(self):
        if not self._check_permission("payroll.manage"):
            return
        self.clear_content()

        form = SalarySlipForm(
            self.content,
            user=self.user,
            on_back=self.show_salary_slips,
            on_saved=lambda slip_id: self.show_salary_slips(),
        )

        form.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # TRANSACTION REPORTS
    # --------------------------------------------------

    def show_transaction_reports(self):
        if not self._check_permission("fees.reports.view"):
            return
        self.clear_content()

        reports_page = TransactionReportsFrame(
            self.content,
            on_back=self.show_dashboard,
            user=self.user,
        )

        reports_page.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------
    # PLACEHOLDER MODULES
    # --------------------------------------------------

    def show_placeholder(self, module_name):
        self.clear_content()

        tk.Label(
            self.content,
            text=module_name,
            font=("Segoe UI", 23, "bold"),
            bg="#F3F5F9",
            fg="#172033"
        ).pack(anchor="w", padx=30, pady=(30, 10))

        tk.Label(
            self.content,
            text=f"The {module_name} module has not been implemented yet.",
            font=("Segoe UI", 11),
            bg="#F3F5F9",
            fg="#64748B"
        ).pack(anchor="w", padx=30)

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------

    def logout(self):
        if messagebox.askyesno(
            "Logout",
            "Are you sure you want to log out?",
            parent=self
        ):
            self.destroy()
            self.on_logout()
