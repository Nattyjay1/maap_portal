from django.urls import path
from . import views

urlpatterns = [
    path("", views.reports_index, name="reports-index"),
    path("class/<int:class_id>/grade-report/", views.printable_grade_report, name="printable-grade-report"),
    path("my-progress/", views.printable_my_progress_report, name="printable-my-progress-report"),
    path("student/<int:student_id>/progress/", views.printable_student_progress_report, name="printable-student-progress-report"),
    path("department-summary/", views.printable_department_summary, name="printable-department-summary"),
]