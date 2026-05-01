from django.conf import settings
from django.db import models


class AcademicForm(models.Model):
    CATEGORY_CHOICES = [
        ("student", "Student Form"),
        ("faculty", "Faculty Form"),
        ("admin", "Administrative Form"),
        ("certification", "Certification Form"),
        ("general", "General Form"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")
    file = models.FileField(upload_to="academic_forms/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_forms"
    )
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title