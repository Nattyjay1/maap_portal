from django import forms
from .models import Grade


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = [
            "quiz_total",
            "activity_total",
            "exam_total",
            "lab_total",
            "attendance_score",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "max": "100",
            })
            

class GradeEditForm(forms.ModelForm):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Enter reason for changing the grade"
        })
    )

    class Meta:
        model = Grade
        fields = [
            "quiz_total",
            "activity_total",
            "exam_total",
            "lab_total",
            "attendance_score",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in [
            "quiz_total",
            "activity_total",
            "exam_total",
            "lab_total",
            "attendance_score",
        ]:
            self.fields[field_name].widget.attrs.update({
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "max": "100",
            })