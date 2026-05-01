from django.conf import settings
from django.db import models

from decimal import Decimal, ROUND_HALF_UP


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class FacultyProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faculty_profile"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_members"
    )
    employee_id = models.CharField(max_length=30, unique=True)
    designation = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students"
    )
    student_number = models.CharField(max_length=30, unique=True)
    year_level = models.CharField(max_length=20)
    section = models.CharField(max_length=50)

    class Meta:
        ordering = ["student_number"]

    def __str__(self):
        return f"{self.student_number} - {self.user.get_full_name() or self.user.username}"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    units = models.PositiveIntegerField(default=3)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subjects"
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class ClassSection(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="class_sections"
    )
    faculty = models.ForeignKey(
        FacultyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes_handled"
    )
    section_name = models.CharField(max_length=50)
    term = models.CharField(max_length=30)
    school_year = models.CharField(max_length=20)
    schedule = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["school_year", "term", "section_name"]
        unique_together = ("subject", "section_name", "term", "school_year")

    def __str__(self):
        return f"{self.subject.code} - {self.section_name} ({self.term} {self.school_year})"


class AdvisorySection(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="advisory_sections"
    )
    adviser = models.ForeignKey(
        FacultyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advisory_sections"
    )
    section_name = models.CharField(max_length=50)
    year_level = models.CharField(max_length=10)
    term = models.CharField(max_length=30)
    school_year = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["department__code", "year_level", "section_name"]
        unique_together = ("section_name", "term", "school_year")

    def __str__(self):
        adviser_name = self.adviser.user.get_full_name() if self.adviser else "No adviser"
        return f"{self.section_name} - {self.term} {self.school_year} ({adviser_name})"


class Enrollment(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student__student_number"]
        unique_together = ("student", "class_section")

    def __str__(self):
        return f"{self.student.student_number} -> {self.class_section}"


class Grade(models.Model):
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="grade"
    )
    quiz_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    activity_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    lab_total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    attendance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    final_grade = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks = models.CharField(max_length=20, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["enrollment__class_section", "enrollment__student__student_number"]

    def compute_final_grade(self):
        total = (
            Decimal(self.quiz_total) * Decimal("0.30") +
            Decimal(self.activity_total) * Decimal("0.20") +
            Decimal(self.exam_total) * Decimal("0.30") +
            Decimal(self.lab_total) * Decimal("0.10") +
            Decimal(self.attendance_score) * Decimal("0.10")
        )
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.final_grade = self.compute_final_grade()
        self.remarks = "Passed" if self.final_grade >= Decimal("75.00") else "Failed"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enrollment.student.student_number} - {self.enrollment.class_section.subject.code} ({self.final_grade})"


class GradeAdjustmentLog(models.Model):
    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="adjustment_logs"
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grade_adjustments"
    )
    field_changed = models.CharField(max_length=50)
    old_value = models.CharField(max_length=50)
    new_value = models.CharField(max_length=50)
    reason = models.TextField()
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-edited_at"]

    def __str__(self):
        return f"{self.grade.enrollment.student.student_number} | {self.field_changed} | {self.edited_at:%Y-%m-%d %H:%M}"


class AttendanceSummary(models.Model):
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="attendance_summary"
    )
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)

    attendance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["enrollment__class_section", "enrollment__student__student_number"]

    def compute_attendance_percent(self):
        total_meetings = self.present_count + self.absent_count + self.late_count
        if total_meetings == 0:
            return Decimal("0.00")

        attended = Decimal(self.present_count + self.late_count)
        percent = (attended / Decimal(total_meetings)) * Decimal("100")
        return percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self.attendance_percent = self.compute_attendance_percent()

        if self.attendance_percent >= Decimal("90.00"):
            self.status = "Good"
        elif self.attendance_percent >= Decimal("75.00"):
            self.status = "Warning"
        else:
            self.status = "Critical"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.enrollment.student.student_number} - {self.enrollment.class_section.subject.code} ({self.attendance_percent}%)"
    