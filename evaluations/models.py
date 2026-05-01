from django.db import models
from academics.models import FacultyProfile


class FacultyEvaluation(models.Model):
    EVALUATOR_TYPE_CHOICES = [
        ("student", "Student"),
        ("peer", "Peer"),
        ("admin", "Admin"),
        ("self", "Self-Evaluation"),
    ]

    faculty = models.ForeignKey(
        FacultyProfile,
        on_delete=models.CASCADE,
        related_name="evaluations"
    )
    evaluator_type = models.CharField(
        max_length=20,
        choices=EVALUATOR_TYPE_CHOICES,
        default="student"
    )
    evaluation_score = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(blank=True)
    term = models.CharField(max_length=30)
    school_year = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.faculty.employee_id} - {self.evaluation_score} ({self.term} {self.school_year})"