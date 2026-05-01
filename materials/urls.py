from django.urls import path

from . import views

urlpatterns = [
    path("", views.lesson_materials_repository, name="lesson-materials"),
]