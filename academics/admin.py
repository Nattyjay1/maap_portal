from django.contrib import admin
from .models import (
    Department,
    FacultyProfile,
    StudentProfile,
    Subject,
    ClassSection,
    Enrollment,
    Grade,
    GradeAdjustmentLog,
    AttendanceSummary,
    AdvisorySection,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "department", "designation")
    search_fields = ("employee_id", "user__username", "user__first_name", "user__last_name")
    list_filter = ("department",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_number", "user", "department", "year_level", "section")
    search_fields = ("student_number", "user__username", "user__first_name", "user__last_name")
    list_filter = ("department", "year_level", "section")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "units", "department")
    search_fields = ("code", "title")
    list_filter = ("department",)


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ("subject", "section_name", "faculty", "term", "school_year", "schedule", "room")
    search_fields = ("subject__code", "subject__title", "section_name", "faculty__user__username")
    list_filter = ("term", "school_year", "subject__department")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "class_section", "enrolled_at")
    search_fields = ("student__student_number", "student__user__username", "class_section__subject__code")
    list_filter = ("class_section__term", "class_section__school_year")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "quiz_total",
        "activity_total",
        "exam_total",
        "lab_total",
        "attendance_score",
        "final_grade",
        "remarks",
        "updated_at",
    )
    search_fields = (
        "enrollment__student__student_number",
        "enrollment__student__user__username",
        "enrollment__class_section__subject__code",
    )
    list_filter = (
        "remarks",
        "enrollment__class_section__term",
        "enrollment__class_section__school_year",
    )
    

@admin.register(GradeAdjustmentLog)
class GradeAdjustmentLogAdmin(admin.ModelAdmin):
    list_display = (
        "grade",
        "field_changed",
        "old_value",
        "new_value",
        "edited_by",
        "edited_at",
    )
    search_fields = (
        "grade__enrollment__student__student_number",
        "grade__enrollment__student__user__username",
        "grade__enrollment__class_section__subject__code",
        "field_changed",
        "reason",
    )
    list_filter = ("field_changed", "edited_at")
    

@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "present_count",
        "absent_count",
        "late_count",
        "attendance_percent",
        "status",
        "updated_at",
    )
    search_fields = (
        "enrollment__student__student_number",
        "enrollment__student__user__username",
        "enrollment__class_section__subject__code",
    )
    list_filter = (
        "status",
        "enrollment__class_section__term",
        "enrollment__class_section__school_year",
    )


@admin.register(AdvisorySection)
class AdvisorySectionAdmin(admin.ModelAdmin):
    list_display = (
        "section_name",
        "department",
        "year_level",
        "adviser",
        "term",
        "school_year",
    )
    search_fields = (
        "section_name",
        "department__code",
        "adviser__user__first_name",
        "adviser__user__last_name",
    )
    list_filter = ("department", "term", "school_year")


