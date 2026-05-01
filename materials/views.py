from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LessonMaterialForm
from .models import LessonMaterial


@login_required
def lesson_materials_repository(request):
    can_upload = request.user.role in ["admin", "faculty"]

    if request.method == "POST":
        if not can_upload:
            messages.error(request, "You are not allowed to upload lesson materials.")
            return redirect("lesson-materials")

        form = LessonMaterialForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            material = form.save(commit=False)
            material.uploaded_by = request.user
            material.save()

            messages.success(request, "Lesson material uploaded successfully.")
            return redirect("lesson-materials")
    else:
        form = LessonMaterialForm(user=request.user)

    materials = (
        LessonMaterial.objects
        .filter(is_active=True)
        .select_related("subject", "class_section", "uploaded_by")
        .order_by("-uploaded_at")
    )

    # Role-based visibility
    if request.user.role == "student":
        materials = materials.exclude(visibility="faculty")
    elif request.user.role == "faculty":
        materials = materials.exclude(visibility="students")
    elif request.user.role != "admin":
        materials = materials.filter(visibility="all")

    # Optional filters
    selected_type = request.GET.get("type", "")
    selected_keyword = request.GET.get("q", "")

    if selected_type:
        materials = materials.filter(material_type=selected_type)

    if selected_keyword:
        materials = materials.filter(title__icontains=selected_keyword)

    context = {
        "page_title": "Lesson / Materials",
        "form": form,
        "materials": materials,
        "can_upload": can_upload,
        "selected_type": selected_type,
        "selected_keyword": selected_keyword,
        "material_type_choices": LessonMaterial.MATERIAL_TYPE_CHOICES,
    }

    return render(request, "materials/lesson_materials_repository.html", context)