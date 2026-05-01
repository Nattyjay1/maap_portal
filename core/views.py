import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from django.db.models import Avg, Count, Q
from academics.models import (ClassSection, 
                              Enrollment, 
                              Grade, 
                              GradeAdjustmentLog, 
                              AttendanceSummary, 
                              Department, 
                              FacultyProfile)
from evaluations.models import FacultyEvaluation


def home(request):
    if request.user.is_authenticated:
        return redirect("role-redirect")
    return redirect("login")


@login_required
def role_redirect_view(request):
    user = request.user

    if user.role == "admin":
        return redirect("admin-dashboard")
    elif user.role == "faculty":
        return redirect("faculty-dashboard")
    elif user.role == "student":
        return redirect("student-dashboard")
    return redirect("login")


@login_required
def admin_dashboard(request):
    if request.user.role != "admin":
        return redirect("role-redirect")

    total_departments = Department.objects.count()
    total_faculty = FacultyProfile.objects.count()

    # Department performance based on SUBJECT department
    department_performance = list(
        Grade.objects
        .values(
            "enrollment__class_section__subject__department__code",
            "enrollment__class_section__subject__department__name",
        )
        .annotate(
            avg_final_grade=Avg("final_grade"),
            avg_attendance=Avg("enrollment__attendance_summary__attendance_percent"),
            total_students=Count("enrollment__student", distinct=True),
        )
        .order_by("enrollment__class_section__subject__department__code")
    )

    department_chart_labels = [
        item["enrollment__class_section__subject__department__code"] or "N/A"
        for item in department_performance
    ]

    department_chart_values = [
        float(item["avg_final_grade"]) if item["avg_final_grade"] is not None else 0
        for item in department_performance
    ]

    # Grade distribution
    grade_distribution_labels = ["Below 75", "75-79", "80-84", "85-89", "90-100"]

    grade_distribution_values = [
        Grade.objects.filter(final_grade__lt=75).count(),
        Grade.objects.filter(final_grade__gte=75, final_grade__lt=80).count(),
        Grade.objects.filter(final_grade__gte=80, final_grade__lt=85).count(),
        Grade.objects.filter(final_grade__gte=85, final_grade__lt=90).count(),
        Grade.objects.filter(final_grade__gte=90).count(),
    ]

    # Average attendance by SUBJECT department
    attendance_trend = list(
        AttendanceSummary.objects
        .values("enrollment__class_section__subject__department__code")
        .annotate(avg_attendance=Avg("attendance_percent"))
        .order_by("enrollment__class_section__subject__department__code")
    )

    attendance_trend_labels = [
        item["enrollment__class_section__subject__department__code"] or "N/A"
        for item in attendance_trend
    ]

    attendance_trend_values = [
        float(item["avg_attendance"]) if item["avg_attendance"] is not None else 0
        for item in attendance_trend
    ]

    # Pass / fail summary
    passed_count = Grade.objects.filter(remarks="Passed").count()
    failed_count = Grade.objects.filter(remarks="Failed").count()

    pass_fail_labels = ["Passed", "Failed"]
    pass_fail_values = [passed_count, failed_count]

    # Faculty encoding progress
    faculty_progress = []
    faculty_qs = FacultyProfile.objects.select_related("user", "department").order_by("employee_id")

    for faculty in faculty_qs:
        total_records = Enrollment.objects.filter(class_section__faculty=faculty).count()
        graded_records = Grade.objects.filter(enrollment__class_section__faculty=faculty).count()

        progress_percent = 0
        if total_records > 0:
            progress_percent = round((graded_records / total_records) * 100, 2)

        if progress_percent == 100:
            progress_status = "Complete"
        elif progress_percent > 0:
            progress_status = "In Progress"
        else:
            progress_status = "Not Started"

        faculty_progress.append({
            "faculty": faculty,
            "total_records": total_records,
            "graded_records": graded_records,
            "progress_percent": progress_percent,
            "progress_status": progress_status,
        })

    faculty_progress_labels = [
        row["faculty"].user.get_full_name() or row["faculty"].user.username
        for row in faculty_progress
    ]

    faculty_progress_values = [
        row["progress_percent"]
        for row in faculty_progress
    ]

    # Unique student risk logic
    student_risk = {}

    enrollments = (
        Enrollment.objects
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject",
        )
        .all()
    )

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        risk_rank = 1
        risk_level = "Low Risk"
        reason = "Acceptable grade and attendance indicators."

        if grade and grade.final_grade < 75:
            risk_rank = 3
            risk_level = "High Risk"
            reason = "Final grade is below the passing threshold."

        if attendance and attendance.attendance_percent < 75:
            risk_rank = 3
            risk_level = "High Risk"
            reason = "Attendance is below the critical threshold."

        if risk_rank != 3:
            if grade and grade.final_grade < 80:
                risk_rank = 2
                risk_level = "Moderate Risk"
                reason = "Final grade is near the minimum threshold."

            if attendance and attendance.attendance_percent < 85:
                risk_rank = 2
                risk_level = "Moderate Risk"
                reason = "Attendance requires continued monitoring."

        student_id = enrollment.student.id

        if student_id not in student_risk or risk_rank > student_risk[student_id]["risk_rank"]:
            student_risk[student_id] = {
                "student": enrollment.student,
                "department": enrollment.student.department,
                "subject": enrollment.class_section.subject,
                "grade": grade,
                "attendance": attendance,
                "risk_rank": risk_rank,
                "risk_level": risk_level,
                "reason": reason,
            }

    high_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "High Risk")
    moderate_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "Moderate Risk")
    low_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "Low Risk")

    at_risk_students_count = high_risk_count + moderate_risk_count

    at_risk_students_preview = [
        item for item in student_risk.values()
        if item["risk_level"] in ["High Risk", "Moderate Risk"]
    ][:8]

    at_risk_labels = ["High Risk", "Moderate Risk", "Low Risk"]
    at_risk_values = [high_risk_count, moderate_risk_count, low_risk_count]

    # Evaluation summary
    evaluation_summary = list(
        FacultyEvaluation.objects
        .values(
            "faculty__employee_id",
            "faculty__user__first_name",
            "faculty__user__last_name",
            "faculty__department__code",
        )
        .annotate(
            average_score=Avg("evaluation_score"),
            total_evaluations=Count("id"),
        )
        .order_by("-average_score")
    )

    overall_evaluation_average = FacultyEvaluation.objects.aggregate(
        avg=Avg("evaluation_score")
    )["avg"]

    context = {
        "page_title": "Admin Dashboard",

        "total_departments": total_departments,
        "total_faculty": total_faculty,
        "at_risk_students_count": at_risk_students_count,
        "overall_evaluation_average": overall_evaluation_average,

        "department_performance": department_performance,
        "faculty_progress": faculty_progress,
        "evaluation_summary": evaluation_summary[:8],
        "at_risk_students_preview": at_risk_students_preview,

        "department_chart_labels": json.dumps(department_chart_labels),
        "department_chart_values": json.dumps(department_chart_values),

        "grade_distribution_labels": json.dumps(grade_distribution_labels),
        "grade_distribution_values": json.dumps(grade_distribution_values),

        "attendance_trend_labels": json.dumps(attendance_trend_labels),
        "attendance_trend_values": json.dumps(attendance_trend_values),

        "pass_fail_labels": json.dumps(pass_fail_labels),
        "pass_fail_values": json.dumps(pass_fail_values),

        "at_risk_labels": json.dumps(at_risk_labels),
        "at_risk_values": json.dumps(at_risk_values),

        "faculty_progress_labels": json.dumps(faculty_progress_labels),
        "faculty_progress_values": json.dumps(faculty_progress_values),
    }

    return render(request, "core/admin_dashboard.html", context)


@login_required
def admin_forms_placeholder(request):
    if request.user.role != "admin":
        return redirect("role-redirect")
    return render(request, "core/admin_forms_placeholder.html", {"page_title": "Forms"})


@login_required
def admin_reports_placeholder(request):
    if request.user.role != "admin":
        return redirect("role-redirect")
    return render(request, "core/admin_reports_placeholder.html", {"page_title": "Reports"})


@login_required
def faculty_dashboard(request):
    if request.user.role != "faculty" or not hasattr(request.user, "faculty_profile"):
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    assigned_classes_qs = (
        ClassSection.objects
        .filter(faculty=faculty_profile)
        .select_related("subject")
        .annotate(
            total_students=Count("enrollments"),
            avg_grade=Avg("enrollments__grade__final_grade"),
            avg_attendance=Avg("enrollments__attendance_summary__attendance_percent"),
        )
        .order_by("school_year", "term", "section_name")
    )

    assigned_classes = assigned_classes_qs.count()

    total_students = (
        Enrollment.objects
        .filter(class_section__faculty=faculty_profile)
        .values("student")
        .distinct()
        .count()
    )

    total_records = Enrollment.objects.filter(
        class_section__faculty=faculty_profile
    ).count()

    graded_records = Grade.objects.filter(
        enrollment__class_section__faculty=faculty_profile
    ).count()

    encoding_progress = 0
    if total_records > 0:
        encoding_progress = round((graded_records / total_records) * 100, 2)

    average_grade = (
        Grade.objects
        .filter(enrollment__class_section__faculty=faculty_profile)
        .aggregate(avg=Avg("final_grade"))
        .get("avg")
    )

    average_attendance = (
        AttendanceSummary.objects
        .filter(enrollment__class_section__faculty=faculty_profile)
        .aggregate(avg=Avg("attendance_percent"))
        .get("avg")
    )

    average_grade_display = f"{average_grade:.2f}" if average_grade is not None else "0.00"
    average_attendance_display = f"{average_attendance:.2f}%" if average_attendance is not None else "0.00%"

    passed_count = Grade.objects.filter(
        enrollment__class_section__faculty=faculty_profile,
        remarks="Passed"
    ).count()

    failed_count = Grade.objects.filter(
        enrollment__class_section__faculty=faculty_profile,
        remarks="Failed"
    ).count()

    grade_distribution_labels = [
        "Below 75",
        "75-79",
        "80-84",
        "85-89",
        "90-100",
    ]

    grade_distribution_values = [
        Grade.objects.filter(enrollment__class_section__faculty=faculty_profile, final_grade__lt=75).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty_profile, final_grade__gte=75, final_grade__lt=80).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty_profile, final_grade__gte=80, final_grade__lt=85).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty_profile, final_grade__gte=85, final_grade__lt=90).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty_profile, final_grade__gte=90).count(),
    ]

    class_labels = []
    class_grade_values = []
    class_attendance_values = []

    for class_item in assigned_classes_qs:
        class_labels.append(f"{class_item.subject.code} - {class_item.section_name}")
        class_grade_values.append(float(class_item.avg_grade) if class_item.avg_grade is not None else 0)
        class_attendance_values.append(float(class_item.avg_attendance) if class_item.avg_attendance is not None else 0)

    student_risk = {}

    enrollments = (
        Enrollment.objects
        .filter(class_section__faculty=faculty_profile)
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject",
        )
    )

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        risk_rank = 1
        risk_level = "Low Risk"
        reason = "Acceptable grade and attendance indicators."

        if grade and grade.final_grade < 75:
            risk_rank = 3
            risk_level = "High Risk"
            reason = "Final grade is below the passing threshold."

        if attendance and attendance.attendance_percent < 75:
            risk_rank = 3
            risk_level = "High Risk"
            reason = "Attendance is below the critical threshold."

        if risk_rank != 3:
            if grade and grade.final_grade < 80:
                risk_rank = 2
                risk_level = "Moderate Risk"
                reason = "Final grade is near the minimum threshold."

            if attendance and attendance.attendance_percent < 85:
                risk_rank = 2
                risk_level = "Moderate Risk"
                reason = "Attendance requires continued monitoring."

        student_id = enrollment.student.id

        if student_id not in student_risk or risk_rank > student_risk[student_id]["risk_rank"]:
            student_risk[student_id] = {
                "student": enrollment.student,
                "subject": enrollment.class_section.subject,
                "class_section": enrollment.class_section,
                "grade": grade,
                "attendance": attendance,
                "risk_rank": risk_rank,
                "risk_level": risk_level,
                "reason": reason,
            }

    high_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "High Risk")
    moderate_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "Moderate Risk")
    low_risk_count = sum(1 for item in student_risk.values() if item["risk_level"] == "Low Risk")

    at_risk_students_count = high_risk_count + moderate_risk_count

    at_risk_students_preview = [
        item for item in student_risk.values()
        if item["risk_level"] in ["High Risk", "Moderate Risk"]
    ][:8]

    recent_grade_edits = (
        GradeAdjustmentLog.objects
        .filter(grade__enrollment__class_section__faculty=faculty_profile)
        .select_related(
            "edited_by",
            "grade__enrollment__student__user",
            "grade__enrollment__class_section__subject",
        )
        .order_by("-edited_at")[:8]
    )

    context = {
        "page_title": "Faculty Dashboard",

        "assigned_classes": assigned_classes,
        "total_students": total_students,
        "graded_records": graded_records,
        "total_records": total_records,
        "encoding_progress": encoding_progress,
        "average_grade": average_grade_display,
        "average_attendance": average_attendance_display,

        "passed_count": passed_count,
        "failed_count": failed_count,

        "at_risk_students_count": at_risk_students_count,
        "high_risk_count": high_risk_count,
        "moderate_risk_count": moderate_risk_count,
        "low_risk_count": low_risk_count,

        "assigned_classes_qs": assigned_classes_qs,
        "recent_grade_edits": recent_grade_edits,
        "at_risk_students_preview": at_risk_students_preview,

        "class_labels": json.dumps(class_labels),
        "class_grade_values": json.dumps(class_grade_values),
        "class_attendance_values": json.dumps(class_attendance_values),

        "pass_fail_labels": json.dumps(["Passed", "Failed"]),
        "pass_fail_values": json.dumps([passed_count, failed_count]),

        "grade_distribution_labels": json.dumps(grade_distribution_labels),
        "grade_distribution_values": json.dumps(grade_distribution_values),

        "risk_labels": json.dumps(["High Risk", "Moderate Risk", "Low Risk"]),
        "risk_values": json.dumps([high_risk_count, moderate_risk_count, low_risk_count]),
    }

    return render(request, "core/faculty_dashboard.html", context)


@login_required
def student_dashboard(request):
    if request.user.role != "student" or not hasattr(request.user, "student_profile"):
        return redirect("role-redirect")

    student_profile = request.user.student_profile

    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("class_section__subject", "class_section")
        .order_by("class_section__subject__code")
    )

    total_enrollments = enrollments.count()

    grades_qs = Grade.objects.filter(enrollment__student=student_profile)
    attendance_qs = AttendanceSummary.objects.filter(enrollment__student=student_profile)

    average_grade = grades_qs.aggregate(avg=Avg("final_grade")).get("avg")
    average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

    passed_count = grades_qs.filter(remarks="Passed").count()
    failed_count = grades_qs.filter(remarks="Failed").count()

    high_risk_count = 0
    moderate_risk_count = 0

    rows = []
    chart_labels = []
    chart_values = []

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        subject_label = f"{enrollment.class_section.subject.code}"

        if grade:
            chart_labels.append(subject_label)
            chart_values.append(float(grade.final_grade))

        is_high_risk = False
        is_moderate_risk = False

        if grade and grade.final_grade < 75:
            is_high_risk = True

        if attendance and attendance.attendance_percent < 75:
            is_high_risk = True

        if not is_high_risk:
            if grade and grade.final_grade < 80:
                is_moderate_risk = True

            if attendance and attendance.attendance_percent < 85:
                is_moderate_risk = True

        if is_high_risk:
            high_risk_count += 1
            subject_risk = "High Risk"
        elif is_moderate_risk:
            moderate_risk_count += 1
            subject_risk = "Moderate Risk"
        else:
            subject_risk = "Low Risk"

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "subject_risk": subject_risk,
        })

    if total_enrollments == 0:
        risk_level = "No Data"
        risk_badge_class = "secondary"
        advisory_message = "No enrolled subjects are currently available for this student."
    elif high_risk_count > 0:
        risk_level = "High Risk"
        risk_badge_class = "danger"
        advisory_message = "Immediate academic monitoring is recommended because one or more subjects show low grade performance or critical attendance."
    elif moderate_risk_count > 0:
        risk_level = "Moderate Risk"
        risk_badge_class = "warning"
        advisory_message = "The student is currently stable but requires continued monitoring due to borderline grade or attendance indicators."
    else:
        risk_level = "Low Risk"
        risk_badge_class = "success"
        advisory_message = "The student is currently within acceptable academic standing based on available grade and attendance records."

    forms = [
        {
            "title": "Student Certification Request Form",
            "description": "Request official student certification or academic standing document.",
        },
        {
            "title": "Grade Verification Form",
            "description": "Request review or verification of encoded academic grades.",
        },
        {
            "title": "Attendance Concern Form",
            "description": "Submit attendance-related concerns for review.",
        },
    ]

    context = {
        "page_title": "Student Dashboard",
        "enrolled_subjects": total_enrollments,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "risk_level": risk_level,
        "risk_badge_class": risk_badge_class,
        "advisory_message": advisory_message,
        "rows": rows,
        "forms": forms,
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
    }

    return render(request, "core/student_dashboard.html", context)

@login_required
def student_forms_placeholder(request):
    if request.user.role != "student":
        return redirect("role-redirect")

    forms = [
        {
            "title": "Student Certification Request Form",
            "description": "Request official student certification or academic standing document.",
        },
        {
            "title": "Grade Verification Form",
            "description": "Request review or verification of encoded academic grades.",
        },
        {
            "title": "Attendance Concern Form",
            "description": "Submit attendance-related concerns for review.",
        },
        {
            "title": "General Academic Request Form",
            "description": "Submit general academic requests for processing.",
        },
    ]

    return render(
        request,
        "core/student_forms_placeholder.html",
        {
            "page_title": "Student Forms",
            "forms": forms,
        }
    )


@login_required
def unified_access_portal(request):
    context = {
        "page_title": "Unified Access Portal",
    }
    return render(request, "core/unified_access.html", context)