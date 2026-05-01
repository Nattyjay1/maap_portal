from django import forms
from .models import AcademicForm


class AcademicFormUploadForm(forms.ModelForm):
    class Meta:
        model = AcademicForm
        fields = ["title", "description", "category", "file", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        self.fields["description"].widget.attrs.update({
            "rows": 3,
            "placeholder": "Short description of the form"
        })

        self.fields["is_active"].widget.attrs.update({"class": "form-check-input"})