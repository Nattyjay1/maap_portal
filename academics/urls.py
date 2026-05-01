from django.urls import path
from . import views

urlpatterns = [
    path("faculty/classes/", views.faculty_class_list, name="faculty-class-list"),
    path("faculty/attendance/classes/", views.faculty_class_list, name="faculty-attendance-class-list"),

    path("faculty/classes/<int:class_id>/students/", views.enrolled_student_list, name="enrolled-student-list"),
    path("faculty/classes/<int:class_id>/encode-grades/", views.class_grade_entry, name="class-grade-entry"),
    path("faculty/classes/<int:class_id>/attendance/", views.class_attendance_entry, name="class-attendance-entry"),

    path("faculty/enrollment/<int:enrollment_id>/grade/", views.grade_entry, name="grade-entry"),

    path("student/attendance/", views.student_attendance_list, name="student-attendance-list"),
    path("student/grades/", views.student_grade_list, name="student-grade-list"),
    
    path("admin/faculty/", views.admin_faculty_list, name="admin-faculty-list"),
    path("admin/faculty/<int:faculty_id>/analytics/", views.admin_faculty_analytics, name="admin-faculty-analytics"),
    
    path("faculty/students/", views.faculty_student_monitoring, name="faculty-student-monitoring"),
    path("faculty/students/<int:student_id>/analytics/", views.faculty_student_analytics, name="faculty-student-analytics"),
    
    path("faculty/class-advisory/", views.faculty_class_advisory, name="faculty-class-advisory"),
    path("faculty/class-advisory/<int:advisory_id>/", views.faculty_class_advisory_detail, name="faculty-class-advisory-detail"),
    path("faculty/class-advisory/<int:advisory_id>/student/<int:student_id>/", views.faculty_class_advisory_student_analytics, name="faculty-class-advisory-student-analytics"),
]