import json

from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import redirect, render

from academics.models import Enrollment, Grade, AttendanceSummary


@login_required
def analytics_dashboard(request):
    """
    Role-aware analytics dashboard.
    Admin and faculty already have analytics in their dashboards.
    Student receives a student-specific analytics dashboard.
    """

    if request.user.role == "admin":
        return redirect("admin-dashboard")

    if request.user.role == "faculty":
        return redirect("faculty-dashboard")

    if request.user.role == "student":
        return student_analytics_dashboard(request)

    return redirect("role-redirect")


@login_required
def student_analytics_dashboard(request):
    if request.user.role != "student" or not hasattr(request.user, "student_profile"):
        return redirect("role-redirect")

    student_profile = request.user.student_profile

    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("class_section__subject", "class_section")
        .order_by("class_section__subject__code")
    )

    grade_qs = Grade.objects.filter(enrollment__student=student_profile)
    attendance_qs = AttendanceSummary.objects.filter(enrollment__student=student_profile)

    average_grade = grade_qs.aggregate(avg=Avg("final_grade")).get("avg")
    average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

    subject_labels = []
    grade_values = []
    attendance_values = []

    risk_summary = {
        "High Risk": 0,
        "Moderate Risk": 0,
        "Low Risk": 0,
        "No Data": 0,
    }

    rows = []

    for enrollment in enrollments:
        subject = enrollment.class_section.subject
        subject_label = f"{subject.code}"

        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        final_grade = float(grade.final_grade) if grade else None
        attendance_percent = float(attendance.attendance_percent) if attendance else None

        subject_labels.append(subject_label)
        grade_values.append(final_grade if final_grade is not None else 0)
        attendance_values.append(attendance_percent if attendance_percent is not None else 0)

        risk_level = "Low Risk"
        advisory = "Student is currently within acceptable academic standing for this subject."

        if not grade and not attendance:
            risk_level = "No Data"
            advisory = "No grade and attendance data are available yet for this subject."

        elif grade and grade.final_grade < 75:
            risk_level = "High Risk"
            advisory = "Immediate academic monitoring is recommended due to low grade performance."

        elif attendance and attendance.attendance_percent < 75:
            risk_level = "High Risk"
            advisory = "Immediate monitoring is recommended due to critical attendance level."

        elif grade and grade.final_grade < 80:
            risk_level = "Moderate Risk"
            advisory = "Continued monitoring is recommended because the grade is near the minimum threshold."

        elif attendance and attendance.attendance_percent < 85:
            risk_level = "Moderate Risk"
            advisory = "Attendance is acceptable but should be monitored to avoid academic risk."

        risk_summary[risk_level] += 1

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "risk_level": risk_level,
            "advisory": advisory,
        })

    if risk_summary["High Risk"] > 0:
        overall_risk = "High Risk"
        overall_badge = "danger"
        overall_advisory = "Immediate academic monitoring is recommended because one or more subjects show high-risk indicators."
    elif risk_summary["Moderate Risk"] > 0:
        overall_risk = "Moderate Risk"
        overall_badge = "warning"
        overall_advisory = "The student is generally stable but requires continued monitoring in some subjects."
    elif risk_summary["No Data"] == enrollments.count() and enrollments.count() > 0:
        overall_risk = "No Data"
        overall_badge = "secondary"
        overall_advisory = "Academic analytics will become available once grades and attendance are encoded."
    else:
        overall_risk = "Low Risk"
        overall_badge = "success"
        overall_advisory = "The student is currently within acceptable academic standing based on available records."

    context = {
        "page_title": "Student Analytics Dashboard",
        "student_profile": student_profile,
        "enrolled_subjects": enrollments.count(),
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "overall_risk": overall_risk,
        "overall_badge": overall_badge,
        "overall_advisory": overall_advisory,
        "rows": rows,

        "subject_labels": json.dumps(subject_labels),
        "grade_values": json.dumps(grade_values),
        "attendance_values": json.dumps(attendance_values),
        "risk_labels": json.dumps(list(risk_summary.keys())),
        "risk_values": json.dumps(list(risk_summary.values())),
    }

    return render(request, "analytics_app/student_analytics_dashboard.html", context)