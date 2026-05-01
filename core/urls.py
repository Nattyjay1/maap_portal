from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("redirect/", views.role_redirect_view, name="role-redirect"),

    path("admin-dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("faculty-dashboard/", views.faculty_dashboard, name="faculty-dashboard"),
    path("student-dashboard/", views.student_dashboard, name="student-dashboard"),
    path("student/forms/", views.student_forms_placeholder, name="student-forms-placeholder"),

    path("unified-access/", views.unified_access_portal, name="unified-access"),
    
    path("admin/forms/", views.admin_forms_placeholder, name="admin-forms-placeholder"),
    path("admin/reports/", views.admin_reports_placeholder, name="admin-reports-placeholder"),
]