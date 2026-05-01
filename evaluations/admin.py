from django.contrib import admin
from .models import FacultyEvaluation


@admin.register(FacultyEvaluation)
class FacultyEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "faculty",
        "evaluator_type",
        "evaluation_score",
        "term",
        "school_year",
        "created_at",
    )
    search_fields = (
        "faculty__employee_id",
        "faculty__user__username",
        "faculty__user__first_name",
        "faculty__user__last_name",
        "remarks",
    )
    list_filter = (
        "evaluator_type",
        "term",
        "school_year",
        "faculty__department",
    )