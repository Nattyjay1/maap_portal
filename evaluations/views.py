import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from .forms import FacultyEvaluationForm, FacultySelfEvaluationForm
from .models import FacultyEvaluation


def _admin_check(request):
    return request.user.is_authenticated and request.user.role == "admin"


@login_required
def evaluation_input(request):
    if not _admin_check(request):
        messages.error(request, "You are not authorized to access the evaluation module.")
        return redirect("role-redirect")

    if request.method == "POST":
        form = FacultyEvaluationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculty evaluation summary saved successfully.")
            return redirect("evaluation-input")
    else:
        form = FacultyEvaluationForm()

    recent_evaluations = FacultyEvaluation.objects.select_related(
        "faculty__user",
        "faculty__department"
    )[:10]

    context = {
        "page_title": "Faculty Evaluation Input",
        "form": form,
        "recent_evaluations": recent_evaluations,
    }
    return render(request, "evaluations/evaluation_input.html", context)


@login_required
def evaluation_summary(request):
    if not _admin_check(request):
        messages.error(request, "You are not authorized to access the evaluation summary page.")
        return redirect("role-redirect")

    summary = (
        FacultyEvaluation.objects
        .values(
            "faculty__id",
            "faculty__employee_id",
            "faculty__user__first_name",
            "faculty__user__last_name",
            "faculty__department__code",
        )
        .annotate(
            average_score=Avg("evaluation_score"),
            total_evaluations=Count("id"),
        )
        .order_by("faculty__employee_id")
    )

    total_entries = FacultyEvaluation.objects.count()
    overall_average = FacultyEvaluation.objects.aggregate(avg=Avg("evaluation_score"))["avg"]
    total_faculty_evaluated = summary.count()

    context = {
        "page_title": "Faculty Evaluation Summary",
        "summary": summary,
        "total_entries": total_entries,
        "overall_average": overall_average,
        "total_faculty_evaluated": total_faculty_evaluated,
    }
    return render(request, "evaluations/evaluation_summary.html", context)


@login_required
def evaluation_portal(request):
    if request.user.role == "admin":
        return redirect("evaluation-summary")

    if request.user.role == "faculty":
        return redirect("faculty-evaluation-dashboard")

    return redirect("role-redirect")


@login_required
def faculty_evaluation_dashboard(request):
    if request.user.role != "faculty" or not hasattr(request.user, "faculty_profile"):
        messages.error(request, "You are not authorized to access faculty evaluation.")
        return redirect("role-redirect")

    faculty_profile = request.user.faculty_profile

    if request.method == "POST":
        form = FacultySelfEvaluationForm(request.POST)

        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.faculty = faculty_profile
            evaluation.evaluator_type = "self"
            evaluation.save()

            messages.success(request, "Self-evaluation entry submitted successfully.")
            return redirect("faculty-evaluation-dashboard")
    else:
        form = FacultySelfEvaluationForm(initial={
            "term": "1st Semester",
            "school_year": "2025-2026",
        })

    evaluations = (
        FacultyEvaluation.objects
        .filter(faculty=faculty_profile)
        .order_by("-created_at")
    )

    total_evaluations = evaluations.count()

    overall_average = evaluations.aggregate(
        avg=Avg("evaluation_score")
    ).get("avg")

    evaluation_by_type = list(
        evaluations
        .values("evaluator_type")
        .annotate(
            average_score=Avg("evaluation_score"),
            total=Count("id"),
        )
        .order_by("evaluator_type")
    )

    type_display = {
        "student": "Student",
        "peer": "Peer",
        "admin": "Admin",
        "self": "Self-Evaluation",
    }

    chart_labels = []
    chart_values = []
    chart_counts = []

    for item in evaluation_by_type:
        chart_labels.append(type_display.get(item["evaluator_type"], item["evaluator_type"]))
        chart_values.append(float(item["average_score"]) if item["average_score"] is not None else 0)
        chart_counts.append(item["total"])

    recent_evaluations = evaluations[:10]

    context = {
        "page_title": "My Faculty Evaluation",
        "faculty_profile": faculty_profile,
        "form": form,
        "total_evaluations": total_evaluations,
        "overall_average": overall_average,
        "evaluation_by_type": evaluation_by_type,
        "recent_evaluations": recent_evaluations,
        "type_display": type_display,

        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
        "chart_counts": json.dumps(chart_counts),
    }

    return render(request, "evaluations/faculty_evaluation_dashboard.html", context)