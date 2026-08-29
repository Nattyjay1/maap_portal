import csv
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse


HIGH_RISK = "High Risk"
MODERATE_RISK = "Moderate Risk"
LOW_RISK = "Low Risk"
NO_DATA = "No Data"
INCOMPLETE_DATA = "Incomplete Data"


def _to_decimal(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def calculate_student_risk(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)

    if grade is None and attendance is None:
        return NO_DATA

    if grade is not None and grade < Decimal("75"):
        return HIGH_RISK

    if attendance is not None and attendance < Decimal("75"):
        return HIGH_RISK

    if grade is not None and Decimal("75") <= grade < Decimal("80"):
        return MODERATE_RISK

    if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
        return MODERATE_RISK

    if grade is not None and attendance is not None:
        if grade >= Decimal("80") and attendance >= Decimal("85"):
            return LOW_RISK

    return INCOMPLETE_DATA


def get_risk_reason(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)
    risk_status = calculate_student_risk(grade, attendance)

    if risk_status == HIGH_RISK:
        reasons = []

        if grade is not None and grade < Decimal("75"):
            reasons.append("Final grade is below the passing threshold.")

        if attendance is not None and attendance < Decimal("75"):
            reasons.append("Attendance is below the critical threshold.")

        return " ".join(reasons)

    if risk_status == MODERATE_RISK:
        reasons = []

        if grade is not None and Decimal("75") <= grade < Decimal("80"):
            reasons.append("Final grade is near the minimum passing threshold.")

        if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
            reasons.append("Attendance requires continued monitoring.")

        return " ".join(reasons)

    if risk_status == LOW_RISK:
        return "Final grade and attendance meet the low-risk thresholds."

    if risk_status == NO_DATA:
        return "No grade or attendance data is available yet."

    if grade is None:
        return "Grade data is missing, while attendance does not currently indicate risk."

    return "Attendance data is missing, while grade performance does not currently indicate risk."


def get_recommended_action(risk_status, reason=None, attendance_percentage=None):
    known_statuses = {
        HIGH_RISK,
        MODERATE_RISK,
        LOW_RISK,
        NO_DATA,
        INCOMPLETE_DATA,
    }

    if attendance_percentage is not None or risk_status not in known_statuses:
        return _get_faculty_recommended_action(
            risk_status,
            reason,
            attendance_percentage,
        )

    status = (risk_status or "").strip()
    reason_text = (reason or "").strip()
    reason_lower = reason_text.lower()

    if status == HIGH_RISK:
        has_grade_issue = "grade" in reason_lower or "passing" in reason_lower
        has_attendance_issue = "attendance" in reason_lower

        if has_grade_issue and has_attendance_issue:
            return "Schedule immediate academic intervention and attendance follow-up."

        if has_grade_issue:
            return "Schedule immediate academic intervention and review learning support needs."

        if has_attendance_issue:
            return "Contact the student and adviser for immediate attendance follow-up."

        return "Prioritize this student for immediate monitoring and intervention."

    if status == MODERATE_RISK:
        return "Monitor weekly and provide early support before the risk level escalates."

    if status == LOW_RISK:
        return "Continue routine monitoring and reinforce current performance."

    if status == NO_DATA:
        return "Request grade and attendance encoding before making an academic risk decision."

    if status == INCOMPLETE_DATA:
        return "Complete the missing academic record, then reassess the student's risk status."

    return "Review the student's latest grade and attendance records."


def _get_related_object(instance, attribute_name):
    try:
        return getattr(instance, attribute_name, None)
    except (AttributeError, ObjectDoesNotExist):
        return None


def _get_enrollment_grade(enrollment):
    return _get_related_object(enrollment, "grade")


def _get_enrollment_attendance(enrollment):
    return _get_related_object(enrollment, "attendance_summary")


def _get_dashboard_risk_status(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)

    if grade is None and attendance is None:
        return NO_DATA

    if grade is not None and grade < Decimal("75"):
        return HIGH_RISK

    if attendance is not None and attendance < Decimal("75"):
        return HIGH_RISK

    if grade is not None and Decimal("75") <= grade < Decimal("80"):
        return MODERATE_RISK

    if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
        return MODERATE_RISK

    return LOW_RISK


def get_risk_status(final_grade, attendance_percentage):
    return _get_dashboard_risk_status(final_grade, attendance_percentage)


def get_risk_explanation(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)
    risk_status = _get_dashboard_risk_status(grade, attendance)

    if risk_status == HIGH_RISK:
        if grade is not None and grade < Decimal("75"):
            return "This subject is marked High Risk because the final grade is below the passing threshold."

        return "This subject is marked High Risk because attendance is below the critical threshold."

    if risk_status == MODERATE_RISK:
        if grade is not None and Decimal("75") <= grade < Decimal("80"):
            return "This subject is marked Moderate Risk because the final grade is near the minimum passing level."

        return "This subject is marked Moderate Risk because attendance needs continued monitoring."

    if risk_status == LOW_RISK:
        if grade is None:
            return "This subject is marked Low Risk based on the available attendance record."

        if attendance is None:
            return "This subject is marked Low Risk based on the available grade record."

        return "This subject is marked Low Risk because both grade and attendance are within acceptable levels."

    return "This subject has No Data because grade and attendance records are not available yet."


def _get_faculty_risk_reason(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)
    risk_status = get_risk_status(grade, attendance)

    if risk_status == NO_DATA:
        return "No grade and attendance records are available yet."

    if grade is not None and grade < Decimal("75") and attendance is not None and attendance < Decimal("75"):
        return "Final grade and attendance are both below the safe thresholds."

    if grade is not None and grade < Decimal("75"):
        return "Final grade is below the passing threshold."

    if attendance is not None and attendance < Decimal("75"):
        return "Attendance is below the critical threshold."

    if grade is not None and Decimal("75") <= grade < Decimal("80"):
        return "Final grade is near the minimum passing level."

    if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
        return "Attendance needs continued monitoring."

    return "Grade and attendance are within acceptable levels."


def _get_faculty_recommended_action(final_grade, attendance_percentage, risk_status=None):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)
    status = risk_status or get_risk_status(grade, attendance)

    has_low_grade = grade is not None and grade < Decimal("75")
    has_low_attendance = attendance is not None and attendance < Decimal("75")

    if has_low_grade and has_low_attendance:
        return "Prioritize this student for academic and attendance monitoring."

    if has_low_grade:
        return "Review grade performance and provide academic support."

    if has_low_attendance:
        return "Check attendance record and coordinate with the student."

    if grade is not None and Decimal("75") <= grade < Decimal("80"):
        return "Monitor closely because the grade is near the minimum passing level."

    if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
        return "Remind student to maintain regular attendance."

    if status == NO_DATA:
        return "Wait for grade and attendance records before deciding on intervention."

    return "Continue routine monitoring."


def _get_enrollment_student_name(enrollment):
    student = _get_related_object(enrollment, "student")
    user = _get_related_object(student, "user") if student else None

    if user is None:
        return "Unknown student"

    return user.get_full_name() or user.username


def _get_enrollment_class_subject(enrollment):
    class_section = _get_related_object(enrollment, "class_section")
    subject = _get_related_object(class_section, "subject") if class_section else None

    if class_section is None and subject is None:
        return "No class assigned"

    if subject is None:
        return getattr(class_section, "section_name", "No class assigned")

    section_name = getattr(class_section, "section_name", "")
    return f"{section_name} / {subject.code} - {subject.title}"


def _get_risk_badge(risk_status):
    if risk_status == HIGH_RISK:
        return "danger"

    if risk_status == MODERATE_RISK:
        return "warning"

    if risk_status == LOW_RISK:
        return "success"

    return "secondary"


def _get_risk_rank(risk_status):
    if risk_status == HIGH_RISK:
        return 3

    if risk_status == MODERATE_RISK:
        return 2

    if risk_status == LOW_RISK:
        return 1

    return 0


def _decimal_average(values):
    decimal_values = [
        value
        for value in [_to_decimal(item) for item in values]
        if value is not None
    ]

    if not decimal_values:
        return None

    return sum(decimal_values) / Decimal(len(decimal_values))


def _safe_percent(numerator, denominator):
    if not denominator:
        return None

    return round((numerator / denominator) * 100, 2)


def _get_student_department(enrollment):
    student = _get_related_object(enrollment, "student")
    return _get_related_object(student, "department") if student else None


def _get_enrollment_department(enrollment):
    class_section = _get_related_object(enrollment, "class_section")
    subject = _get_related_object(class_section, "subject") if class_section else None
    department = _get_related_object(subject, "department") if subject else None

    if department is None:
        department = _get_student_department(enrollment)

    return department


def _get_department_key(department):
    return getattr(department, "id", None) or "unassigned"


def _get_department_code(department):
    return getattr(department, "code", None) or "Unassigned"


def _get_department_name(department):
    return getattr(department, "name", None) or "Unassigned Department"


def get_risk_cause(final_grade, attendance_percentage):
    grade = _to_decimal(final_grade)
    attendance = _to_decimal(attendance_percentage)

    if grade is None and attendance is None:
        return "No Data"

    has_low_grade = grade is not None and grade < Decimal("75")
    has_low_attendance = attendance is not None and attendance < Decimal("75")

    if has_low_grade and has_low_attendance:
        return "Both Low Grade and Low Attendance"

    if has_low_grade:
        return "Low Grade Only"

    if has_low_attendance:
        return "Low Attendance Only"

    if grade is not None and Decimal("75") <= grade < Decimal("80"):
        return "Near Passing Grade"

    if attendance is not None and Decimal("75") <= attendance < Decimal("85"):
        return "Attendance Needs Monitoring"

    return "Within Acceptable Range"


def get_priority_ranked_students(enrollments):
    if enrollments is None:
        return []

    ranked_students = []

    for enrollment in list(enrollments):
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))
        risk_status = get_risk_status(final_grade, attendance_percentage)

        if risk_status not in [HIGH_RISK, MODERATE_RISK]:
            continue

        ranked_students.append({
            "enrollment": enrollment,
            "student_name": _get_enrollment_student_name(enrollment),
            "class_subject": _get_enrollment_class_subject(enrollment),
            "final_grade": final_grade,
            "attendance_percentage": attendance_percentage,
            "has_grade": final_grade is not None,
            "has_attendance": attendance_percentage is not None,
            "risk_status": risk_status,
            "risk_badge": _get_risk_badge(risk_status),
            "main_reason": _get_faculty_risk_reason(final_grade, attendance_percentage),
            "recommended_action": _get_faculty_recommended_action(
                final_grade,
                attendance_percentage,
                risk_status,
            ),
        })

    risk_order = {
        HIGH_RISK: 0,
        MODERATE_RISK: 1,
    }

    ranked_students.sort(
        key=lambda item: (
            risk_order.get(item["risk_status"], 9),
            item["final_grade"] if item["final_grade"] is not None else Decimal("999"),
            item["attendance_percentage"] if item["attendance_percentage"] is not None else Decimal("999"),
            item["student_name"],
        )
    )

    for index, item in enumerate(ranked_students, start=1):
        item["priority_rank"] = index

    return ranked_students


def get_risk_reason_breakdown(enrollments):
    labels = [
        "Low Grade Only",
        "Low Attendance Only",
        "Both Grade and Attendance",
        "Near Passing Grade",
        "Attendance Needs Monitoring",
        "No Data",
    ]
    breakdown = {label: 0 for label in labels}

    if enrollments is None:
        return breakdown

    for enrollment in list(enrollments):
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))

        if final_grade is None and attendance_percentage is None:
            breakdown["No Data"] += 1
            continue

        has_low_grade = final_grade is not None and final_grade < Decimal("75")
        has_low_attendance = attendance_percentage is not None and attendance_percentage < Decimal("75")

        if has_low_grade and has_low_attendance:
            breakdown["Both Grade and Attendance"] += 1
        elif has_low_grade:
            breakdown["Low Grade Only"] += 1
        elif has_low_attendance:
            breakdown["Low Attendance Only"] += 1

        if final_grade is not None and Decimal("75") <= final_grade < Decimal("80"):
            breakdown["Near Passing Grade"] += 1

        if attendance_percentage is not None and Decimal("75") <= attendance_percentage < Decimal("85"):
            breakdown["Attendance Needs Monitoring"] += 1

    return breakdown


def _get_health_status(score):
    if score is None:
        return "No Data", "secondary"

    if score >= Decimal("90"):
        return "Excellent Standing", "success"

    if score >= Decimal("80"):
        return "Good Standing", "primary"

    if score >= Decimal("75"):
        return "Needs Monitoring", "warning"

    return "Critical", "danger"


def get_class_health_scores(class_sections):
    if class_sections is None:
        return []

    try:
        from django.db.models import Avg
        from academics.models import AttendanceSummary, Grade
    except Exception:
        return []

    rows = []

    for class_section in list(class_sections):
        average_grade = (
            Grade.objects
            .filter(enrollment__class_section=class_section)
            .aggregate(avg=Avg("final_grade"))
            .get("avg")
        )
        average_attendance = (
            AttendanceSummary.objects
            .filter(enrollment__class_section=class_section)
            .aggregate(avg=Avg("attendance_percent"))
            .get("avg")
        )

        health_score = None
        if average_grade is not None and average_attendance is not None:
            health_score = (
                _to_decimal(average_grade) + _to_decimal(average_attendance)
            ) / Decimal("2")

        status, badge = _get_health_status(health_score)
        subject = _get_related_object(class_section, "subject")

        rows.append({
            "class_section": class_section,
            "class_subject": f"{class_section.section_name} / {subject.code} - {subject.title}" if subject else class_section.section_name,
            "average_final_grade": _to_decimal(average_grade),
            "average_attendance": _to_decimal(average_attendance),
            "health_score": health_score,
            "status": status,
            "badge": badge,
            "has_grade_data": average_grade is not None,
            "has_attendance_data": average_attendance is not None,
            "has_health_score": health_score is not None,
        })

    return rows


def get_near_passing_students(enrollments):
    if enrollments is None:
        return []

    students = []

    for enrollment in list(enrollments):
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))

        if final_grade is None or not Decimal("75") <= final_grade < Decimal("80"):
            continue

        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))

        students.append({
            "enrollment": enrollment,
            "student_name": _get_enrollment_student_name(enrollment),
            "class_subject": _get_enrollment_class_subject(enrollment),
            "final_grade": final_grade,
            "attendance_percentage": attendance_percentage,
            "has_attendance": attendance_percentage is not None,
            "status": "Near Passing",
            "badge": "warning",
            "suggested_action": "Monitor this student's next assessment and provide guidance if needed.",
        })

    students.sort(
        key=lambda item: (
            item["final_grade"],
            item["attendance_percentage"] if item["attendance_percentage"] is not None else Decimal("999"),
            item["student_name"],
        )
    )

    return students


def get_admin_at_risk_students(enrollments=None):
    try:
        from academics.models import Enrollment
    except Exception:
        return []

    if enrollments is None:
        enrollments = (
            Enrollment.objects
            .select_related(
                "student__user",
                "student__department",
                "class_section__subject__department",
                "grade",
                "attendance_summary",
            )
            .order_by(
                "student__student_number",
                "class_section__subject__code",
                "class_section__section_name",
            )
        )

    student_risk = {}

    for enrollment in list(enrollments):
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))
        risk_status = get_risk_status(final_grade, attendance_percentage)

        if risk_status not in [HIGH_RISK, MODERATE_RISK]:
            continue

        available_values = [
            value
            for value in [final_grade, attendance_percentage]
            if value is not None
        ]
        lowest_available_value = min(available_values) if available_values else Decimal("999")
        student = _get_related_object(enrollment, "student")
        student_id = getattr(student, "id", None) or getattr(enrollment, "student_id", None)
        student_department = _get_student_department(enrollment) or _get_enrollment_department(enrollment)
        class_section = _get_related_object(enrollment, "class_section")
        subject = _get_related_object(class_section, "subject") if class_section else None

        row = {
            "enrollment": enrollment,
            "student": student,
            "student_name": _get_enrollment_student_name(enrollment),
            "department": student_department,
            "department_code": _get_department_code(student_department),
            "department_name": _get_department_name(student_department),
            "class_section": class_section,
            "class_section_name": getattr(class_section, "section_name", "No class assigned"),
            "class_subject": _get_enrollment_class_subject(enrollment),
            "subject": subject,
            "subject_code": getattr(subject, "code", "N/A"),
            "subject_title": getattr(subject, "title", "No subject title"),
            "final_grade": final_grade,
            "attendance_percent": attendance_percentage,
            "has_grade": final_grade is not None,
            "has_attendance": attendance_percentage is not None,
            "risk_status": risk_status,
            "risk_badge": _get_risk_badge(risk_status),
            "risk_rank": _get_risk_rank(risk_status),
            "reason": _get_faculty_risk_reason(final_grade, attendance_percentage),
            "recommended_action": _get_faculty_recommended_action(
                final_grade,
                attendance_percentage,
                risk_status,
            ),
            "lowest_available_value": lowest_available_value,
        }

        current_row = student_risk.get(student_id)
        if (
            current_row is None
            or row["risk_rank"] > current_row["risk_rank"]
            or (
                row["risk_rank"] == current_row["risk_rank"]
                and row["lowest_available_value"] < current_row["lowest_available_value"]
            )
        ):
            student_risk[student_id] = row

    return sorted(
        student_risk.values(),
        key=lambda item: (
            -item["risk_rank"],
            item["department_code"],
            item["student_name"],
        )
    )


def get_faculty_submission_progress():
    try:
        from django.db.models import Count
        from academics.models import FacultyProfile
    except Exception:
        return []

    rows = []
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
        completion_percent = _safe_percent(encoded_records, expected_records) or 0

        if completion_percent == 100:
            completion_status = "Complete"
            completion_badge = "success"
        elif completion_percent > 0:
            completion_status = "In Progress"
            completion_badge = "warning"
        else:
            completion_status = "Not Started"
            completion_badge = "secondary"

        rows.append({
            "faculty": faculty,
            "faculty_name": faculty.user.get_full_name() or faculty.user.username,
            "department": faculty.department,
            "department_code": _get_department_code(faculty.department),
            "department_name": _get_department_name(faculty.department),
            "expected_grade_records": expected_records,
            "encoded_grade_records": encoded_records,
            "pending_records": pending_records,
            "completion_percent": completion_percent,
            "completion_status": completion_status,
            "completion_badge": completion_badge,
        })

    return rows


def _new_department_row(department):
    return {
        "department": department,
        "department_code": _get_department_code(department),
        "department_name": _get_department_name(department),
        "total_students": 0,
        "low_risk_count": 0,
        "moderate_risk_count": 0,
        "high_risk_count": 0,
        "no_data_count": 0,
        "average_grade": None,
        "average_attendance": None,
        "faculty_submission_progress": None,
        "department_health_score": None,
        "health_score": None,
        "health_status": "No Data",
        "status": "No Data",
        "health_badge": "secondary",
        "badge": "secondary",
        "risk_level_summary": "No Data",
        "risk_badge": "secondary",
        "recommended_action": "Verify encoded enrollments before reviewing department risk.",
        "_student_risks": {},
        "_grade_values": [],
        "_attendance_values": [],
        "_expected_grade_records": 0,
        "_encoded_grade_records": 0,
    }


def _finalize_department_row(row):
    student_risks = row.pop("_student_risks", {})
    grade_values = row.pop("_grade_values", [])
    attendance_values = row.pop("_attendance_values", [])
    expected_records = row.pop("_expected_grade_records", 0)
    encoded_records = row.pop("_encoded_grade_records", 0)

    row["total_students"] = len(student_risks)
    row["low_risk_count"] = sum(
        1 for item in student_risks.values()
        if item["risk_status"] == LOW_RISK
    )
    row["moderate_risk_count"] = sum(
        1 for item in student_risks.values()
        if item["risk_status"] == MODERATE_RISK
    )
    row["high_risk_count"] = sum(
        1 for item in student_risks.values()
        if item["risk_status"] == HIGH_RISK
    )
    row["no_data_count"] = sum(
        1 for item in student_risks.values()
        if item["risk_status"] == NO_DATA
    )
    row["average_grade"] = _decimal_average(grade_values)
    row["average_attendance"] = _decimal_average(attendance_values)
    row["faculty_submission_progress"] = _safe_percent(
        encoded_records,
        expected_records,
    )

    health_score = None
    if row["average_grade"] is not None and row["average_attendance"] is not None:
        health_values = [row["average_grade"], row["average_attendance"]]
        if row["faculty_submission_progress"] is not None:
            health_values.append(_to_decimal(row["faculty_submission_progress"]))
        health_score = sum(health_values) / Decimal(len(health_values))

    health_status, health_badge = _get_health_status(health_score)
    row["department_health_score"] = health_score
    row["health_score"] = health_score
    row["health_status"] = health_status
    row["status"] = health_status
    row["health_badge"] = health_badge
    row["badge"] = health_badge

    if row["high_risk_count"] > 0:
        row["risk_level_summary"] = "High Risk Priority"
        row["risk_badge"] = "danger"
        row["recommended_action"] = "Review high-risk students and coordinate with faculty advisers."
    elif row["moderate_risk_count"] > 0:
        row["risk_level_summary"] = "Needs Monitoring"
        row["risk_badge"] = "warning"
        row["recommended_action"] = "Monitor students near the minimum passing level."
    elif row["average_attendance"] is not None and row["average_attendance"] < Decimal("85"):
        row["risk_level_summary"] = "Attendance Monitoring"
        row["risk_badge"] = "warning"
        row["recommended_action"] = "Review attendance concerns and coordinate with concerned faculty."
    elif row["total_students"] == 0:
        row["risk_level_summary"] = "No Data"
        row["risk_badge"] = "secondary"
        row["recommended_action"] = "Verify encoded enrollments before reviewing department risk."
    else:
        row["risk_level_summary"] = "Stable"
        row["risk_badge"] = "success"
        row["recommended_action"] = "Continue monitoring academic performance."

    return row


def get_department_risk_ranking():
    try:
        from academics.models import Department, Enrollment
    except Exception:
        return []

    rows_by_key = {}
    for department in Department.objects.order_by("code"):
        rows_by_key[_get_department_key(department)] = _new_department_row(department)

    enrollments = (
        Enrollment.objects
        .select_related(
            "student__user",
            "student__department",
            "class_section__subject__department",
            "grade",
            "attendance_summary",
        )
    )

    for enrollment in enrollments:
        department = _get_enrollment_department(enrollment)
        department_key = _get_department_key(department)

        if department_key not in rows_by_key:
            rows_by_key[department_key] = _new_department_row(department)

        row = rows_by_key[department_key]
        row["_expected_grade_records"] += 1

        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))

        if final_grade is not None:
            row["_grade_values"].append(final_grade)
            row["_encoded_grade_records"] += 1

        if attendance_percentage is not None:
            row["_attendance_values"].append(attendance_percentage)

        risk_status = get_risk_status(final_grade, attendance_percentage)
        available_values = [
            value
            for value in [final_grade, attendance_percentage]
            if value is not None
        ]
        lowest_available_value = min(available_values) if available_values else Decimal("999")
        student = _get_related_object(enrollment, "student")
        student_id = getattr(student, "id", None) or getattr(enrollment, "student_id", None)
        current_risk = row["_student_risks"].get(student_id)
        risk_row = {
            "risk_status": risk_status,
            "risk_rank": _get_risk_rank(risk_status),
            "lowest_available_value": lowest_available_value,
        }

        if (
            current_risk is None
            or risk_row["risk_rank"] > current_risk["risk_rank"]
            or (
                risk_row["risk_rank"] == current_risk["risk_rank"]
                and risk_row["lowest_available_value"] < current_risk["lowest_available_value"]
            )
        ):
            row["_student_risks"][student_id] = risk_row

    rows = [
        _finalize_department_row(row)
        for row in rows_by_key.values()
    ]

    rows.sort(
        key=lambda item: (
            -item["high_risk_count"],
            -item["moderate_risk_count"],
            item["average_grade"] if item["average_grade"] is not None else Decimal("999"),
            item["average_attendance"] if item["average_attendance"] is not None else Decimal("999"),
            item["department_code"],
        )
    )

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    return rows


def get_department_health_scores(department_risk_ranking=None):
    rows = department_risk_ranking or get_department_risk_ranking()
    health_rows = []

    for row in rows:
        health_rows.append({
            "department": row.get("department"),
            "department_code": row.get("department_code"),
            "department_name": row.get("department_name"),
            "average_grade": row.get("average_grade"),
            "average_attendance": row.get("average_attendance"),
            "faculty_submission_progress": row.get("faculty_submission_progress"),
            "department_health_score": row.get("department_health_score"),
            "health_score": row.get("health_score"),
            "status": row.get("status"),
            "badge": row.get("badge"),
        })

    health_rows.sort(
        key=lambda item: (
            item["department_health_score"] if item["department_health_score"] is not None else Decimal("999"),
            item["department_code"] or "",
        )
    )

    return health_rows


def get_risk_cause_summary(enrollments=None):
    try:
        from academics.models import Enrollment
    except Exception:
        return {}

    labels = [
        "Low Grade Only",
        "Low Attendance Only",
        "Both Low Grade and Low Attendance",
        "Near Passing Grade",
        "Attendance Needs Monitoring",
        "No Data",
    ]
    summary = {label: 0 for label in labels}

    if enrollments is None:
        enrollments = (
            Enrollment.objects
            .select_related(
                "grade",
                "attendance_summary",
            )
        )

    student_causes = {}

    for enrollment in list(enrollments):
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))
        cause = get_risk_cause(final_grade, attendance_percentage)
        risk_status = get_risk_status(final_grade, attendance_percentage)
        available_values = [
            value
            for value in [final_grade, attendance_percentage]
            if value is not None
        ]
        lowest_available_value = min(available_values) if available_values else Decimal("999")
        student = _get_related_object(enrollment, "student")
        student_id = getattr(student, "id", None) or getattr(enrollment, "student_id", None)

        cause_row = {
            "cause": cause,
            "risk_rank": _get_risk_rank(risk_status),
            "lowest_available_value": lowest_available_value,
        }

        current_cause = student_causes.get(student_id)
        if (
            current_cause is None
            or cause_row["risk_rank"] > current_cause["risk_rank"]
            or (
                cause_row["risk_rank"] == current_cause["risk_rank"]
                and cause_row["lowest_available_value"] < current_cause["lowest_available_value"]
            )
        ):
            student_causes[student_id] = cause_row

    for cause_row in student_causes.values():
        cause = cause_row["cause"]
        if cause in summary:
            summary[cause] += 1

    return summary


def _section_recommended_action(main_concern, high_risk_count, moderate_risk_count):
    if high_risk_count > 0:
        return "Review students with High Risk status."

    if main_concern == "Many students near passing":
        return "Provide academic guidance to students near the passing level."

    if moderate_risk_count > 0:
        return "Monitor grade and attendance records before the next reporting period."

    return "Coordinate with the assigned faculty adviser."


def get_top_sections_needing_attention(limit=5):
    try:
        from academics.models import ClassSection, Enrollment
    except Exception:
        return []

    enrollments_by_section = {}
    enrollments = (
        Enrollment.objects
        .select_related(
            "student__user",
            "class_section",
            "grade",
            "attendance_summary",
        )
    )

    for enrollment in enrollments:
        enrollments_by_section.setdefault(enrollment.class_section_id, []).append(enrollment)

    rows = []
    class_sections = (
        ClassSection.objects
        .select_related(
            "subject__department",
            "faculty__user",
            "faculty__department",
        )
        .order_by("school_year", "term", "section_name")
    )

    for class_section in class_sections:
        section_enrollments = enrollments_by_section.get(class_section.id, [])
        grade_values = []
        attendance_values = []
        high_risk_count = 0
        moderate_risk_count = 0
        low_grade_count = 0
        low_attendance_count = 0
        near_passing_count = 0
        attendance_monitoring_count = 0

        for enrollment in section_enrollments:
            grade = _get_enrollment_grade(enrollment)
            attendance = _get_enrollment_attendance(enrollment)
            final_grade = _to_decimal(getattr(grade, "final_grade", None))
            attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))

            if final_grade is not None:
                grade_values.append(final_grade)
                if final_grade < Decimal("75"):
                    low_grade_count += 1
                elif final_grade < Decimal("80"):
                    near_passing_count += 1

            if attendance_percentage is not None:
                attendance_values.append(attendance_percentage)
                if attendance_percentage < Decimal("75"):
                    low_attendance_count += 1
                elif attendance_percentage < Decimal("85"):
                    attendance_monitoring_count += 1

            risk_status = get_risk_status(final_grade, attendance_percentage)
            if risk_status == HIGH_RISK:
                high_risk_count += 1
            elif risk_status == MODERATE_RISK:
                moderate_risk_count += 1

        average_grade = _decimal_average(grade_values)
        average_attendance = _decimal_average(attendance_values)
        class_health_score = None
        if average_grade is not None and average_attendance is not None:
            class_health_score = (average_grade + average_attendance) / Decimal("2")

        status, badge = _get_health_status(class_health_score)

        if low_grade_count > 0 and low_attendance_count > 0:
            main_concern = "Grade and attendance concern"
        elif low_grade_count > 0:
            main_concern = "Low grade concern"
        elif low_attendance_count > 0:
            main_concern = "Attendance concern"
        elif near_passing_count > 0:
            main_concern = "Many students near passing"
        elif attendance_monitoring_count > 0 or moderate_risk_count > 0:
            main_concern = "Needs monitoring"
        elif not section_enrollments:
            main_concern = "No enrollment data"
        else:
            main_concern = "Stable"

        subject = _get_related_object(class_section, "subject")
        department = _get_related_object(subject, "department") if subject else None
        faculty = _get_related_object(class_section, "faculty")
        faculty_user = _get_related_object(faculty, "user") if faculty else None
        faculty_name = "No faculty assigned"
        if faculty_user is not None:
            faculty_name = faculty_user.get_full_name() or faculty_user.username

        rows.append({
            "class_section": class_section,
            "rank": None,
            "section_name": getattr(class_section, "section_name", "No section"),
            "subject": subject,
            "subject_code": getattr(subject, "code", "N/A"),
            "subject_title": getattr(subject, "title", "No subject title"),
            "department": department,
            "department_code": _get_department_code(department),
            "department_name": _get_department_name(department),
            "faculty": faculty,
            "faculty_name": faculty_name,
            "total_students": len(section_enrollments),
            "high_risk_count": high_risk_count,
            "moderate_risk_count": moderate_risk_count,
            "average_grade": average_grade,
            "average_attendance": average_attendance,
            "class_health_score": class_health_score,
            "health_score": class_health_score,
            "status": status,
            "badge": badge,
            "main_concern": main_concern,
            "recommended_action": _section_recommended_action(
                main_concern,
                high_risk_count,
                moderate_risk_count,
            ),
        })

    rows.sort(
        key=lambda item: (
            -item["high_risk_count"],
            -item["moderate_risk_count"],
            item["class_health_score"] if item["class_health_score"] is not None else Decimal("999"),
            item["average_attendance"] if item["average_attendance"] is not None else Decimal("999"),
            item["section_name"],
        )
    )

    if limit is not None:
        rows = rows[:limit]

    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    return rows


def export_csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)

    for row in rows:
        writer.writerow(row)

    return response


def get_subject_priority_ranking(enrollments):
    if enrollments is None:
        return []

    enrollment_list = list(enrollments)
    ranked_subjects = []

    for enrollment in enrollment_list:
        class_section = _get_related_object(enrollment, "class_section")
        subject = _get_related_object(class_section, "subject") if class_section else None
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)

        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))
        risk_status = _get_dashboard_risk_status(final_grade, attendance_percentage)

        ranked_subjects.append({
            "enrollment": enrollment,
            "class_section": class_section,
            "subject": subject,
            "subject_code": getattr(subject, "code", "N/A"),
            "subject_title": getattr(subject, "title", "No subject title"),
            "final_grade": final_grade,
            "attendance_percentage": attendance_percentage,
            "has_grade": final_grade is not None,
            "has_attendance": attendance_percentage is not None,
            "risk_status": risk_status,
            "reason": get_risk_explanation(final_grade, attendance_percentage),
        })

    risk_order = {
        HIGH_RISK: 0,
        MODERATE_RISK: 1,
        LOW_RISK: 2,
        NO_DATA: 3,
    }

    ranked_subjects.sort(
        key=lambda item: (
            risk_order.get(item["risk_status"], 4),
            item["final_grade"] if item["final_grade"] is not None else Decimal("999"),
            item["attendance_percentage"] if item["attendance_percentage"] is not None else Decimal("999"),
            item["subject_code"],
        )
    )

    for index, item in enumerate(ranked_subjects, start=1):
        item["priority_number"] = index

    return ranked_subjects


def _resolve_weakest_subject(weakest_subject):
    if weakest_subject is None:
        return None, None

    if isinstance(weakest_subject, dict):
        subject = weakest_subject.get("subject")
        class_section = weakest_subject.get("class_section")

        if subject is None:
            enrollment = weakest_subject.get("enrollment")
            class_section = class_section or _get_related_object(enrollment, "class_section")
            subject = _get_related_object(class_section, "subject") if class_section else None

        if subject is None and weakest_subject.get("subject_code"):
            try:
                from academics.models import Subject

                subject = Subject.objects.filter(code=weakest_subject["subject_code"]).first()
            except Exception:
                subject = None

        return subject, class_section

    class_section = _get_related_object(weakest_subject, "class_section")
    subject = _get_related_object(class_section, "subject") if class_section else None

    if subject is None:
        subject = _get_related_object(weakest_subject, "subject")

    if subject is None and hasattr(weakest_subject, "code"):
        subject = weakest_subject

    return subject, class_section


def get_recommended_learning_materials(student, weakest_subject):
    subject, class_section = _resolve_weakest_subject(weakest_subject)

    if subject is None and class_section is None:
        return {
            "materials": [],
            "message": "No recommended material is available yet.",
            "subject": None,
            "class_section": None,
        }

    try:
        from django.db.models import Q
        from materials.models import LessonMaterial
    except Exception:
        return {
            "materials": [],
            "message": "No recommended material is available yet.",
            "subject": subject,
            "class_section": class_section,
        }

    filters = Q()

    if subject is not None:
        filters |= Q(subject=subject)

    if class_section is not None:
        filters |= Q(class_section=class_section)

    materials = list(
        LessonMaterial.objects
        .filter(filters, is_active=True, visibility__in=["all", "students"])
        .select_related("subject", "class_section__subject", "uploaded_by")
        .order_by("-uploaded_at")
        .distinct()[:5]
    )

    message = ""
    if not materials:
        message = "No recommended material is available yet."

    return {
        "materials": materials,
        "message": message,
        "subject": subject,
        "class_section": class_section,
    }


def get_progress_trend(enrollments):
    if enrollments is None:
        return "Stable"

    enrollment_list = list(enrollments)
    if not enrollment_list:
        return "Stable"

    risk_statuses = []
    grade_values = []

    for enrollment in enrollment_list:
        grade = _get_enrollment_grade(enrollment)
        attendance = _get_enrollment_attendance(enrollment)
        final_grade = _to_decimal(getattr(grade, "final_grade", None))
        attendance_percentage = _to_decimal(getattr(attendance, "attendance_percent", None))
        risk_status = _get_dashboard_risk_status(final_grade, attendance_percentage)

        risk_statuses.append(risk_status)

        if final_grade is not None:
            grade_values.append(final_grade)

    if HIGH_RISK in risk_statuses:
        return "Declining"

    if MODERATE_RISK in risk_statuses:
        return "Needs Monitoring"

    low_risk_count = risk_statuses.count(LOW_RISK)
    evaluated_count = len([status for status in risk_statuses if status != NO_DATA])

    if evaluated_count == 0:
        return "Stable"

    average_grade = None
    if grade_values:
        average_grade = sum(grade_values) / Decimal(len(grade_values))

    if low_risk_count == len(risk_statuses) and average_grade is not None and average_grade >= Decimal("90"):
        return "Improving"

    if low_risk_count >= (evaluated_count / 2):
        return "Stable"

    return "Needs Monitoring"


def _has_queryset_api(records):
    return (
        hasattr(records, "filter")
        and hasattr(records, "count")
        and hasattr(records, "values_list")
    )


def _count_records(records):
    if records is None:
        return 0

    if _has_queryset_api(records):
        return records.count()

    return len(records)


def _has_related_grade(enrollment):
    try:
        return getattr(enrollment, "grade", None) is not None
    except (AttributeError, ObjectDoesNotExist):
        return False


def _get_enrollment_ids(enrollments):
    return [
        enrollment_id
        for enrollment_id in [
            getattr(enrollment, "id", None)
            for enrollment in enrollments
        ]
        if enrollment_id is not None
    ]


def _count_grade_records(grades, enrollments):
    if grades is None:
        from academics.models import Grade

        if _has_queryset_api(enrollments):
            return Grade.objects.filter(enrollment__in=enrollments).count()

        enrollment_ids = _get_enrollment_ids(enrollments)
        if enrollment_ids:
            return Grade.objects.filter(enrollment_id__in=enrollment_ids).count()

        return sum(1 for enrollment in enrollments if _has_related_grade(enrollment))

    if _has_queryset_api(grades):
        if _has_queryset_api(enrollments):
            return grades.filter(enrollment__in=enrollments).values("enrollment_id").distinct().count()

        enrollment_ids = _get_enrollment_ids(enrollments)
        if enrollment_ids:
            return grades.filter(enrollment_id__in=enrollment_ids).values("enrollment_id").distinct().count()

        return grades.values("enrollment_id").distinct().count()

    enrollment_ids = set(_get_enrollment_ids(enrollments))
    submitted_enrollment_ids = set()

    for grade in grades:
        enrollment_id = getattr(grade, "enrollment_id", None)

        if enrollment_id is None and getattr(grade, "enrollment", None) is not None:
            enrollment_id = getattr(grade.enrollment, "id", None)

        if enrollment_ids and enrollment_id not in enrollment_ids:
            continue

        if enrollment_id is not None:
            submitted_enrollment_ids.add(enrollment_id)

    return len(submitted_enrollment_ids)


def compute_faculty_submission_progress(class_sections=None, enrollments=None, grades=None):
    if enrollments is None and class_sections is not None:
        from academics.models import Enrollment

        enrollments = Enrollment.objects.filter(class_section__in=class_sections)

    if enrollments is None:
        enrollments = []
    elif not _has_queryset_api(enrollments):
        enrollments = list(enrollments)

    if grades is not None and not _has_queryset_api(grades):
        grades = list(grades)

    total_records = _count_records(enrollments)
    graded_records = _count_grade_records(grades, enrollments) if total_records else 0
    graded_records = min(graded_records, total_records)
    missing_records = max(total_records - graded_records, 0)

    progress_percent = 0
    if total_records > 0:
        progress_percent = round((graded_records / total_records) * 100, 2)

    if total_records > 0 and graded_records == total_records:
        progress_status = "Complete"
    elif graded_records > 0:
        progress_status = "In Progress"
    else:
        progress_status = "Not Started"

    return {
        "total_records": total_records,
        "graded_records": graded_records,
        "missing_records": missing_records,
        "progress_percent": progress_percent,
        "progress_status": progress_status,
        "is_complete": progress_status == "Complete",
    }


__all__ = [
    "HIGH_RISK",
    "MODERATE_RISK",
    "LOW_RISK",
    "NO_DATA",
    "INCOMPLETE_DATA",
    "calculate_student_risk",
    "get_risk_status",
    "get_risk_cause",
    "get_admin_at_risk_students",
    "get_department_risk_ranking",
    "get_department_health_scores",
    "get_risk_cause_summary",
    "get_top_sections_needing_attention",
    "get_faculty_submission_progress",
    "get_subject_priority_ranking",
    "get_risk_explanation",
    "get_risk_reason",
    "get_recommended_action",
    "get_recommended_learning_materials",
    "get_progress_trend",
    "get_priority_ranked_students",
    "get_risk_reason_breakdown",
    "get_class_health_scores",
    "get_near_passing_students",
    "compute_faculty_submission_progress",
    "export_csv_response",
]
