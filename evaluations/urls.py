from django.urls import path
from . import views

urlpatterns = [
    path("", views.evaluation_portal, name="evaluation-portal"),

    path("admin/input/", views.evaluation_input, name="evaluation-input"),
    path("admin/summary/", views.evaluation_summary, name="evaluation-summary"),

    path("faculty/my-evaluations/", views.faculty_evaluation_dashboard, name="faculty-evaluation-dashboard"),
]