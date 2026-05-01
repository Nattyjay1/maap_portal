from django.contrib import admin
from .models import AcademicForm


@admin.register(AcademicForm)
class AcademicFormAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active", "uploaded_by", "uploaded_at")
    search_fields = ("title", "description", "category")
    list_filter = ("category", "is_active", "uploaded_at")