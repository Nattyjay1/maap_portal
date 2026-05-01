from pathlib import Path
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File

from academics.models import (
    Department,
    FacultyProfile,
    StudentProfile,
    Subject,
    ClassSection,
    Enrollment,
    Grade,
    AttendanceSummary,
)

from evaluations.models import FacultyEvaluation
from formsrepo.models import AcademicForm


User = get_user_model()


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def upsert_user(username, password, role, first_name, last_name, email=None, is_staff=False):
    user, created = User.objects.get_or_create(username=username)
    user.role = role
    user.first_name = first_name
    user.last_name = last_name
    user.email = email or f"{username}@maap.edu.ph"
    user.is_active = True
    user.is_staff = is_staff
    user.set_password(password)
    user.save()
    return user


def upsert_department(code, name):
    department, created = Department.objects.get_or_create(code=code)
    department.name = name
    department.save()
    return department


def upsert_faculty_profile(user, department, employee_id, designation):
    profile, created = FacultyProfile.objects.get_or_create(user=user)
    profile.department = department
    profile.employee_id = employee_id
    profile.designation = designation
    profile.save()
    return profile


def upsert_student_profile(user, department, student_number, year_level, section):
    profile, created = StudentProfile.objects.get_or_create(user=user)
    profile.department = department
    profile.student_number = student_number
    profile.year_level = year_level
    profile.section = section
    profile.save()
    return profile


def upsert_subject(code, title, units, department):
    subject, created = Subject.objects.get_or_create(code=code)
    subject.title = title
    subject.units = units
    subject.department = department
    subject.save()
    return subject


def upsert_class_section(subject, faculty, section_name, term, school_year, schedule, room):
    class_section, created = ClassSection.objects.get_or_create(
        subject=subject,
        section_name=section_name,
        term=term,
        school_year=school_year,
    )
    class_section.faculty = faculty
    class_section.schedule = schedule
    class_section.room = room
    class_section.save()
    return class_section


def enroll_student(student, class_section):
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        class_section=class_section,
    )
    return enrollment


def create_grade(enrollment, quiz, activity, exam, lab, attendance_score):
    grade, created = Grade.objects.get_or_create(enrollment=enrollment)
    grade.quiz_total = Decimal(str(quiz))
    grade.activity_total = Decimal(str(activity))
    grade.exam_total = Decimal(str(exam))
    grade.lab_total = Decimal(str(lab))
    grade.attendance_score = Decimal(str(attendance_score))
    grade.save()
    return grade


def create_attendance(enrollment, present, absent, late):
    attendance, created = AttendanceSummary.objects.get_or_create(enrollment=enrollment)
    attendance.present_count = present
    attendance.absent_count = absent
    attendance.late_count = late
    attendance.save()
    return attendance


def create_evaluation(faculty, evaluator_type, score, remarks, term, school_year):
    FacultyEvaluation.objects.get_or_create(
        faculty=faculty,
        evaluator_type=evaluator_type,
        evaluation_score=Decimal(str(score)),
        term=term,
        school_year=school_year,
        remarks=remarks,
    )


def create_demo_form(title, description, category, filename, uploaded_by):
    demo_dir = Path(settings.MEDIA_ROOT) / "demo_form_sources"
    demo_dir.mkdir(parents=True, exist_ok=True)

    source_file = demo_dir / filename

    if not source_file.exists():
        source_file.write_text(
            f"{title}\n\n{description}\n\nThis is a demo form file for the prototype system.",
            encoding="utf-8"
        )

    academic_form, created = AcademicForm.objects.get_or_create(
        title=title,
        defaults={
            "description": description,
            "category": category,
            "uploaded_by": uploaded_by,
            "is_active": True,
        }
    )

    academic_form.description = description
    academic_form.category = category
    academic_form.uploaded_by = uploaded_by
    academic_form.is_active = True

    if not academic_form.file:
        with open(source_file, "rb") as f:
            academic_form.file.save(filename, File(f), save=False)

    academic_form.save()
    return academic_form


# ---------------------------------------------------------
# Core setup
# ---------------------------------------------------------

print("Creating April 26 complete demo database...")

term = "1st Semester"
school_year = "2025-2026"


# ---------------------------------------------------------
# Departments
# ---------------------------------------------------------

bsmt = upsert_department("BSMT", "Bachelor of Science in Marine Transportation")
bsme = upsert_department("BSME", "Bachelor of Science in Marine Engineering")
ge = upsert_department("GE", "General Education")


# ---------------------------------------------------------
# Users
# ---------------------------------------------------------

admin_user = upsert_user("admin1", "admin123", "admin", "Portal", "Administrator")

faculty_users = {
    "nav1": upsert_user("faculty_nav1", "faculty123", "faculty", "Ramon", "Dela Cruz"),
    "nav2": upsert_user("faculty_nav2", "faculty123", "faculty", "Julius", "Mendoza"),
    "eng1": upsert_user("faculty_eng1", "faculty123", "faculty", "Michael", "Reyes"),
    "eng2": upsert_user("faculty_eng2", "faculty123", "faculty", "Paolo", "Castillo"),
    "ge1": upsert_user("faculty_ge1", "faculty123", "faculty", "Maria Teresa", "Santos"),
    "ge2": upsert_user("faculty_ge2", "faculty123", "faculty", "Anthony", "Garcia"),
}

faculty_profiles = {
    "nav1": upsert_faculty_profile(faculty_users["nav1"], bsmt, "FAC-001", "Instructor I"),
    "nav2": upsert_faculty_profile(faculty_users["nav2"], bsmt, "FAC-002", "Instructor II"),
    "eng1": upsert_faculty_profile(faculty_users["eng1"], bsme, "FAC-003", "Instructor I"),
    "eng2": upsert_faculty_profile(faculty_users["eng2"], bsme, "FAC-004", "Instructor II"),
    "ge1": upsert_faculty_profile(faculty_users["ge1"], ge, "FAC-005", "Assistant Professor"),
    "ge2": upsert_faculty_profile(faculty_users["ge2"], ge, "FAC-006", "Instructor I"),
}


# ---------------------------------------------------------
# Students: 30 total
# 15 BSMT, 15 BSME
# ---------------------------------------------------------

bsmt_names = [
    ("John Mark", "Santos"),
    ("Carl Vincent", "Ramos"),
    ("Joshua", "Perez"),
    ("Miguel", "Torres"),
    ("Adrian", "Cruz"),
    ("Noel", "Garcia"),
    ("Kevin", "Bautista"),
    ("Lester", "Medina"),
    ("Francis", "Lim"),
    ("Patrick", "Dominguez"),
    ("Rafael", "Castro"),
    ("Daniel", "Villanueva"),
    ("Sean", "Navarro"),
    ("Gabriel", "Morales"),
    ("Nathan", "Aquino"),
]

bsme_names = [
    ("Ryan", "Navarro"),
    ("Ethan", "Villanueva"),
    ("Marco", "Alvarez"),
    ("Neil", "Fernandez"),
    ("Christian", "Lopez"),
    ("Jerome", "Aquino"),
    ("Alden", "Flores"),
    ("Kenneth", "Padilla"),
    ("Mark Joseph", "Salazar"),
    ("Elijah", "Robles"),
    ("Ivan", "Marquez"),
    ("Luis", "Reyes"),
    ("Cedrick", "Santiago"),
    ("Harvey", "Tolentino"),
    ("Vincent", "Ocampo"),
]

bsmt_students = []
bsme_students = []

for index, (first, last) in enumerate(bsmt_names, start=1):
    username = f"bsmt_stu{index:02d}"
    user = upsert_user(username, "student123", "student", first, last)
    section = "A" if index <= 8 else "B"
    student = upsert_student_profile(
        user=user,
        department=bsmt,
        student_number=f"2025-BSMT-{index:03d}",
        year_level="1",
        section=section,
    )
    bsmt_students.append(student)

for index, (first, last) in enumerate(bsme_names, start=1):
    username = f"bsme_stu{index:02d}"
    user = upsert_user(username, "student123", "student", first, last)
    section = "A" if index <= 8 else "B"
    student = upsert_student_profile(
        user=user,
        department=bsme,
        student_number=f"2025-BSME-{index:03d}",
        year_level="1",
        section=section,
    )
    bsme_students.append(student)


# ---------------------------------------------------------
# Subjects: 10 total
# ---------------------------------------------------------

subjects = {
    "NAV101": upsert_subject("NAV101", "Fundamentals of Navigation", 3, bsmt),
    "COLREG101": upsert_subject("COLREG101", "Rules of the Road and COLREG", 3, bsmt),
    "SEAM101": upsert_subject("SEAM101", "Basic Seamanship", 2, bsmt),
    "MET101": upsert_subject("MET101", "Marine Meteorology", 3, bsmt),

    "ENG101": upsert_subject("ENG101", "Fundamentals of Marine Engineering", 3, bsme),
    "THERMO101": upsert_subject("THERMO101", "Thermodynamics for Marine Engineers", 3, bsme),
    "ELEC101": upsert_subject("ELEC101", "Marine Electrical Systems", 3, bsme),
    "MECH101": upsert_subject("MECH101", "Engineering Mechanics", 3, bsme),

    "MATH101": upsert_subject("MATH101", "College Algebra and Trigonometry", 3, ge),
    "ENGCOM101": upsert_subject("ENGCOM101", "Technical Communication", 3, ge),
}


# ---------------------------------------------------------
# Class sections
# ---------------------------------------------------------

classes = {
    "NAV101_A": upsert_class_section(subjects["NAV101"], faculty_profiles["nav1"], "BSMT-1A", term, school_year, "MWF 8:00-9:00 AM", "Bridge Lab 1"),
    "COLREG101_A": upsert_class_section(subjects["COLREG101"], faculty_profiles["nav2"], "BSMT-1A", term, school_year, "MWF 9:00-10:00 AM", "Room 204"),
    "SEAM101_B": upsert_class_section(subjects["SEAM101"], faculty_profiles["nav1"], "BSMT-1B", term, school_year, "TTH 1:00-2:30 PM", "Deck Training Room"),
    "MET101_B": upsert_class_section(subjects["MET101"], faculty_profiles["nav2"], "BSMT-1B", term, school_year, "TTH 2:30-4:00 PM", "Room 205"),

    "ENG101_A": upsert_class_section(subjects["ENG101"], faculty_profiles["eng1"], "BSME-1A", term, school_year, "MWF 8:00-9:00 AM", "Engine Lab 1"),
    "THERMO101_A": upsert_class_section(subjects["THERMO101"], faculty_profiles["eng2"], "BSME-1A", term, school_year, "MWF 10:00-11:00 AM", "Room 302"),
    "ELEC101_B": upsert_class_section(subjects["ELEC101"], faculty_profiles["eng1"], "BSME-1B", term, school_year, "TTH 8:00-9:30 AM", "Electrical Lab"),
    "MECH101_B": upsert_class_section(subjects["MECH101"], faculty_profiles["eng2"], "BSME-1B", term, school_year, "TTH 10:00-11:30 AM", "Room 303"),

    "MATH101_BSMT_A": upsert_class_section(subjects["MATH101"], faculty_profiles["ge1"], "BSMT-1A", term, school_year, "MWF 1:00-2:00 PM", "Room 101"),
    "ENGCOM101_BSME_A": upsert_class_section(subjects["ENGCOM101"], faculty_profiles["ge2"], "BSME-1A", term, school_year, "TTH 1:00-2:30 PM", "Room 102"),
}


# ---------------------------------------------------------
# Enrollments
# ---------------------------------------------------------

all_enrollments = []

# BSMT A: first 8 students
for student in bsmt_students[:8]:
    all_enrollments.append(enroll_student(student, classes["NAV101_A"]))
    all_enrollments.append(enroll_student(student, classes["COLREG101_A"]))
    all_enrollments.append(enroll_student(student, classes["MATH101_BSMT_A"]))

# BSMT B: remaining 7 students
for student in bsmt_students[8:]:
    all_enrollments.append(enroll_student(student, classes["SEAM101_B"]))
    all_enrollments.append(enroll_student(student, classes["MET101_B"]))

# BSME A: first 8 students
for student in bsme_students[:8]:
    all_enrollments.append(enroll_student(student, classes["ENG101_A"]))
    all_enrollments.append(enroll_student(student, classes["THERMO101_A"]))
    all_enrollments.append(enroll_student(student, classes["ENGCOM101_BSME_A"]))

# BSME B: remaining 7 students
for student in bsme_students[8:]:
    all_enrollments.append(enroll_student(student, classes["ELEC101_B"]))
    all_enrollments.append(enroll_student(student, classes["MECH101_B"]))


# ---------------------------------------------------------
# Grades and attendance
# Mix of high, average, borderline, and at-risk records
# ---------------------------------------------------------

grade_patterns = [
    (94, 95, 92, 96, 98),
    (88, 90, 86, 89, 94),
    (82, 84, 80, 85, 90),
    (78, 80, 76, 79, 85),
    (74, 76, 72, 75, 80),
    (68, 70, 66, 72, 76),
    (91, 89, 93, 90, 95),
    (85, 87, 83, 86, 91),
    (79, 78, 77, 80, 82),
    (72, 74, 70, 73, 78),
]

attendance_patterns = [
    (19, 0, 1),
    (18, 1, 1),
    (17, 2, 1),
    (16, 3, 1),
    (15, 4, 1),
    (14, 5, 1),
    (13, 6, 1),
    (12, 7, 1),
    (18, 0, 2),
    (16, 2, 2),
]

for index, enrollment in enumerate(all_enrollments):
    grade_data = grade_patterns[index % len(grade_patterns)]
    attendance_data = attendance_patterns[index % len(attendance_patterns)]

    create_grade(enrollment, *grade_data)
    create_attendance(enrollment, *attendance_data)


# ---------------------------------------------------------
# Faculty evaluation summaries
# ---------------------------------------------------------

evaluation_data = [
    ("student", 92.50, "Very effective in classroom discussion."),
    ("peer", 90.00, "Organized and well-prepared."),
    ("admin", 91.25, "Meets instructional and reporting expectations."),
    ("student", 88.75, "Clear explanation of concepts."),
    ("peer", 87.50, "Consistent in teaching delivery."),
    ("admin", 89.00, "Shows good classroom management."),
]

faculty_list = list(faculty_profiles.values())

for index, faculty in enumerate(faculty_list):
    base = evaluation_data[index % len(evaluation_data)]
    create_evaluation(faculty, base[0], base[1], base[2], term, school_year)
    create_evaluation(faculty, "student", min(100, Decimal(str(base[1])) + Decimal("1.25")), "Positive student feedback summary.", term, school_year)


# ---------------------------------------------------------
# Uploaded demo forms
# ---------------------------------------------------------

forms_data = [
    (
        "Student Certification Request Form",
        "Used by students to request certification of enrollment or academic standing.",
        "certification",
        "student_certification_request.txt",
    ),
    (
        "Grade Verification Form",
        "Used to request verification or review of encoded grades.",
        "student",
        "grade_verification_form.txt",
    ),
    (
        "Attendance Concern Form",
        "Used to submit attendance-related concerns for review.",
        "student",
        "attendance_concern_form.txt",
    ),
    (
        "Faculty Grade Submission Form",
        "Used by faculty members as a supporting document for grade submission.",
        "faculty",
        "faculty_grade_submission_form.txt",
    ),
    (
        "Department Academic Summary Form",
        "Used by administrators for department-level academic monitoring.",
        "admin",
        "department_academic_summary_form.txt",
    ),
]

for title, description, category, filename in forms_data:
    create_demo_form(title, description, category, filename, admin_user)


# ---------------------------------------------------------
# Final verification summary
# ---------------------------------------------------------

print("======================================")
print("April 26 demo database completed.")
print("======================================")
print("Departments:", Department.objects.count())
print("Faculty Profiles:", FacultyProfile.objects.count())
print("Student Profiles:", StudentProfile.objects.count())
print("Subjects:", Subject.objects.count())
print("Class Sections:", ClassSection.objects.count())
print("Enrollments:", Enrollment.objects.count())
print("Grades:", Grade.objects.count())
print("Attendance Summaries:", AttendanceSummary.objects.count())
print("Faculty Evaluations:", FacultyEvaluation.objects.count())
print("Academic Forms:", AcademicForm.objects.count())
print("======================================")
print("Demo login accounts:")
print("admin1 / admin123")
print("faculty_nav1 / faculty123")
print("faculty_eng1 / faculty123")
print("faculty_ge1 / faculty123")
print("bsmt_stu01 / student123")
print("bsme_stu01 / student123")
print("======================================")