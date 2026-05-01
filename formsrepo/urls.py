from django.urls import path
from . import views

urlpatterns = [
    path("", views.forms_repository, name="forms-repository"),
]