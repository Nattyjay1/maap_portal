from django.contrib.auth import get_user_model
from academics.models import Department, FacultyProfile, StudentProfile, Subject, ClassSection, Enrollment

User = get_user_model()


def upsert_user(username, password, role, first_name, last_name, email=None, is_staff=False):
    user, created = User.objects.get_or_create(username=username)
    user.role = role
    user.first_name = first_name
    user.last_name = last_name
    user.is_active = True
    user.is_staff = is_staff
    if email:
        user.email = email
    user.set_password(password)
    user.save()
    return user


def upsert_department(code, name):
    dept, created = Department.objects.get_or_create(code=code)
    dept.name = name
    dept.save()
    return dept


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


def enroll_students(student_profiles, class_section):
    for student in student_profiles:
        Enrollment.objects.get_or_create(
            student=student,
            class_section=class_section
        )


print("Creating departments...")
bsmt = upsert_department("BSMT", "Bachelor of Science in Marine Transportation")
bsmare = upsert_department("BSMarE", "Bachelor of Science in Marine Engineering")

print("Creating users...")
admin1 = upsert_user("admin1", "admin123", "admin", "Portal", "Admin")

faculty_nav1_user = upsert_user("faculty_nav1", "faculty123", "faculty", "Ramon", "Dela Cruz")
faculty_nav2_user = upsert_user("faculty_nav2", "faculty123", "faculty", "Julius", "Mendoza")
faculty_nav3_user = upsert_user("faculty_nav3", "faculty123", "faculty", "Arvin", "Santos")
faculty_eng1_user = upsert_user("faculty_eng1", "faculty123", "faculty", "Michael", "Reyes")
faculty_eng2_user = upsert_user("faculty_eng2", "faculty123", "faculty", "Paolo", "Castillo")
faculty_eng3_user = upsert_user("faculty_eng3", "faculty123", "faculty", "Dennis", "Ferrer")

bsmt_users = [
    upsert_user("bsmt_stu01", "student123", "student", "John Mark", "Santos"),
    upsert_user("bsmt_stu02", "student123", "student", "Carl Vincent", "Ramos"),
    upsert_user("bsmt_stu03", "student123", "student", "Joshua", "Perez"),
    upsert_user("bsmt_stu04", "student123", "student", "Miguel", "Torres"),
    upsert_user("bsmt_stu05", "student123", "student", "Adrian", "Cruz"),
    upsert_user("bsmt_stu06", "student123", "student", "Noel", "Garcia"),
    upsert_user("bsmt_stu07", "student123", "student", "Kevin", "Bautista"),
    upsert_user("bsmt_stu08", "student123", "student", "Lester", "Medina"),
    upsert_user("bsmt_stu09", "student123", "student", "Francis", "Lim"),
    upsert_user("bsmt_stu10", "student123", "student", "Patrick", "Dominguez"),
]

bsmare_users = [
    upsert_user("bsmare_stu01", "student123", "student", "Ryan", "Navarro"),
    upsert_user("bsmare_stu02", "student123", "student", "Ethan", "Villanueva"),
    upsert_user("bsmare_stu03", "student123", "student", "Marco", "Alvarez"),
    upsert_user("bsmare_stu04", "student123", "student", "Neil", "Fernandez"),
    upsert_user("bsmare_stu05", "student123", "student", "Christian", "Lopez"),
    upsert_user("bsmare_stu06", "student123", "student", "Jerome", "Aquino"),
    upsert_user("bsmare_stu07", "student123", "student", "Alden", "Flores"),
    upsert_user("bsmare_stu08", "student123", "student", "Kenneth", "Padilla"),
    upsert_user("bsmare_stu09", "student123", "student", "Mark Joseph", "Salazar"),
    upsert_user("bsmare_stu10", "student123", "student", "Elijah", "Robles"),
]

print("Creating faculty profiles...")
faculty_nav1 = upsert_faculty_profile(faculty_nav1_user, bsmt, "FAC-001", "Instructor I")
faculty_nav2 = upsert_faculty_profile(faculty_nav2_user, bsmt, "FAC-002", "Instructor II")
faculty_nav3 = upsert_faculty_profile(faculty_nav3_user, bsmt, "FAC-003", "Assistant Professor")
faculty_eng1 = upsert_faculty_profile(faculty_eng1_user, bsmare, "FAC-004", "Instructor I")
faculty_eng2 = upsert_faculty_profile(faculty_eng2_user, bsmare, "FAC-005", "Instructor II")
faculty_eng3 = upsert_faculty_profile(faculty_eng3_user, bsmare, "FAC-006", "Assistant Professor")

print("Creating student profiles...")
bsmt_profiles = [
    upsert_student_profile(bsmt_users[0], bsmt, "2025-BSMT-001", "1", "A"),
    upsert_student_profile(bsmt_users[1], bsmt, "2025-BSMT-002", "1", "A"),
    upsert_student_profile(bsmt_users[2], bsmt, "2025-BSMT-003", "1", "A"),
    upsert_student_profile(bsmt_users[3], bsmt, "2025-BSMT-004", "1", "A"),
    upsert_student_profile(bsmt_users[4], bsmt, "2025-BSMT-005", "1", "A"),
    upsert_student_profile(bsmt_users[5], bsmt, "2025-BSMT-006", "1", "B"),
    upsert_student_profile(bsmt_users[6], bsmt, "2025-BSMT-007", "1", "B"),
    upsert_student_profile(bsmt_users[7], bsmt, "2025-BSMT-008", "1", "B"),
    upsert_student_profile(bsmt_users[8], bsmt, "2025-BSMT-009", "1", "B"),
    upsert_student_profile(bsmt_users[9], bsmt, "2025-BSMT-010", "1", "B"),
]

bsmare_profiles = [
    upsert_student_profile(bsmare_users[0], bsmare, "2025-BSMARE-001", "1", "A"),
    upsert_student_profile(bsmare_users[1], bsmare, "2025-BSMARE-002", "1", "A"),
    upsert_student_profile(bsmare_users[2], bsmare, "2025-BSMARE-003", "1", "A"),
    upsert_student_profile(bsmare_users[3], bsmare, "2025-BSMARE-004", "1", "A"),
    upsert_student_profile(bsmare_users[4], bsmare, "2025-BSMARE-005", "1", "A"),
    upsert_student_profile(bsmare_users[5], bsmare, "2025-BSMARE-006", "1", "B"),
    upsert_student_profile(bsmare_users[6], bsmare, "2025-BSMARE-007", "1", "B"),
    upsert_student_profile(bsmare_users[7], bsmare, "2025-BSMARE-008", "1", "B"),
    upsert_student_profile(bsmare_users[8], bsmare, "2025-BSMARE-009", "1", "B"),
    upsert_student_profile(bsmare_users[9], bsmare, "2025-BSMARE-010", "1", "B"),
]

print("Creating subjects...")
nav101 = upsert_subject("NAV101", "Fundamentals of Navigation", 3, bsmt)
colreg101 = upsert_subject("COLREG101", "Rules of the Road and COLREG", 3, bsmt)
seam101 = upsert_subject("SEAM101", "Basic Seamanship", 2, bsmt)
met101 = upsert_subject("MET101", "Marine Meteorology", 3, bsmt)

eng101 = upsert_subject("ENG101", "Fundamentals of Marine Engineering", 3, bsmare)
thermo101 = upsert_subject("THERMO101", "Thermodynamics for Marine Engineers", 3, bsmare)
elec101 = upsert_subject("ELEC101", "Marine Electrical Systems", 3, bsmare)
mech101 = upsert_subject("MECH101", "Engineering Mechanics", 3, bsmare)

print("Creating class sections...")
term = "1st Semester"
school_year = "2025-2026"

class_1 = upsert_class_section(nav101, faculty_nav1, "BSMT-1A", term, school_year, "MWF 8:00-9:00 AM", "Bridge Lab 1")
class_2 = upsert_class_section(colreg101, faculty_nav2, "BSMT-1A", term, school_year, "MWF 9:00-10:00 AM", "Room 204")
class_3 = upsert_class_section(seam101, faculty_nav3, "BSMT-1B", term, school_year, "TTH 1:00-2:30 PM", "Deck Training Room")
class_4 = upsert_class_section(met101, faculty_nav1, "BSMT-1B", term, school_year, "TTH 2:30-4:00 PM", "Room 205")

class_5 = upsert_class_section(eng101, faculty_eng1, "BSMarE-1A", term, school_year, "MWF 8:00-9:00 AM", "Engine Lab 1")
class_6 = upsert_class_section(thermo101, faculty_eng2, "BSMarE-1A", term, school_year, "MWF 10:00-11:00 AM", "Room 302")
class_7 = upsert_class_section(elec101, faculty_eng3, "BSMarE-1B", term, school_year, "TTH 8:00-9:30 AM", "Electrical Lab")
class_8 = upsert_class_section(mech101, faculty_eng1, "BSMarE-1B", term, school_year, "TTH 10:00-11:30 AM", "Room 303")

print("Creating enrollments...")
enroll_students(bsmt_profiles[:5], class_1)
enroll_students(bsmt_profiles[:5], class_2)
enroll_students(bsmt_profiles[5:], class_3)
enroll_students(bsmt_profiles[5:], class_4)

enroll_students(bsmare_profiles[:5], class_5)
enroll_students(bsmare_profiles[:5], class_6)
enroll_students(bsmare_profiles[5:], class_7)
enroll_students(bsmare_profiles[5:], class_8)

print("======================================")
print("Dummy data creation completed.")
print("Portal test accounts:")
print("admin1 / admin123")
print("faculty_nav1 / faculty123")
print("faculty_eng1 / faculty123")
print("bsmt_stu01 / student123")
print("bsmare_stu01 / student123")
print("======================================")