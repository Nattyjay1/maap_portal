from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AcademicFormUploadForm
from .models import AcademicForm


@login_required
def forms_repository(request):
    if request.method == "POST":
        if request.user.role != "admin":
            messages.error(request, "Only admin users can upload forms.")
            return redirect("forms-repository")

        form = AcademicFormUploadForm(request.POST, request.FILES)
        if form.is_valid():
            academic_form = form.save(commit=False)
            academic_form.uploaded_by = request.user
            academic_form.save()
            messages.success(request, "Form uploaded successfully.")
            return redirect("forms-repository")
    else:
        form = AcademicFormUploadForm()

    forms = AcademicForm.objects.filter(is_active=True).order_by("category", "title")

    context = {
        "page_title": "Forms Repository",
        "form": form,
        "forms": forms,
    }

    return render(request, "formsrepo/forms_repository.html", context)