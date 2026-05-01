from academics.models import AdvisorySection, Department, FacultyProfile

bsmt = Department.objects.get(code="BSMT")
bsme = Department.objects.get(code="BSME")

faculty_nav1 = FacultyProfile.objects.get(employee_id="FAC-001")
faculty_nav2 = FacultyProfile.objects.get(employee_id="FAC-002")
faculty_eng1 = FacultyProfile.objects.get(employee_id="FAC-003")
faculty_eng2 = FacultyProfile.objects.get(employee_id="FAC-004")

AdvisorySection.objects.update_or_create(
    section_name="BSMT-1A",
    term="1st Semester",
    school_year="2025-2026",
    defaults={
        "department": bsmt,
        "year_level": "1",
        "adviser": faculty_nav1,
    }
)

AdvisorySection.objects.update_or_create(
    section_name="BSMT-1B",
    term="1st Semester",
    school_year="2025-2026",
    defaults={
        "department": bsmt,
        "year_level": "1",
        "adviser": faculty_nav2,
    }
)

AdvisorySection.objects.update_or_create(
    section_name="BSME-1A",
    term="1st Semester",
    school_year="2025-2026",
    defaults={
        "department": bsme,
        "year_level": "1",
        "adviser": faculty_eng1,
    }
)

AdvisorySection.objects.update_or_create(
    section_name="BSME-1B",
    term="1st Semester",
    school_year="2025-2026",
    defaults={
        "department": bsme,
        "year_level": "1",
        "adviser": faculty_eng2,
    }
)

print("Class advisory records created.")