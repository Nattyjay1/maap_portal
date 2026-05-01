from django import forms
from .models import FacultyEvaluation


class FacultyEvaluationForm(forms.ModelForm):
    class Meta:
        model = FacultyEvaluation
        fields = [
            "faculty",
            "evaluator_type",
            "evaluation_score",
            "remarks",
            "term",
            "school_year",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

        self.fields["remarks"].widget.attrs.update({
            "rows": 3,
            "placeholder": "Optional evaluation remarks"
        })
        self.fields["evaluation_score"].widget.attrs.update({
            "step": "0.01",
            "min": "0",
            "max": "100",
        })
        

class FacultySelfEvaluationForm(forms.ModelForm):
    class Meta:
        model = FacultyEvaluation
        fields = [
            "evaluation_score",
            "remarks",
            "term",
            "school_year",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

        self.fields["evaluation_score"].widget.attrs.update({
            "step": "0.01",
            "min": "0",
            "max": "100",
            "placeholder": "Enter self-evaluation score"
        })

        self.fields["remarks"].widget.attrs.update({
            "rows": 4,
            "placeholder": "Write your self-evaluation remarks or reflection"
        })

        self.fields["term"].widget.attrs.update({
            "placeholder": "Example: 1st Semester"
        })

        self.fields["school_year"].widget.attrs.update({
            "placeholder": "Example: 2025-2026"
        })