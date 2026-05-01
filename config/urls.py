from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("academics/", include("academics.urls")),
    path("evaluations/", include("evaluations.urls")),
    path("forms/", include("formsrepo.urls")),
    path("reports/", include("reports.urls")),
    
    path("analytics/", include("analytics_app.urls")),
    path("materials/", include("materials.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)