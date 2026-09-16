from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="api-dashboard"),
    path("reports/monthly-donations.csv", views.monthly_donation_export, name="api-monthly-donations-csv"),
]