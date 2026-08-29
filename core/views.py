import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from django.db.models import Avg, Count, Q
from academics.models import (ClassSection, 
                              Enrollment, 
                              Grade, 
                              GradeAdjustmentLog, 
                              AttendanceSummary, 
                              Department, 
                              FacultyProfile,
                              StudentProfile)
from analytics_app.analytics_utils import (
    export_csv_response,
    get_admin_at_risk_students,
    get_class_health_scores,
    get_department_health_scores,
    get_department_risk_ranking,
    get_faculty_submission_progress,
    get_near_passing_students,
    get_priority_ranked_students,
    get_progress_trend,
    get_recommended_learning_materials,
    get_recommended_action,
    get_risk_cause_summary,
    get_risk_reason_breakdown,
    get_risk_explanation,
    get_subject_priority_ranking,
    get_top_sections_needing_attention,
)
from evaluations.models import FacultyEvaluation


ADMIN_DASHBOARD_ROLES = {"admin", "dean", "function_head"}


def home(request):
    if request.user.is_authenticated:
        return redirect("role-redirect")
    return redirect("login")


@login_required
def role_redirect_view(request):
    user = request.user

    if user.role in ADMIN_DASHBOARD_ROLES:
        return redirect("admin-dashboard")
    elif user.role == "faculty":
        return redirect("faculty-dashboard")
    elif user.role == "student":
        return redirect("student-dashboard")
    return redirect("login")


@login_required
def admin_dashboard(request):
    if request.user.role not in ADMIN_DASHBOARD_ROLES:
        return redirect("role-redirect")

    total_departments = Department.objects.count()
    total_faculty = FacultyProfile.objects.count()
    total_students_system = StudentProfile.objects.count()

    departments = (
        Department.objects
        .annotate(
            avg_final_grade=Avg("subjects__class_sections__enrollments__grade__final_grade"),
            avg_attendance=Avg("subjects__class_sections__enrollments__attendance_summary__attendance_percent"),
            total_students=Count("subjects__class_sections__enrollments__student", distinct=True),
            total_class_sections=Count("subjects__class_sections", distinct=True),
        )
        .order_by("code")
    )

    department_performance = []
    department_chart_labels = []
    department_grade_averages = []
    department_attendance_averages = []

    for department in departments:
        grade_average = (
            float(department.avg_final_grade)
            if department.avg_final_grade is not None
            else None
        )
        attendance_average = (
            float(department.avg_attendance)
            if department.avg_attendance is not None
            else None
        )

        department_performance.append({
            "department": department,
            "total_students": department.total_students,
            "total_class_sections": department.total_class_sections,
            "avg_final_grade": grade_average,
            "avg_attendance": attendance_average,
            "has_grade_data": department.avg_final_grade is not None,
            "has_attendance_data": department.avg_attendance is not None,
        })
        department_chart_labels.append(department.code)
        department_grade_averages.append(grade_average)
        department_attendance_averages.append(attendance_average)

    # Backward-compatible chart values for older dashboard snippets.
    department_chart_values = [
        value if value is not None else 0
        for value in department_grade_averages
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

    attendance_trend_labels = department_chart_labels
    attendance_trend_values = [
        value if value is not None else 0
        for value in department_attendance_averages
    ]

    # Pass / fail summary
    passed_count = Grade.objects.filter(remarks="Passed").count()
    failed_count = Grade.objects.filter(remarks="Failed").count()

    pass_fail_labels = ["Passed", "Failed"]
    pass_fail_values = [passed_count, failed_count]

    # Faculty submission progress across all assigned class sections.
    faculty_submission_progress = []
    faculty_qs = (
        FacultyProfile.objects
        .select_related("user", "department")
        .annotate(
            expected_grade_records=Count("classes_handled__enrollments", distinct=True),
            encoded_grade_records=Count("classes_handled__enrollments__grade", distinct=True),
        )
        .order_by("employee_id")
    )

    for faculty in faculty_qs:
        expected_records = faculty.expected_grade_records
        encoded_records = faculty.encoded_grade_records
        pending_records = max(expected_records - encoded_records, 0)
        completion_percent = 0
        if expected_records > 0:
            completion_percent = round((encoded_records / expected_records) * 100, 2)

        if completion_percent == 100:
            completion_status = "Complete"
            completion_badge = "success"
        elif completion_percent > 0:
            completion_status = "In Progress"
            completion_badge = "warning"
        else:
            completion_status = "Not Started"
            completion_badge = "secondary"

        faculty_submission_progress.append({
            "faculty": faculty,
            "faculty_name": faculty.user.get_full_name() or faculty.user.username,
            "department": faculty.department,
            "department_code": faculty.department.code if faculty.department else "-",
            "expected_grade_records": expected_records,
            "encoded_grade_records": encoded_records,
            "pending_records": pending_records,
            "completion_percent": completion_percent,
            "completion_status": completion_status,
            "completion_badge": completion_badge,
        })

    faculty_progress = [
        {
            "faculty": row["faculty"],
            "total_records": row["expected_grade_records"],
            "graded_records": row["encoded_grade_records"],
            "progress_percent": row["completion_percent"],
            "progress_status": row["completion_status"],
        }
        for row in faculty_submission_progress
    ]

    faculty_progress_labels = [
        row["faculty_name"]
        for row in faculty_submission_progress
    ]

    faculty_progress_values = [
        row["completion_percent"]
        for row in faculty_submission_progress
    ]

    grades_by_enrollment = {
        grade.enrollment_id: grade
        for grade in Grade.objects.select_related("enrollment")
    }
    attendance_by_enrollment = {
        attendance.enrollment_id: attendance
        for attendance in AttendanceSummary.objects.select_related("enrollment")
    }

    student_risk = {}
    enrollments = (
        Enrollment.objects
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject__department",
        )
        .order_by(
            "student__student_number",
            "class_section__subject__code",
            "class_section__section_name",
        )
    )

    for enrollment in enrollments:
        grade = grades_by_enrollment.get(enrollment.id)
        attendance = attendance_by_enrollment.get(enrollment.id)

        risk_rank = 1
        risk_status = "Low Risk"
        risk_badge = "success"
        reasons = []

        if not grade and not attendance:
            risk_rank = 0
            risk_status = "No Data"
            risk_badge = "secondary"
            reasons.append("No grade or attendance summary has been encoded yet.")
        else:
            if grade and grade.final_grade < 75:
                reasons.append("Final grade is below the passing threshold.")

            if attendance and attendance.attendance_percent < 75:
                reasons.append("Attendance is below the critical threshold.")

            if reasons:
                risk_rank = 3
                risk_status = "High Risk"
                risk_badge = "danger"
            else:
                if grade and grade.final_grade < 80:
                    reasons.append("Final grade is near the minimum threshold.")

                if attendance and attendance.attendance_percent < 85:
                    reasons.append("Attendance requires continued monitoring.")

                if reasons:
                    risk_rank = 2
                    risk_status = "Moderate Risk"
                    risk_badge = "warning"
                else:
                    reasons.append("Available grade and attendance indicators are acceptable.")

        grade_value = float(grade.final_grade) if grade else None
        attendance_value = float(attendance.attendance_percent) if attendance else None
        lowest_available_value = min(
            value for value in [grade_value, attendance_value]
            if value is not None
        ) if grade or attendance else 100

        student_name = enrollment.student.user.get_full_name() or enrollment.student.user.username
        student_department = enrollment.student.department
        subject = enrollment.class_section.subject

        risk_row = {
            "student": enrollment.student,
            "student_name": student_name,
            "department": student_department,
            "department_code": student_department.code if student_department else "-",
            "class_section": enrollment.class_section,
            "class_subject": f"{enrollment.class_section.section_name} / {subject.code} - {subject.title}",
            "subject": subject,
            "final_grade": grade.final_grade if grade else None,
            "attendance_percent": attendance.attendance_percent if attendance else None,
            "has_grade": grade is not None,
            "has_attendance": attendance is not None,
            "risk_status": risk_status,
            "risk_badge": risk_badge,
            "risk_rank": risk_rank,
            "reason": " ".join(reasons),
            "recommended_action": get_recommended_action(
                grade.final_grade if grade else None,
                attendance.attendance_percent if attendance else None,
                risk_status,
            ),
            "lowest_available_value": lowest_available_value,
        }

        student_id = enrollment.student_id
        current_row = student_risk.get(student_id)
        if (
            current_row is None
            or risk_row["risk_rank"] > current_row["risk_rank"]
            or (
                risk_row["risk_rank"] == current_row["risk_rank"]
                and risk_row["lowest_available_value"] < current_row["lowest_available_value"]
            )
        ):
            student_risk[student_id] = risk_row

    total_high_risk = sum(
        1 for item in student_risk.values()
        if item["risk_status"] == "High Risk"
    )
    total_moderate_risk = sum(
        1 for item in student_risk.values()
        if item["risk_status"] == "Moderate Risk"
    )
    total_low_risk = sum(
        1 for item in student_risk.values()
        if item["risk_status"] == "Low Risk"
    )
    total_no_data = sum(
        1 for item in student_risk.values()
        if item["risk_status"] == "No Data"
    )

    admin_at_risk_students = sorted(
        [
            item for item in student_risk.values()
            if item["risk_status"] in ["High Risk", "Moderate Risk"]
        ],
        key=lambda item: (-item["risk_rank"], item["department_code"], item["student_name"])
    )

    at_risk_students_count = total_high_risk + total_moderate_risk
    at_risk_students_preview = admin_at_risk_students[:8]

    at_risk_labels = ["High Risk", "Moderate Risk", "Low Risk"]
    at_risk_values = [total_high_risk, total_moderate_risk, total_low_risk]

    total_expected_grade_records = sum(
        row["expected_grade_records"]
        for row in faculty_submission_progress
    )
    total_pending_grade_records = sum(
        row["pending_records"]
        for row in faculty_submission_progress
    )
    total_encoded_grade_records = total_expected_grade_records - total_pending_grade_records
    admin_submission_progress_percent = 0
    if total_expected_grade_records > 0:
        admin_submission_progress_percent = round(
            (
                total_encoded_grade_records / total_expected_grade_records
            ) * 100,
            2
        )

    department_risk_ranking = get_department_risk_ranking()
    highest_risk_department = department_risk_ranking[0] if department_risk_ranking else None

    if highest_risk_department is None:
        highest_risk_department_reason = "No department risk data is available yet."
    elif highest_risk_department["high_risk_count"] > 0:
        highest_risk_department_reason = (
            f"{highest_risk_department['department_code']} has the highest priority with "
            f"{highest_risk_department['high_risk_count']} high-risk student(s)."
        )
    elif highest_risk_department["moderate_risk_count"] > 0:
        highest_risk_department_reason = (
            f"{highest_risk_department['department_code']} needs monitoring with "
            f"{highest_risk_department['moderate_risk_count']} moderate-risk student(s)."
        )
    elif highest_risk_department["total_students"] == 0:
        highest_risk_department_reason = "No department has enough encoded student data for risk ranking yet."
    else:
        highest_risk_department_reason = (
            f"{highest_risk_department['department_code']} is currently the top ranked department, "
            "but no high-risk or moderate-risk students were detected."
        )

    department_health_scores = get_department_health_scores(department_risk_ranking)
    department_health_values = [
        row["department_health_score"]
        for row in department_health_scores
        if row.get("department_health_score") is not None
    ]
    overall_department_health_score = None
    if department_health_values:
        overall_department_health_score = round(
            float(sum(department_health_values) / len(department_health_values)),
            2
        )

    if overall_department_health_score is None:
        overall_department_health_status = "No Data"
        overall_department_health_badge_class = "secondary"
    elif overall_department_health_score >= 90:
        overall_department_health_status = "Excellent Standing"
        overall_department_health_badge_class = "success"
    elif overall_department_health_score >= 80:
        overall_department_health_status = "Good Standing"
        overall_department_health_badge_class = "primary"
    elif overall_department_health_score >= 75:
        overall_department_health_status = "Needs Monitoring"
        overall_department_health_badge_class = "warning"
    else:
        overall_department_health_status = "Critical"
        overall_department_health_badge_class = "danger"

    risk_cause_summary = get_risk_cause_summary()
    risk_cause_labels = list(risk_cause_summary.keys())
    risk_cause_data = list(risk_cause_summary.values())
    risk_cause_counts = [
        (label, count)
        for label, count in risk_cause_summary.items()
        if count > 0
    ]
    most_common_risk_cause = (
        max(risk_cause_counts, key=lambda item: item[1])[0]
        if risk_cause_counts
        else "No Data"
    )

    top_sections_needing_attention = get_top_sections_needing_attention()

    if total_high_risk > 0:
        admin_dashboard_insight = (
            f"{total_high_risk} high-risk student(s) need immediate review. "
            f"{total_pending_grade_records} expected grade record(s) are still pending."
        )
        admin_recommended_action = (
            "Prioritize high-risk students for adviser follow-up and remind faculty with pending grade records to complete submissions."
        )
    elif total_moderate_risk > 0:
        admin_dashboard_insight = (
            f"{total_moderate_risk} student(s) show moderate risk indicators. "
            f"{total_low_risk} student(s) are currently low risk based on available records."
        )
        admin_recommended_action = (
            "Monitor moderate-risk students and review departments or faculty with incomplete grade submissions."
        )
    elif total_expected_grade_records == 0:
        admin_dashboard_insight = (
            "No expected grade records are available yet because no enrolled class records were found."
        )
        admin_recommended_action = (
            "Verify that class sections and enrollments are encoded before using the dashboard for intervention planning."
        )
    elif total_pending_grade_records > 0:
        admin_dashboard_insight = (
            f"No high or moderate student risk is currently detected, but {total_pending_grade_records} grade record(s) remain pending."
        )
        admin_recommended_action = (
            "Follow up on pending grade submissions so the risk analytics can reflect complete academic records."
        )
    else:
        admin_dashboard_insight = (
            f"All currently evaluated students are low risk. {total_low_risk} student(s) have acceptable available indicators."
        )
        admin_recommended_action = (
            "Maintain routine monitoring and continue checking submissions after each grading update."
        )

    if total_no_data > 0:
        admin_dashboard_insight = (
            f"{admin_dashboard_insight} {total_no_data} enrolled student(s) still have no encoded grade or attendance data."
        )

    if most_common_risk_cause != "No Data":
        admin_dashboard_insight = (
            f"{admin_dashboard_insight} Most common risk cause: {most_common_risk_cause.lower()}."
        )

    if highest_risk_department_reason:
        admin_dashboard_insight = (
            f"{admin_dashboard_insight} {highest_risk_department_reason}"
        )

    if top_sections_needing_attention:
        admin_recommended_action = (
            f"{admin_recommended_action} Review the top sections needing attention and use exported reports for monitoring."
        )

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

    department_chart_labels = [
        label or "N/A"
        for label in department_chart_labels
    ]

    context = {
        "page_title": "Admin Dashboard",

        "total_departments": total_departments,
        "total_faculty": total_faculty,
        "total_students_system": total_students_system,
        "at_risk_students_count": at_risk_students_count,
        "overall_evaluation_average": overall_evaluation_average,
        "total_low_risk": total_low_risk,
        "total_moderate_risk": total_moderate_risk,
        "total_high_risk": total_high_risk,

        "department_performance": department_performance,
        "faculty_progress": faculty_progress,
        "faculty_submission_progress": faculty_submission_progress,
        "evaluation_summary": evaluation_summary[:8],
        "at_risk_students_preview": at_risk_students_preview,
        "admin_at_risk_students": admin_at_risk_students,

        "department_chart_labels": department_chart_labels,
        "department_grade_averages": department_grade_averages,
        "department_attendance_averages": department_attendance_averages,
        "department_chart_values": json.dumps(department_chart_values),

        "grade_distribution_labels": grade_distribution_labels,
        "grade_distribution_values": grade_distribution_values,

        "attendance_trend_labels": attendance_trend_labels,
        "attendance_trend_values": attendance_trend_values,

        "pass_fail_labels": pass_fail_labels,
        "pass_fail_values": pass_fail_values,

        "at_risk_labels": at_risk_labels,
        "at_risk_values": at_risk_values,

        "faculty_progress_labels": faculty_progress_labels,
        "faculty_progress_values": faculty_progress_values,
        "total_expected_grade_records": total_expected_grade_records,
        "total_encoded_grade_records": total_encoded_grade_records,
        "total_pending_grade_records": total_pending_grade_records,
        "admin_submission_progress_percent": admin_submission_progress_percent,
        "department_risk_ranking": department_risk_ranking,
        "highest_risk_department": highest_risk_department,
        "highest_risk_department_reason": highest_risk_department_reason,
        "department_health_scores": department_health_scores,
        "overall_department_health_score": overall_department_health_score,
        "overall_department_health_status": overall_department_health_status,
        "overall_department_health_badge_class": overall_department_health_badge_class,
        "risk_cause_summary": risk_cause_summary,
        "risk_cause_labels": risk_cause_labels,
        "risk_cause_data": risk_cause_data,
        "most_common_risk_cause": most_common_risk_cause,
        "top_sections_needing_attention": top_sections_needing_attention,
        "export_at_risk_url": reverse("admin-dashboard-export-at-risk"),
        "export_faculty_submission_url": reverse("admin-dashboard-export-faculty-submission"),
        "export_department_risk_url": reverse("admin-dashboard-export-department-risk"),
        "export_top_sections_url": reverse("admin-dashboard-export-top-sections"),

        "admin_dashboard_insight": admin_dashboard_insight,
        "admin_recommended_action": admin_recommended_action,
    }

    return render(request, "core/admin_dashboard.html", context)


def _format_report_decimal(value):
    if value is None:
        return "No Data"

    return f"{float(value):.2f}"


def _admin_report_department_label(row):
    code = row.get("department_code") or "Unassigned"
    name = row.get("department_name") or "Unassigned Department"

    if code == name:
        return code

    return f"{code} - {name}"


def _admin_report_allowed(request):
    return request.user.role in ADMIN_DASHBOARD_ROLES


@login_required
def admin_export_at_risk_report(request):
    if not _admin_report_allowed(request):
        return redirect("role-redirect")

    headers = [
        "Student Name",
        "Department",
        "Section/Class",
        "Subject",
        "Final Grade",
        "Attendance Percentage",
        "Risk Status",
        "Main Reason",
        "Recommended Action",
    ]
    rows = []

    for row in get_admin_at_risk_students():
        rows.append([
            row["student_name"],
            _admin_report_department_label(row),
            row["class_section_name"],
            f"{row['subject_code']} - {row['subject_title']}",
            _format_report_decimal(row["final_grade"]),
            _format_report_decimal(row["attendance_percent"]),
            row["risk_status"],
            row["reason"],
            row["recommended_action"],
        ])

    return export_csv_response(
        "admin_at_risk_student_report.csv",
        headers,
        rows,
    )


@login_required
def admin_export_faculty_submission_report(request):
    if not _admin_report_allowed(request):
        return redirect("role-redirect")

    headers = [
        "Faculty Name",
        "Department",
        "Expected Grade Records",
        "Encoded Grade Records",
        "Pending Grade Records",
        "Completion Percentage",
        "Status",
    ]
    rows = []

    for row in get_faculty_submission_progress():
        rows.append([
            row["faculty_name"],
            _admin_report_department_label(row),
            row["expected_grade_records"],
            row["encoded_grade_records"],
            row["pending_records"],
            _format_report_decimal(row["completion_percent"]),
            row["completion_status"],
        ])

    return export_csv_response(
        "admin_faculty_submission_report.csv",
        headers,
        rows,
    )


@login_required
def admin_export_department_risk_report(request):
    if not _admin_report_allowed(request):
        return redirect("role-redirect")

    headers = [
        "Rank",
        "Department",
        "Total Students",
        "Low Risk Count",
        "Moderate Risk Count",
        "High Risk Count",
        "Average Grade",
        "Average Attendance",
        "Health Score",
        "Recommended Action",
    ]
    rows = []

    for row in get_department_risk_ranking():
        rows.append([
            row["rank"],
            _admin_report_department_label(row),
            row["total_students"],
            row["low_risk_count"],
            row["moderate_risk_count"],
            row["high_risk_count"],
            _format_report_decimal(row["average_grade"]),
            _format_report_decimal(row["average_attendance"]),
            _format_report_decimal(row["department_health_score"]),
            row["recommended_action"],
        ])

    return export_csv_response(
        "admin_department_risk_ranking.csv",
        headers,
        rows,
    )


@login_required
def admin_export_top_sections_report(request):
    if not _admin_report_allowed(request):
        return redirect("role-redirect")

    headers = [
        "Rank",
        "Section/Class",
        "Subject",
        "Department",
        "Faculty",
        "Total Students",
        "High Risk Count",
        "Moderate Risk Count",
        "Average Grade",
        "Average Attendance",
        "Class Health Score",
        "Main Concern",
        "Recommended Action",
    ]
    rows = []

    for row in get_top_sections_needing_attention():
        rows.append([
            row["rank"],
            row["section_name"],
            f"{row['subject_code']} - {row['subject_title']}",
            _admin_report_department_label(row),
            row["faculty_name"],
            row["total_students"],
            row["high_risk_count"],
            row["moderate_risk_count"],
            _format_report_decimal(row["average_grade"]),
            _format_report_decimal(row["average_attendance"]),
            _format_report_decimal(row["class_health_score"]),
            row["main_concern"],
            row["recommended_action"],
        ])

    return export_csv_response(
        "admin_top_sections_needing_attention.csv",
        headers,
        rows,
    )


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
            encoded_grade_records=Count("enrollments__grade"),
            avg_grade=Avg("enrollments__grade__final_grade"),
            avg_attendance=Avg("enrollments__attendance_summary__attendance_percent"),
        )
        .order_by("school_year", "term", "section_name")
    )

    assigned_classes = assigned_classes_qs.count()
    assigned_classes_list = list(assigned_classes_qs)

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

    for class_item in assigned_classes_list:
        class_labels.append(f"{class_item.subject.code} - {class_item.section_name}")
        class_grade_values.append(float(class_item.avg_grade) if class_item.avg_grade is not None else 0)
        class_attendance_values.append(float(class_item.avg_attendance) if class_item.avg_attendance is not None else 0)
        class_item.pending_grade_records = max(class_item.total_students - class_item.encoded_grade_records, 0)
        class_item.completion_percent = 0
        if class_item.total_students > 0:
            class_item.completion_percent = round(
                (class_item.encoded_grade_records / class_item.total_students) * 100,
                2
            )
        if class_item.completion_percent == 100:
            class_item.completion_badge = "success"
        elif class_item.completion_percent > 0:
            class_item.completion_badge = "warning"
        else:
            class_item.completion_badge = "secondary"

    student_risk = {}

    enrollments = (
        Enrollment.objects
        .filter(class_section__faculty=faculty_profile)
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject",
            "grade",
            "attendance_summary",
        )
    )
    enrollments = list(enrollments)

    for enrollment in enrollments:
        try:
            grade = enrollment.grade
        except Grade.DoesNotExist:
            grade = None

        try:
            attendance = enrollment.attendance_summary
        except AttendanceSummary.DoesNotExist:
            attendance = None

        risk_rank = 0
        risk_level = "No Data"
        reason = "No grade or attendance summary has been encoded yet."

        if grade or attendance:
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
    no_data_count = sum(1 for item in student_risk.values() if item["risk_level"] == "No Data")

    at_risk_students_count = high_risk_count + moderate_risk_count

    at_risk_students_preview = [
        item for item in student_risk.values()
        if item["risk_level"] in ["High Risk", "Moderate Risk"]
    ][:8]

    risk_reason_breakdown = get_risk_reason_breakdown(enrollments)
    risk_reason_labels = list(risk_reason_breakdown.keys())
    risk_reason_data = list(risk_reason_breakdown.values())

    priority_at_risk_students = get_priority_ranked_students(enrollments)

    class_health_scores = get_class_health_scores(assigned_classes_list)
    class_health_values = [
        row["health_score"]
        for row in class_health_scores
        if row.get("health_score") is not None
    ]
    overall_class_health_score = None
    if class_health_values:
        overall_class_health_score = round(
            float(sum(class_health_values) / len(class_health_values)),
            2
        )

    if overall_class_health_score is None:
        overall_class_health_status = "No Data"
        overall_class_health_badge_class = "secondary"
    elif overall_class_health_score >= 90:
        overall_class_health_status = "Excellent Standing"
        overall_class_health_badge_class = "success"
    elif overall_class_health_score >= 80:
        overall_class_health_status = "Good Standing"
        overall_class_health_badge_class = "primary"
    elif overall_class_health_score >= 75:
        overall_class_health_status = "Needs Monitoring"
        overall_class_health_badge_class = "warning"
    else:
        overall_class_health_status = "Critical"
        overall_class_health_badge_class = "danger"

    near_passing_students = get_near_passing_students(enrollments)
    near_passing_count = len(near_passing_students)

    if high_risk_count > 0:
        faculty_dashboard_insight = (
            f"{high_risk_count} assigned student(s) need immediate attention. "
            f"{total_records - graded_records} grade record(s) are still pending."
        )
        faculty_recommended_action = "Review the at-risk list, contact the affected students, and complete pending grade records."
    elif moderate_risk_count > 0:
        faculty_dashboard_insight = (
            f"{moderate_risk_count} assigned student(s) show moderate risk indicators across your classes."
        )
        faculty_recommended_action = "Monitor borderline grades and attendance before they become high-risk cases."
    elif total_records == 0:
        faculty_dashboard_insight = "No assigned student records are available yet for dashboard analytics."
        faculty_recommended_action = "Check assigned classes and enrollments before preparing intervention reports."
    elif graded_records < total_records:
        faculty_dashboard_insight = (
            f"No student risk is currently detected, but {total_records - graded_records} grade record(s) remain pending."
        )
        faculty_recommended_action = "Complete grade submissions so the dashboard reflects full class performance."
    else:
        faculty_dashboard_insight = "Assigned students are currently low risk based on available grade and attendance records."
        faculty_recommended_action = "Maintain routine monitoring and continue encoding updates on time."

    if no_data_count > 0:
        faculty_dashboard_insight = (
            f"{faculty_dashboard_insight} {no_data_count} assigned student(s) still have no grade or attendance data."
        )

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
        "no_data_count": no_data_count,
        "faculty_dashboard_insight": faculty_dashboard_insight,
        "faculty_recommended_action": faculty_recommended_action,

        "assigned_classes_qs": assigned_classes_list,
        "recent_grade_edits": recent_grade_edits,
        "at_risk_students_preview": at_risk_students_preview,
        "risk_reason_breakdown": risk_reason_breakdown,
        "risk_reason_labels": risk_reason_labels,
        "risk_reason_data": risk_reason_data,
        "priority_at_risk_students": priority_at_risk_students,
        "overall_class_health_score": overall_class_health_score,
        "overall_class_health_status": overall_class_health_status,
        "overall_class_health_badge_class": overall_class_health_badge_class,
        "class_health_scores": class_health_scores,
        "near_passing_students": near_passing_students,
        "near_passing_count": near_passing_count,

        "class_labels": class_labels,
        "class_grade_values": class_grade_values,
        "class_attendance_values": class_attendance_values,

        "pass_fail_labels": ["Passed", "Failed"],
        "pass_fail_values": [passed_count, failed_count],

        "grade_distribution_labels": grade_distribution_labels,
        "grade_distribution_values": grade_distribution_values,

        "risk_labels": ["High Risk", "Moderate Risk", "Low Risk"],
        "risk_values": [high_risk_count, moderate_risk_count, low_risk_count],
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
        .select_related(
            "class_section__subject",
            "class_section",
            "grade",
            "attendance_summary",
        )
        .order_by("class_section__subject__code")
    )
    enrollments = list(enrollments)

    total_enrollments = len(enrollments)

    grades_qs = Grade.objects.filter(enrollment__student=student_profile)
    attendance_qs = AttendanceSummary.objects.filter(enrollment__student=student_profile)

    average_grade = grades_qs.aggregate(avg=Avg("final_grade")).get("avg")
    average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

    passed_count = grades_qs.filter(remarks="Passed").count()
    failed_count = grades_qs.filter(remarks="Failed").count()

    high_risk_count = 0
    moderate_risk_count = 0
    low_risk_count = 0
    no_data_count = 0
    has_academic_data = False

    rows = []
    grade_chart_labels = []
    grade_chart_data = []
    attendance_chart_data = []
    attention_candidates = []

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        subject = enrollment.class_section.subject
        subject_label = f"{subject.code} - {enrollment.class_section.section_name}"
        grade_value = float(grade.final_grade) if grade else None
        attendance_value = float(attendance.attendance_percent) if attendance else None

        grade_chart_labels.append(subject_label)
        grade_chart_data.append(grade_value)
        attendance_chart_data.append(attendance_value)

        if grade or attendance:
            has_academic_data = True

        if grade and grade.final_grade < 75:
            subject_risk = "High Risk"
        elif attendance and attendance.attendance_percent < 75:
            subject_risk = "High Risk"
        elif grade and grade.final_grade < 80:
            subject_risk = "Moderate Risk"
        elif attendance and attendance.attendance_percent < 85:
            subject_risk = "Moderate Risk"
        elif not grade and not attendance:
            subject_risk = "No Data"
        else:
            subject_risk = "Low Risk"

        if subject_risk == "High Risk":
            high_risk_count += 1
            subject_risk_badge = "danger"
        elif subject_risk == "Moderate Risk":
            moderate_risk_count += 1
            subject_risk_badge = "warning"
        elif subject_risk == "No Data":
            no_data_count += 1
            subject_risk_badge = "secondary"
        else:
            low_risk_count += 1
            subject_risk_badge = "success"

        if grade or attendance:
            lowest_available_value = min(
                value for value in [grade_value, attendance_value]
                if value is not None
            )
            attention_candidates.append({
                "subject_code": subject.code,
                "subject_title": subject.title,
                "section_name": enrollment.class_section.section_name,
                "grade": grade_value,
                "attendance": attendance_value,
                "has_grade": grade is not None,
                "has_attendance": attendance is not None,
                "risk_status": subject_risk,
                "risk_rank": {
                    "High Risk": 3,
                    "Moderate Risk": 2,
                    "Low Risk": 1,
                    "No Data": 0,
                }[subject_risk],
                "lowest_available_value": lowest_available_value,
            })

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "subject_risk": subject_risk,
            "subject_risk_badge": subject_risk_badge,
        })

    weakest_subject = None
    if attention_candidates:
        weakest_subject = sorted(
            attention_candidates,
            key=lambda item: (-item["risk_rank"], item["lowest_available_value"])
        )[0]

    subject_priority_ranking = get_subject_priority_ranking(enrollments)
    priority_subject = subject_priority_ranking[0] if subject_priority_ranking else None

    if priority_subject:
        risk_explanation = get_risk_explanation(
            priority_subject.get("final_grade"),
            priority_subject.get("attendance_percentage"),
        )
    else:
        risk_explanation = "No risk explanation is available because no enrolled subjects were found."

    material_recommendation = get_recommended_learning_materials(
        student_profile,
        priority_subject or weakest_subject,
    )
    recommended_materials = material_recommendation.get("materials", [])
    recommended_material_message = material_recommendation.get("message", "")
    if not recommended_material_message and priority_subject:
        recommended_material_message = (
            f"Recommended materials for {priority_subject.get('subject_code', 'the priority subject')}."
        )

    progress_trend_label = get_progress_trend(enrollments)
    progress_trend_descriptions = {
        "Improving": "Your current records show strong performance across enrolled subjects.",
        "Stable": "Your current records are generally acceptable based on available grades and attendance.",
        "Needs Monitoring": "One or more subjects are near the risk threshold and should be monitored closely.",
        "Declining": "One or more subjects show high-risk grade or attendance indicators.",
    }
    progress_trend_badges = {
        "Improving": "success",
        "Stable": "primary",
        "Needs Monitoring": "warning",
        "Declining": "danger",
        "No Data": "secondary",
    }
    progress_trend_description = progress_trend_descriptions.get(
        progress_trend_label,
        "Progress trend cannot be determined from the available records.",
    )
    progress_trend_badge_class = progress_trend_badges.get(progress_trend_label, "secondary")

    if total_enrollments == 0 or not has_academic_data:
        student_risk_status = "No Data"
        student_risk_reason = "No enrolled subjects with encoded grade or attendance records are available yet."
        student_recommended_action = "Check back after your faculty encode grades and attendance summaries."
        dashboard_insight = "Academic analytics will appear once your enrolled subjects have grade or attendance data."
        risk_badge_class = "secondary"
    elif high_risk_count > 0:
        student_risk_status = "High Risk"
        student_risk_reason = "At least one enrolled subject has a final grade below 75 or attendance below 75%."
        student_recommended_action = "Prioritize the subject needing attention and consult your instructor or adviser as soon as possible."
        dashboard_insight = "Immediate monitoring is recommended because one or more subjects show critical grade or attendance indicators."
        risk_badge_class = "danger"
    elif moderate_risk_count > 0:
        student_risk_status = "Moderate Risk"
        student_risk_reason = "One or more enrolled subjects are near the risk threshold: grade below 80 or attendance below 85%."
        student_recommended_action = "Review your weakest subject, keep attendance consistent, and address borderline scores before they drop further."
        dashboard_insight = "You are currently stable, but at least one subject needs continued attention."
        risk_badge_class = "warning"
    else:
        student_risk_status = "Low Risk"
        student_risk_reason = "All available grade and attendance records are within acceptable thresholds."
        student_recommended_action = "Maintain your current study routine and keep attendance strong across all enrolled subjects."
        dashboard_insight = "Your current records show acceptable academic standing across available subjects."
        risk_badge_class = "success"

    if weakest_subject:
        grade_display = f"{weakest_subject['grade']:.2f}" if weakest_subject["has_grade"] else "not encoded"
        attendance_display = f"{weakest_subject['attendance']:.2f}%" if weakest_subject["has_attendance"] else "not encoded"
        dashboard_insight = (
            f"{dashboard_insight} Subject needing attention: "
            f"{weakest_subject['subject_code']} - {weakest_subject['subject_title']} "
            f"has a final grade of {grade_display} and attendance of {attendance_display}."
        )

    student_at_risk_rows = [
        row for row in rows
        if row["subject_risk"] in ["High Risk", "Moderate Risk"]
    ]

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
        "risk_level": student_risk_status,
        "risk_badge_class": risk_badge_class,
        "advisory_message": student_recommended_action,
        "student_risk_status": student_risk_status,
        "student_risk_reason": student_risk_reason,
        "student_recommended_action": student_recommended_action,
        "student_low_risk_count": low_risk_count,
        "student_moderate_risk_count": moderate_risk_count,
        "student_high_risk_count": high_risk_count,
        "student_no_data_count": no_data_count,
        "grade_chart_labels": grade_chart_labels,
        "grade_chart_data": grade_chart_data,
        "attendance_chart_data": attendance_chart_data,
        "weakest_subject": weakest_subject,
        "dashboard_insight": dashboard_insight,
        "student_at_risk_rows": student_at_risk_rows,
        "subject_priority_ranking": subject_priority_ranking,
        "risk_explanation": risk_explanation,
        "recommended_materials": recommended_materials,
        "recommended_material_message": recommended_material_message,
        "progress_trend_label": progress_trend_label,
        "progress_trend_description": progress_trend_description,
        "progress_trend_badge_class": progress_trend_badge_class,
        "priority_subject": priority_subject,
        "rows": rows,
        "forms": forms,
        "chart_labels": json.dumps(grade_chart_labels),
        "chart_values": json.dumps(grade_chart_data),
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
