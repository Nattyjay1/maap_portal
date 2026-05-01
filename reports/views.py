from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import (
    AttendanceSummary,
    ClassSection,
    Department,
    Enrollment,
    FacultyProfile,
    Grade,
    StudentProfile,
)


def _admin_check(request):
    return request.user.is_authenticated and request.user.role == "admin"


def _faculty_check(request):
    return request.user.is_authenticated and request.user.role == "faculty" and hasattr(request.user, "faculty_profile")


def _student_check(request):
    return request.user.is_authenticated and request.user.role == "student" and hasattr(request.user, "student_profile")


@login_required
def reports_index(request):
    classes = ClassSection.objects.none()
    students = StudentProfile.objects.none()

    if request.user.role == "admin":
        classes = ClassSection.objects.select_related("subject", "faculty__user").all()
        students = StudentProfile.objects.select_related("user", "department").all()[:20]
    elif request.user.role == "faculty" and hasattr(request.user, "faculty_profile"):
        classes = ClassSection.objects.select_related("subject", "faculty__user").filter(
            faculty=request.user.faculty_profile
        )
    elif request.user.role == "student":
        pass
    else:
        return redirect("role-redirect")

    context = {
        "page_title": "Reports",
        "classes": classes,
        "students": students,
    }

    return render(request, "reports/reports_index.html", context)


@login_required
def printable_grade_report(request, class_id):
    class_section = get_object_or_404(
        ClassSection.objects.select_related("subject", "faculty__user"),
        id=class_id
    )

    if request.user.role == "faculty":
        if not hasattr(request.user, "faculty_profile") or class_section.faculty != request.user.faculty_profile:
            messages.error(request, "You are not authorized to print this class report.")
            return redirect("role-redirect")
    elif request.user.role != "admin":
        messages.error(request, "You are not authorized to print this report.")
        return redirect("role-redirect")

    enrollments = (
        Enrollment.objects
        .filter(class_section=class_section)
        .select_related("student__user", "student__department")
        .order_by("student__student_number")
    )

    rows = []
    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
        })

    average_grade = Grade.objects.filter(enrollment__class_section=class_section).aggregate(
        avg=Avg("final_grade")
    )["avg"]

    passed_count = Grade.objects.filter(
        enrollment__class_section=class_section,
        remarks="Passed"
    ).count()

    failed_count = Grade.objects.filter(
        enrollment__class_section=class_section,
        remarks="Failed"
    ).count()

    context = {
        "page_title": "Printable Grade Report",
        "class_section": class_section,
        "rows": rows,
        "average_grade": average_grade,
        "passed_count": passed_count,
        "failed_count": failed_count,
    }

    return render(request, "reports/printable_grade_report.html", context)


@login_required
def printable_my_progress_report(request):
    if not _student_check(request):
        return redirect("role-redirect")

    student_profile = request.user.student_profile

    return _render_student_progress_report(request, student_profile)


@login_required
def printable_student_progress_report(request, student_id):
    if not _admin_check(request):
        return redirect("role-redirect")

    student_profile = get_object_or_404(
        StudentProfile.objects.select_related("user", "department"),
        id=student_id
    )

    return _render_student_progress_report(request, student_profile)


def _render_student_progress_report(request, student_profile):
    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("class_section__subject", "class_section__faculty__user")
        .order_by("class_section__subject__code")
    )

    rows = []
    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        risk = "Low Risk"
        if grade and grade.final_grade < 75:
            risk = "High Risk"
        if attendance and attendance.attendance_percent < 75:
            risk = "High Risk"
        if risk != "High Risk":
            if grade and grade.final_grade < 80:
                risk = "Moderate Risk"
            if attendance and attendance.attendance_percent < 85:
                risk = "Moderate Risk"

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "risk": risk,
        })

    average_grade = Grade.objects.filter(enrollment__student=student_profile).aggregate(
        avg=Avg("final_grade")
    )["avg"]

    average_attendance = AttendanceSummary.objects.filter(enrollment__student=student_profile).aggregate(
        avg=Avg("attendance_percent")
    )["avg"]

    context = {
        "page_title": "Printable Student Progress Report",
        "student_profile": student_profile,
        "rows": rows,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
    }

    return render(request, "reports/printable_student_progress_report.html", context)


@login_required
def printable_department_summary(request):
    if not _admin_check(request):
        return redirect("role-redirect")

    departments = Department.objects.all().order_by("code")

    summary_rows = []

    for department in departments:
        # Faculty count still belongs to the faculty department
        faculty_count = FacultyProfile.objects.filter(department=department).count()

        # Student count is based on students enrolled in subjects handled by this department
        student_count = (
            Enrollment.objects
            .filter(class_section__subject__department=department)
            .values("student")
            .distinct()
            .count()
        )

        avg_grade = (
            Grade.objects
            .filter(enrollment__class_section__subject__department=department)
            .aggregate(avg=Avg("final_grade"))
            .get("avg")
        )

        avg_attendance = (
            AttendanceSummary.objects
            .filter(enrollment__class_section__subject__department=department)
            .aggregate(avg=Avg("attendance_percent"))
            .get("avg")
        )

        total_grade_records = (
            Grade.objects
            .filter(enrollment__class_section__subject__department=department)
            .count()
        )

        pass_count = (
            Grade.objects
            .filter(
                enrollment__class_section__subject__department=department,
                remarks="Passed"
            )
            .count()
        )

        fail_count = (
            Grade.objects
            .filter(
                enrollment__class_section__subject__department=department,
                remarks="Failed"
            )
            .count()
        )

        summary_rows.append({
            "department": department,
            "student_count": student_count,
            "faculty_count": faculty_count,
            "avg_grade": avg_grade,
            "avg_attendance": avg_attendance,
            "total_grade_records": total_grade_records,
            "pass_count": pass_count,
            "fail_count": fail_count,
        })

    context = {
        "page_title": "Printable Department Summary",
        "summary_rows": summary_rows,
    }

    return render(request, "reports/printable_department_summary.html", context)