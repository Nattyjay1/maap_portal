from django import forms

from .models import LessonMaterial


class LessonMaterialForm(forms.ModelForm):
    class Meta:
        model = LessonMaterial
        fields = [
            "title",
            "description",
            "material_type",
            "subject",
            "class_section",
            "file",
            "external_link",
            "visibility",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        self.fields["description"].widget.attrs.update({
            "rows": 3,
            "placeholder": "Short description of the lesson or material"
        })

        self.fields["external_link"].widget.attrs.update({
            "placeholder": "Optional: paste a Google Drive, YouTube, or reference link"
        })

        self.fields["is_active"].widget.attrs.update({
            "class": "form-check-input"
        })

        # If faculty uploads, show only their assigned class sections.
        if user and getattr(user, "role", None) == "faculty" and hasattr(user, "faculty_profile"):
            self.fields["class_section"].queryset = (
                self.fields["class_section"]
                .queryset
                .filter(faculty=user.faculty_profile)
            )