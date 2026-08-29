from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("redirect/", views.role_redirect_view, name="role-redirect"),

    path("admin-dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("admin-dashboard/export/at-risk/", views.admin_export_at_risk_report, name="admin-dashboard-export-at-risk"),
    path("admin-dashboard/export/faculty-submission/", views.admin_export_faculty_submission_report, name="admin-dashboard-export-faculty-submission"),
    path("admin-dashboard/export/department-risk/", views.admin_export_department_risk_report, name="admin-dashboard-export-department-risk"),
    path("admin-dashboard/export/top-sections/", views.admin_export_top_sections_report, name="admin-dashboard-export-top-sections"),
    path("faculty-dashboard/", views.faculty_dashboard, name="faculty-dashboard"),
    path("student-dashboard/", views.student_dashboard, name="student-dashboard"),
    path("student/forms/", views.student_forms_placeholder, name="student-forms-placeholder"),

    path("unified-access/", views.unified_access_portal, name="unified-access"),
    
    path("admin/forms/", views.admin_forms_placeholder, name="admin-forms-placeholder"),
    path("admin/reports/", views.admin_reports_placeholder, name="admin-reports-placeholder"),
]
