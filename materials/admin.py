from django.contrib import admin

from .models import LessonMaterial


@admin.register(LessonMaterial)
class LessonMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "material_type",
        "subject",
        "class_section",
        "visibility",
        "uploaded_by",
        "is_active",
        "uploaded_at",
    )
    search_fields = (
        "title",
        "description",
        "subject__code",
        "class_section__section_name",
        "uploaded_by__username",
    )
    list_filter = (
        "material_type",
        "visibility",
        "is_active",
        "uploaded_at",
    )