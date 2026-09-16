"""Root URL configuration for the NGO Operations Management Platform."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("api.urls")),
    path("webhooks/", include("payments.urls")),
]