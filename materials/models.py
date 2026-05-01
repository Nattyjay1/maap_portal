from django.conf import settings
from django.db import models

from academics.models import Subject, ClassSection


class LessonMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = [
        ("lesson", "Lesson"),
        ("module", "Module"),
        ("presentation", "Presentation"),
        ("handout", "Handout"),
        ("activity", "Activity"),
        ("reference", "Reference"),
        ("link", "External Link"),
    ]

    VISIBILITY_CHOICES = [
        ("all", "All Users"),
        ("students", "Students Only"),
        ("faculty", "Faculty Only"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(
        max_length=30,
        choices=MATERIAL_TYPE_CHOICES,
        default="lesson"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_materials"
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_materials"
    )

    file = models.FileField(
        upload_to="lesson_materials/",
        null=True,
        blank=True
    )

    external_link = models.URLField(blank=True)

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="all"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_lesson_materials"
    )

    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title