from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File

from academics.models import Subject, ClassSection
from materials.models import LessonMaterial

User = get_user_model()

demo_dir = Path(settings.MEDIA_ROOT) / "demo_lesson_materials"
demo_dir.mkdir(parents=True, exist_ok=True)

faculty = User.objects.filter(role="faculty").first()

sample_data = [
    {
        "title": "Fundamentals of Navigation - Week 1 Module",
        "description": "Introductory learning material for basic navigation concepts.",
        "material_type": "module",
        "subject_code": "NAV101",
        "section": "BSMT-1A",
        "filename": "nav101_week1_module.txt",
    },
    {
        "title": "COLREG Quick Reference Guide",
        "description": "Summary reference material for rules of the road and COLREG.",
        "material_type": "reference",
        "subject_code": "COLREG101",
        "section": "BSMT-1A",
        "filename": "colreg_quick_reference.txt",
    },
    {
        "title": "Marine Engineering Safety Handout",
        "description": "Safety handout for introductory marine engineering class.",
        "material_type": "handout",
        "subject_code": "ENG101",
        "section": "BSME-1A",
        "filename": "eng101_safety_handout.txt",
    },
]

for item in sample_data:
    source_file = demo_dir / item["filename"]

    if not source_file.exists():
        source_file.write_text(
            f"{item['title']}\n\n{item['description']}\n\nDemo lesson material for prototype presentation.",
            encoding="utf-8"
        )

    subject = Subject.objects.filter(code=item["subject_code"]).first()
    class_section = ClassSection.objects.filter(
        subject=subject,
        section_name=item["section"]
    ).first()

    material, created = LessonMaterial.objects.get_or_create(
        title=item["title"],
        defaults={
            "description": item["description"],
            "material_type": item["material_type"],
            "subject": subject,
            "class_section": class_section,
            "uploaded_by": faculty,
            "visibility": "all",
            "is_active": True,
        }
    )

    material.description = item["description"]
    material.material_type = item["material_type"]
    material.subject = subject
    material.class_section = class_section
    material.uploaded_by = faculty
    material.visibility = "all"
    material.is_active = True

    if not material.file:
        with open(source_file, "rb") as f:
            material.file.save(item["filename"], File(f), save=False)

    material.save()

print("Demo lesson materials created.")