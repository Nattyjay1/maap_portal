import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Avg

from evaluations.models import FacultyEvaluation
from .forms import GradeEditForm
from .models import (ClassSection, 
                     Enrollment, 
                     Grade, 
                     GradeAdjustmentLog, 
                     AttendanceSummary,
                     Department,
                     FacultyProfile,
                     StudentProfile,
                     AdvisorySection,)     


def _faculty_check(request):
    if request.user.role != "faculty":
        return False
    if not hasattr(request.user, "faculty_profile"):
        return False
    return True


def _student_risk_from_records(grade_qs, attendance_qs):
    risk_level = "Low Risk"
    risk_badge = "success"
    advisory = "Student is currently within acceptable academic standing based on available records."

    if grade_qs.filter(final_grade__lt=75).exists():
        risk_level = "High Risk"
        risk_badge = "danger"
        advisory = "Immediate academic monitoring is recommended because one or more grades are below the passing threshold."
    elif attendance_qs.filter(attendance_percent__lt=75).exists():
        risk_level = "High Risk"
        risk_badge = "danger"
        advisory = "Immediate academic monitoring is recommended because attendance is below the critical threshold."
    elif grade_qs.filter(final_grade__lt=80).exists():
        risk_level = "Moderate Risk"
        risk_badge = "warning"
        advisory = "Continued monitoring is recommended because one or more grades are near the minimum threshold."
    elif attendance_qs.filter(attendance_percent__lt=85).exists():
        risk_level = "Moderate Risk"
        risk_badge = "warning"
        advisory = "Attendance is acceptable but should be monitored to avoid academic risk."

    return risk_level, risk_badge, advisory


def _to_decimal(value, default="0"):
    try:
        return Decimal(value if value not in [None, ""] else default)
    except (InvalidOperation, TypeError):
        return Decimal(default)
    
    
def _student_check(request):
    if request.user.role != "student":
        return False
    if not hasattr(request.user, "student_profile"):
        return False
    return True


def _to_int(value, default=0):
    try:
        value = int(value if value not in [None, ""] else default)
        return max(value, 0)
    except (TypeError, ValueError):
        return default
    
    
def _get_student_risk_for_advisory(grade_qs, attendance_qs):
    risk_level = "Low Risk"
    risk_badge = "success"
    advisory = "Student is currently within acceptable academic standing based on available records."

    if grade_qs.filter(final_grade__lt=75).exists():
        risk_level = "High Risk"
        risk_badge = "danger"
        advisory = "Immediate academic monitoring is recommended because one or more grades are below the passing threshold."
    elif attendance_qs.filter(attendance_percent__lt=75).exists():
        risk_level = "High Risk"
        risk_badge = "danger"
        advisory = "Immediate academic monitoring is recommended because attendance is below the critical threshold."
    elif grade_qs.filter(final_grade__lt=80).exists():
        risk_level = "Moderate Risk"
        risk_badge = "warning"
        advisory = "Continued monitoring is recommended because one or more grades are near the minimum threshold."
    elif attendance_qs.filter(attendance_percent__lt=85).exists():
        risk_level = "Moderate Risk"
        risk_badge = "warning"
        advisory = "Attendance is acceptable but should be monitored to avoid academic risk."

    return risk_level, risk_badge, advisory


@login_required
def faculty_class_list(request):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access the faculty grade module.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    classes = (
        ClassSection.objects
        .filter(faculty=faculty_profile)
        .select_related("subject")
        .annotate(total_students=Count("enrollments"))
        .order_by("school_year", "term", "section_name")
    )

    context = {
        "page_title": "My Classes",
        "classes": classes,
    }
    return render(request, "academics/faculty_class_list.html", context)


@login_required
def enrolled_student_list(request, class_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    class_section = get_object_or_404(
        ClassSection.objects.select_related("subject", "faculty__user"),
        id=class_id,
        faculty=faculty_profile,
    )

    enrollments = (
        Enrollment.objects
        .filter(class_section=class_section)
        .select_related("student__user", "class_section")
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

    context = {
        "page_title": "Enrolled Students",
        "class_section": class_section,
        "rows": rows,
    }
    return render(request, "academics/enrolled_student_list.html", context)


@login_required
def class_grade_entry(request, class_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    class_section = get_object_or_404(
        ClassSection.objects.select_related("subject", "faculty__user"),
        id=class_id,
        faculty=faculty_profile,
    )

    enrollments = list(
        Enrollment.objects
        .filter(class_section=class_section)
        .select_related("student__user", "student")
        .order_by("student__student_number")
    )

    grade_map = {
        grade.enrollment_id: grade
        for grade in Grade.objects.filter(enrollment__in=enrollments)
    }

    if request.method == "POST":
        for enrollment in enrollments:
            enrollment_id = enrollment.id

            quiz_total = _to_decimal(request.POST.get(f"quiz_total_{enrollment_id}"))
            activity_total = _to_decimal(request.POST.get(f"activity_total_{enrollment_id}"))
            exam_total = _to_decimal(request.POST.get(f"exam_total_{enrollment_id}"))
            lab_total = _to_decimal(request.POST.get(f"lab_total_{enrollment_id}"))
            attendance_score = _to_decimal(request.POST.get(f"attendance_score_{enrollment_id}"))

            grade, created = Grade.objects.get_or_create(enrollment=enrollment)
            grade.quiz_total = quiz_total
            grade.activity_total = activity_total
            grade.exam_total = exam_total
            grade.lab_total = lab_total
            grade.attendance_score = attendance_score
            grade.save()

        messages.success(request, "Grades for the class were saved successfully.")
        return redirect("enrolled-student-list", class_id=class_section.id)

    rows = []
    for enrollment in enrollments:
        grade = grade_map.get(enrollment.id)
        rows.append({
            "enrollment": enrollment,
            "grade": grade,
        })

    context = {
        "page_title": "Encode Grades",
        "class_section": class_section,
        "rows": rows,
    }
    return render(request, "academics/class_grade_entry.html", context)


@login_required
def grade_entry(request, enrollment_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            "student__user",
            "class_section__subject",
            "class_section__faculty__user"
        ),
        id=enrollment_id,
        class_section__faculty=faculty_profile,
    )

    grade_instance = Grade.objects.filter(enrollment=enrollment).first()

    if not grade_instance:
        messages.error(request, "No existing grade found. Use Encode Grades first.")
        return redirect("class-grade-entry", class_id=enrollment.class_section.id)

    tracked_fields = [
        "quiz_total",
        "activity_total",
        "exam_total",
        "lab_total",
        "attendance_score",
    ]

    original_values = {field: getattr(grade_instance, field) for field in tracked_fields}
    original_final_grade = grade_instance.final_grade
    original_remarks = grade_instance.remarks

    if request.method == "POST":
        form = GradeEditForm(request.POST, instance=grade_instance)

        if form.is_valid():
            updated_grade = form.save(commit=False)
            reason = form.cleaned_data["reason"].strip()

            changes = []
            for field in tracked_fields:
                old_value = original_values[field]
                new_value = getattr(updated_grade, field)
                if old_value != new_value:
                    changes.append((field, old_value, new_value))

            if not changes:
                messages.info(request, "No grade changes were detected.")
                return redirect("enrolled-student-list", class_id=enrollment.class_section.id)

            with transaction.atomic():
                updated_grade.save()

                for field_name, old_value, new_value in changes:
                    GradeAdjustmentLog.objects.create(
                        grade=updated_grade,
                        edited_by=request.user,
                        field_changed=field_name,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        reason=reason,
                    )

                if original_final_grade != updated_grade.final_grade:
                    GradeAdjustmentLog.objects.create(
                        grade=updated_grade,
                        edited_by=request.user,
                        field_changed="final_grade",
                        old_value=str(original_final_grade),
                        new_value=str(updated_grade.final_grade),
                        reason=reason,
                    )

                if original_remarks != updated_grade.remarks:
                    GradeAdjustmentLog.objects.create(
                        grade=updated_grade,
                        edited_by=request.user,
                        field_changed="remarks",
                        old_value=str(original_remarks),
                        new_value=str(updated_grade.remarks),
                        reason=reason,
                    )

            messages.success(request, "Grade updated successfully. Changes were logged.")
            return redirect("enrolled-student-list", class_id=enrollment.class_section.id)
    else:
        form = GradeEditForm(instance=grade_instance)

    recent_logs = grade_instance.adjustment_logs.select_related("edited_by").all()[:10]

    context = {
        "page_title": "Edit Grade",
        "enrollment": enrollment,
        "form": form,
        "computed_grade": grade_instance.final_grade,
        "remarks": grade_instance.remarks,
        "recent_logs": recent_logs,
    }
    return render(request, "academics/grade_form.html", context)


@login_required
def class_attendance_entry(request, class_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    class_section = get_object_or_404(
        ClassSection.objects.select_related("subject", "faculty__user"),
        id=class_id,
        faculty=faculty_profile,
    )

    enrollments = list(
        Enrollment.objects
        .filter(class_section=class_section)
        .select_related("student__user", "student")
        .order_by("student__student_number")
    )

    attendance_map = {
        attendance.enrollment_id: attendance
        for attendance in AttendanceSummary.objects.filter(enrollment__in=enrollments)
    }

    if request.method == "POST":
        for enrollment in enrollments:
            enrollment_id = enrollment.id

            present_count = _to_int(request.POST.get(f"present_count_{enrollment_id}"))
            absent_count = _to_int(request.POST.get(f"absent_count_{enrollment_id}"))
            late_count = _to_int(request.POST.get(f"late_count_{enrollment_id}"))

            attendance, created = AttendanceSummary.objects.get_or_create(enrollment=enrollment)
            attendance.present_count = present_count
            attendance.absent_count = absent_count
            attendance.late_count = late_count
            attendance.save()

        messages.success(request, "Attendance for the class was saved successfully.")
        return redirect("enrolled-student-list", class_id=class_section.id)

    rows = []
    for enrollment in enrollments:
        attendance = attendance_map.get(enrollment.id)
        rows.append({
            "enrollment": enrollment,
            "attendance": attendance,
        })

    class_average = (
        AttendanceSummary.objects
        .filter(enrollment__class_section=class_section)
        .aggregate(avg=Avg("attendance_percent"))
        .get("avg")
    )

    context = {
        "page_title": "Encode Attendance",
        "class_section": class_section,
        "rows": rows,
        "class_average": class_average,
    }
    return render(request, "academics/class_attendance_entry.html", context)


@login_required
def student_attendance_list(request):
    if not _student_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    student_profile = request.user.student_profile

    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("class_section__subject", "class_section")
        .order_by("class_section__subject__code")
    )

    rows = []
    for enrollment in enrollments:
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()
        rows.append({
            "enrollment": enrollment,
            "attendance": attendance,
        })

    average_attendance = (
        AttendanceSummary.objects
        .filter(enrollment__student=student_profile)
        .aggregate(avg=Avg("attendance_percent"))
        .get("avg")
    )

    context = {
        "page_title": "My Attendance",
        "rows": rows,
        "average_attendance": average_attendance,
    }
    return render(request, "academics/student_attendance_list.html", context)


@login_required
def student_grade_list(request):
    if not _student_check(request):
        messages.error(request, "You are not authorized to access this page.")
        return redirect("role-redirect")

    student_profile = request.user.student_profile

    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("class_section__subject", "class_section")
        .order_by("class_section__subject__code")
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

    average_grade = (
        Grade.objects
        .filter(enrollment__student=student_profile)
        .aggregate(avg=Avg("final_grade"))
        .get("avg")
    )

    context = {
        "page_title": "My Grades",
        "rows": rows,
        "average_grade": average_grade,
    }

    return render(request, "academics/student_grade_list.html", context)


@login_required
def admin_faculty_list(request):
    if request.user.role != "admin":
        return redirect("role-redirect")

    departments = Department.objects.all().order_by("code")
    selected_department_id = request.GET.get("department")

    faculty_qs = (
        FacultyProfile.objects
        .select_related("user", "department")
        .order_by("department__code", "employee_id")
    )

    if selected_department_id:
        faculty_qs = faculty_qs.filter(department_id=selected_department_id)

    faculty_rows = []

    for faculty in faculty_qs:
        assigned_classes = ClassSection.objects.filter(faculty=faculty).count()

        total_students = (
            Enrollment.objects
            .filter(class_section__faculty=faculty)
            .values("student")
            .distinct()
            .count()
        )

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

        average_grade = (
            Grade.objects
            .filter(enrollment__class_section__faculty=faculty)
            .aggregate(avg=Avg("final_grade"))
            .get("avg")
        )

        average_attendance = (
            AttendanceSummary.objects
            .filter(enrollment__class_section__faculty=faculty)
            .aggregate(avg=Avg("attendance_percent"))
            .get("avg")
        )

        evaluation_average = (
            FacultyEvaluation.objects
            .filter(faculty=faculty)
            .aggregate(avg=Avg("evaluation_score"))
            .get("avg")
        )

        faculty_rows.append({
            "faculty": faculty,
            "assigned_classes": assigned_classes,
            "total_students": total_students,
            "total_records": total_records,
            "graded_records": graded_records,
            "progress_percent": progress_percent,
            "progress_status": progress_status,
            "average_grade": average_grade,
            "average_attendance": average_attendance,
            "evaluation_average": evaluation_average,
        })

    context = {
        "page_title": "Faculty Monitoring",
        "departments": departments,
        "selected_department_id": selected_department_id,
        "faculty_rows": faculty_rows,
    }

    return render(request, "academics/admin_faculty_list.html", context)


@login_required
def admin_faculty_analytics(request, faculty_id):
    if request.user.role != "admin":
        return redirect("role-redirect")

    faculty = get_object_or_404(
        FacultyProfile.objects.select_related("user", "department"),
        id=faculty_id
    )

    assigned_classes_qs = (
        ClassSection.objects
        .filter(faculty=faculty)
        .select_related("subject")
        .annotate(
            total_students=Count("enrollments"),
            avg_grade=Avg("enrollments__grade__final_grade"),
            avg_attendance=Avg("enrollments__attendance_summary__attendance_percent"),
        )
        .order_by("subject__code", "section_name")
    )

    assigned_classes = assigned_classes_qs.count()

    total_students = (
        Enrollment.objects
        .filter(class_section__faculty=faculty)
        .values("student")
        .distinct()
        .count()
    )

    total_records = Enrollment.objects.filter(class_section__faculty=faculty).count()
    graded_records = Grade.objects.filter(enrollment__class_section__faculty=faculty).count()

    progress_percent = 0
    if total_records > 0:
        progress_percent = round((graded_records / total_records) * 100, 2)

    average_grade = (
        Grade.objects
        .filter(enrollment__class_section__faculty=faculty)
        .aggregate(avg=Avg("final_grade"))
        .get("avg")
    )

    average_attendance = (
        AttendanceSummary.objects
        .filter(enrollment__class_section__faculty=faculty)
        .aggregate(avg=Avg("attendance_percent"))
        .get("avg")
    )

    evaluation_average = (
        FacultyEvaluation.objects
        .filter(faculty=faculty)
        .aggregate(avg=Avg("evaluation_score"))
        .get("avg")
    )

    passed_count = Grade.objects.filter(
        enrollment__class_section__faculty=faculty,
        remarks="Passed"
    ).count()

    failed_count = Grade.objects.filter(
        enrollment__class_section__faculty=faculty,
        remarks="Failed"
    ).count()

    grade_distribution_labels = ["Below 75", "75-79", "80-84", "85-89", "90-100"]

    grade_distribution_values = [
        Grade.objects.filter(enrollment__class_section__faculty=faculty, final_grade__lt=75).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty, final_grade__gte=75, final_grade__lt=80).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty, final_grade__gte=80, final_grade__lt=85).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty, final_grade__gte=85, final_grade__lt=90).count(),
        Grade.objects.filter(enrollment__class_section__faculty=faculty, final_grade__gte=90).count(),
    ]

    class_labels = []
    class_grade_values = []
    class_attendance_values = []

    for class_item in assigned_classes_qs:
        class_labels.append(f"{class_item.subject.code} - {class_item.section_name}")
        class_grade_values.append(float(class_item.avg_grade) if class_item.avg_grade is not None else 0)
        class_attendance_values.append(float(class_item.avg_attendance) if class_item.avg_attendance is not None else 0)

    recent_grade_edits = (
        GradeAdjustmentLog.objects
        .filter(grade__enrollment__class_section__faculty=faculty)
        .select_related(
            "edited_by",
            "grade__enrollment__student__user",
            "grade__enrollment__class_section__subject",
        )
        .order_by("-edited_at")[:10]
    )

    evaluation_records = (
        FacultyEvaluation.objects
        .filter(faculty=faculty)
        .order_by("-created_at")[:10]
    )

    context = {
        "page_title": "Faculty Analytics",
        "faculty": faculty,
        "assigned_classes": assigned_classes,
        "total_students": total_students,
        "total_records": total_records,
        "graded_records": graded_records,
        "progress_percent": progress_percent,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "evaluation_average": evaluation_average,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "assigned_classes_qs": assigned_classes_qs,
        "recent_grade_edits": recent_grade_edits,
        "evaluation_records": evaluation_records,

        "class_labels": json.dumps(class_labels),
        "class_grade_values": json.dumps(class_grade_values),
        "class_attendance_values": json.dumps(class_attendance_values),
        "pass_fail_labels": json.dumps(["Passed", "Failed"]),
        "pass_fail_values": json.dumps([passed_count, failed_count]),
        "grade_distribution_labels": json.dumps(grade_distribution_labels),
        "grade_distribution_values": json.dumps(grade_distribution_values),
    }

    return render(request, "academics/admin_faculty_analytics.html", context)


@login_required
def faculty_student_monitoring(request):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access student monitoring.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile
    selected_section = request.GET.get("section", "")

    assigned_sections = (
        ClassSection.objects
        .filter(faculty=faculty_profile)
        .values_list("section_name", flat=True)
        .distinct()
        .order_by("section_name")
    )

    enrollments = (
        Enrollment.objects
        .filter(class_section__faculty=faculty_profile)
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject",
        )
    )

    if selected_section:
        enrollments = enrollments.filter(class_section__section_name=selected_section)

    student_ids = (
        enrollments
        .values_list("student_id", flat=True)
        .distinct()
    )

    students = (
        StudentProfile.objects
        .filter(id__in=student_ids)
        .select_related("user", "department")
        .order_by("student_number")
    )

    student_rows = []

    for student in students:
        student_enrollments = enrollments.filter(student=student)

        grade_qs = Grade.objects.filter(enrollment__in=student_enrollments)
        attendance_qs = AttendanceSummary.objects.filter(enrollment__in=student_enrollments)

        average_grade = grade_qs.aggregate(avg=Avg("final_grade")).get("avg")
        average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

        risk_level, risk_badge, advisory = _student_risk_from_records(grade_qs, attendance_qs)

        student_rows.append({
            "student": student,
            "subjects_count": student_enrollments.count(),
            "average_grade": average_grade,
            "average_attendance": average_attendance,
            "risk_level": risk_level,
            "risk_badge": risk_badge,
            "advisory": advisory,
        })

    context = {
        "page_title": "Student Monitoring",
        "assigned_sections": assigned_sections,
        "selected_section": selected_section,
        "student_rows": student_rows,
    }

    return render(request, "academics/faculty_student_monitoring.html", context)


@login_required
def faculty_student_analytics(request, student_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access student analytics.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    student = get_object_or_404(
        StudentProfile.objects.select_related("user", "department"),
        id=student_id
    )

    enrollments = (
        Enrollment.objects
        .filter(
            student=student,
            class_section__faculty=faculty_profile
        )
        .select_related(
            "class_section__subject",
            "class_section",
            "student__user",
        )
        .order_by("class_section__subject__code")
    )

    if not enrollments.exists():
        messages.error(request, "This student is not enrolled in any of your assigned classes.")
        return redirect("faculty-student-monitoring")

    grade_qs = Grade.objects.filter(enrollment__in=enrollments)
    attendance_qs = AttendanceSummary.objects.filter(enrollment__in=enrollments)

    average_grade = grade_qs.aggregate(avg=Avg("final_grade")).get("avg")
    average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

    passed_count = grade_qs.filter(remarks="Passed").count()
    failed_count = grade_qs.filter(remarks="Failed").count()

    risk_level, risk_badge, advisory = _student_risk_from_records(grade_qs, attendance_qs)

    rows = []
    subject_labels = []
    grade_values = []
    attendance_values = []

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        subject_label = f"{enrollment.class_section.subject.code}"

        subject_labels.append(subject_label)
        grade_values.append(float(grade.final_grade) if grade else 0)
        attendance_values.append(float(attendance.attendance_percent) if attendance else 0)

        subject_risk = "Low Risk"

        if grade and grade.final_grade < 75:
            subject_risk = "High Risk"
        elif attendance and attendance.attendance_percent < 75:
            subject_risk = "High Risk"
        elif grade and grade.final_grade < 80:
            subject_risk = "Moderate Risk"
        elif attendance and attendance.attendance_percent < 85:
            subject_risk = "Moderate Risk"

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "subject_risk": subject_risk,
        })

    recent_grade_edits = (
        GradeAdjustmentLog.objects
        .filter(
            grade__enrollment__student=student,
            grade__enrollment__class_section__faculty=faculty_profile
        )
        .select_related(
            "edited_by",
            "grade__enrollment__class_section__subject",
        )
        .order_by("-edited_at")[:10]
    )

    context = {
        "page_title": "Student Performance Analytics",
        "student": student,
        "rows": rows,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "risk_level": risk_level,
        "risk_badge": risk_badge,
        "advisory": advisory,
        "recent_grade_edits": recent_grade_edits,

        "subject_labels": json.dumps(subject_labels),
        "grade_values": json.dumps(grade_values),
        "attendance_values": json.dumps(attendance_values),
        "pass_fail_labels": json.dumps(["Passed", "Failed"]),
        "pass_fail_values": json.dumps([passed_count, failed_count]),
    }

    return render(request, "academics/faculty_student_analytics.html", context)


@login_required
def faculty_class_advisory(request):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access class advisory.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    advisory_sections = (
        AdvisorySection.objects
        .filter(adviser=faculty_profile)
        .select_related("department", "adviser__user")
        .order_by("department__code", "section_name")
    )

    rows = []

    for advisory in advisory_sections:
        enrollments = Enrollment.objects.filter(
            class_section__section_name=advisory.section_name,
            class_section__term=advisory.term,
            class_section__school_year=advisory.school_year,
        )

        total_students = enrollments.values("student").distinct().count()
        total_subjects = enrollments.values("class_section__subject").distinct().count()

        average_grade = (
            Grade.objects
            .filter(enrollment__in=enrollments)
            .aggregate(avg=Avg("final_grade"))
            .get("avg")
        )

        average_attendance = (
            AttendanceSummary.objects
            .filter(enrollment__in=enrollments)
            .aggregate(avg=Avg("attendance_percent"))
            .get("avg")
        )

        student_ids = enrollments.values_list("student_id", flat=True).distinct()

        at_risk_count = 0
        for student_id in student_ids:
            student_enrollments = enrollments.filter(student_id=student_id)
            grade_qs = Grade.objects.filter(enrollment__in=student_enrollments)
            attendance_qs = AttendanceSummary.objects.filter(enrollment__in=student_enrollments)

            risk_level, risk_badge, advisory_message = _get_student_risk_for_advisory(
                grade_qs,
                attendance_qs
            )

            if risk_level in ["High Risk", "Moderate Risk"]:
                at_risk_count += 1

        rows.append({
            "advisory": advisory,
            "total_students": total_students,
            "total_subjects": total_subjects,
            "average_grade": average_grade,
            "average_attendance": average_attendance,
            "at_risk_count": at_risk_count,
        })

    context = {
        "page_title": "Class Advisory",
        "rows": rows,
    }

    return render(request, "academics/faculty_class_advisory.html", context)


@login_required
def faculty_class_advisory_detail(request, advisory_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access class advisory.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    advisory = get_object_or_404(
        AdvisorySection.objects.select_related("department", "adviser__user"),
        id=advisory_id,
        adviser=faculty_profile,
    )

    enrollments = (
        Enrollment.objects
        .filter(
            class_section__section_name=advisory.section_name,
            class_section__term=advisory.term,
            class_section__school_year=advisory.school_year,
        )
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject",
        )
    )

    total_students = enrollments.values("student").distinct().count()
    total_subjects = enrollments.values("class_section__subject").distinct().count()

    average_grade = (
        Grade.objects
        .filter(enrollment__in=enrollments)
        .aggregate(avg=Avg("final_grade"))
        .get("avg")
    )

    average_attendance = (
        AttendanceSummary.objects
        .filter(enrollment__in=enrollments)
        .aggregate(avg=Avg("attendance_percent"))
        .get("avg")
    )

    passed_count = Grade.objects.filter(enrollment__in=enrollments, remarks="Passed").count()
    failed_count = Grade.objects.filter(enrollment__in=enrollments, remarks="Failed").count()

    subject_summary = (
        Grade.objects
        .filter(enrollment__in=enrollments)
        .values(
            "enrollment__class_section__subject__code",
            "enrollment__class_section__subject__title",
        )
        .annotate(
            avg_grade=Avg("final_grade"),
            avg_attendance=Avg("enrollment__attendance_summary__attendance_percent"),
            student_count=Count("enrollment__student", distinct=True),
        )
        .order_by("enrollment__class_section__subject__code")
    )

    subject_labels = []
    subject_grade_values = []
    subject_attendance_values = []

    for item in subject_summary:
        subject_labels.append(item["enrollment__class_section__subject__code"])
        subject_grade_values.append(float(item["avg_grade"]) if item["avg_grade"] is not None else 0)
        subject_attendance_values.append(float(item["avg_attendance"]) if item["avg_attendance"] is not None else 0)

    grade_distribution_labels = ["Below 75", "75-79", "80-84", "85-89", "90-100"]

    grade_distribution_values = [
        Grade.objects.filter(enrollment__in=enrollments, final_grade__lt=75).count(),
        Grade.objects.filter(enrollment__in=enrollments, final_grade__gte=75, final_grade__lt=80).count(),
        Grade.objects.filter(enrollment__in=enrollments, final_grade__gte=80, final_grade__lt=85).count(),
        Grade.objects.filter(enrollment__in=enrollments, final_grade__gte=85, final_grade__lt=90).count(),
        Grade.objects.filter(enrollment__in=enrollments, final_grade__gte=90).count(),
    ]

    student_ids = enrollments.values_list("student_id", flat=True).distinct()

    student_rows = []
    high_risk_count = 0
    moderate_risk_count = 0
    low_risk_count = 0

    for student_id in student_ids:
        student = StudentProfile.objects.select_related("user", "department").get(id=student_id)
        student_enrollments = enrollments.filter(student=student)

        grade_qs = Grade.objects.filter(enrollment__in=student_enrollments)
        attendance_qs = AttendanceSummary.objects.filter(enrollment__in=student_enrollments)

        student_average_grade = grade_qs.aggregate(avg=Avg("final_grade")).get("avg")
        student_average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

        risk_level, risk_badge, advisory_message = _get_student_risk_for_advisory(
            grade_qs,
            attendance_qs
        )

        if risk_level == "High Risk":
            high_risk_count += 1
        elif risk_level == "Moderate Risk":
            moderate_risk_count += 1
        else:
            low_risk_count += 1

        student_rows.append({
            "student": student,
            "subjects_count": student_enrollments.count(),
            "average_grade": student_average_grade,
            "average_attendance": student_average_attendance,
            "risk_level": risk_level,
            "risk_badge": risk_badge,
        })

    context = {
        "page_title": "Class Advisory Analytics",
        "advisory": advisory,
        "total_students": total_students,
        "total_subjects": total_subjects,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "subject_summary": subject_summary,
        "student_rows": student_rows,

        "subject_labels": json.dumps(subject_labels),
        "subject_grade_values": json.dumps(subject_grade_values),
        "subject_attendance_values": json.dumps(subject_attendance_values),

        "pass_fail_labels": json.dumps(["Passed", "Failed"]),
        "pass_fail_values": json.dumps([passed_count, failed_count]),

        "risk_labels": json.dumps(["High Risk", "Moderate Risk", "Low Risk"]),
        "risk_values": json.dumps([high_risk_count, moderate_risk_count, low_risk_count]),

        "grade_distribution_labels": json.dumps(grade_distribution_labels),
        "grade_distribution_values": json.dumps(grade_distribution_values),
    }

    return render(request, "academics/faculty_class_advisory_detail.html", context)


@login_required
def faculty_class_advisory_student_analytics(request, advisory_id, student_id):
    if not _faculty_check(request):
        messages.error(request, "You are not authorized to access class advisory analytics.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    advisory = get_object_or_404(
        AdvisorySection.objects.select_related("department", "adviser__user"),
        id=advisory_id,
        adviser=faculty_profile,
    )

    student = get_object_or_404(
        StudentProfile.objects.select_related("user", "department"),
        id=student_id
    )

    enrollments = (
        Enrollment.objects
        .filter(
            student=student,
            class_section__section_name=advisory.section_name,
            class_section__term=advisory.term,
            class_section__school_year=advisory.school_year,
        )
        .select_related(
            "class_section__subject",
            "class_section__faculty__user",
        )
        .order_by("class_section__subject__code")
    )

    if not enrollments.exists():
        messages.error(request, "This student does not belong to your advised class section.")
        return redirect("faculty-class-advisory-detail", advisory_id=advisory.id)

    grade_qs = Grade.objects.filter(enrollment__in=enrollments)
    attendance_qs = AttendanceSummary.objects.filter(enrollment__in=enrollments)

    average_grade = grade_qs.aggregate(avg=Avg("final_grade")).get("avg")
    average_attendance = attendance_qs.aggregate(avg=Avg("attendance_percent")).get("avg")

    passed_count = grade_qs.filter(remarks="Passed").count()
    failed_count = grade_qs.filter(remarks="Failed").count()

    risk_level, risk_badge, advisory_message = _get_student_risk_for_advisory(
        grade_qs,
        attendance_qs
    )

    rows = []
    subject_labels = []
    grade_values = []
    attendance_values = []

    for enrollment in enrollments:
        grade = Grade.objects.filter(enrollment=enrollment).first()
        attendance = AttendanceSummary.objects.filter(enrollment=enrollment).first()

        subject_label = enrollment.class_section.subject.code
        subject_labels.append(subject_label)
        grade_values.append(float(grade.final_grade) if grade else 0)
        attendance_values.append(float(attendance.attendance_percent) if attendance else 0)

        subject_risk = "Low Risk"

        if grade and grade.final_grade < 75:
            subject_risk = "High Risk"
        elif attendance and attendance.attendance_percent < 75:
            subject_risk = "High Risk"
        elif grade and grade.final_grade < 80:
            subject_risk = "Moderate Risk"
        elif attendance and attendance.attendance_percent < 85:
            subject_risk = "Moderate Risk"

        rows.append({
            "enrollment": enrollment,
            "grade": grade,
            "attendance": attendance,
            "subject_risk": subject_risk,
        })

    recent_grade_edits = (
        GradeAdjustmentLog.objects
        .filter(
            grade__enrollment__student=student,
            grade__enrollment__in=enrollments,
        )
        .select_related(
            "edited_by",
            "grade__enrollment__class_section__subject",
        )
        .order_by("-edited_at")[:10]
    )

    context = {
        "page_title": "Advisory Student Analytics",
        "advisory": advisory,
        "student": student,
        "rows": rows,
        "average_grade": average_grade,
        "average_attendance": average_attendance,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "risk_level": risk_level,
        "risk_badge": risk_badge,
        "advisory_message": advisory_message,
        "recent_grade_edits": recent_grade_edits,

        "subject_labels": json.dumps(subject_labels),
        "grade_values": json.dumps(grade_values),
        "attendance_values": json.dumps(attendance_values),
        "pass_fail_labels": json.dumps(["Passed", "Failed"]),
        "pass_fail_values": json.dumps([passed_count, failed_count]),
    }

    return render(request, "academics/faculty_class_advisory_student_analytics.html", context)