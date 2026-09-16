from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.auth_login, name="api-login"),
    path("auth/logout/", views.auth_logout, name="api-logout"),
    path("auth/me/", views.auth_me, name="api-me"),
    path("auth/register/", views.auth_register, name="api-register"),
    path("auth/csrf/", views.auth_csrf, name="api-csrf"),
    path("me/registrations/", views.me_registrations, name="api-me-registrations"),
    path("me/donations/", views.me_donations, name="api-me-donations"),
    path("me/campaigns/", views.me_campaigns, name="api-me-campaigns"),
    path("me/summary/", views.me_summary, name="api-me-summary"),
    path("me/profile/", views.me_profile_update, name="api-me-profile-update"),
    path("users/", views.user_list, name="api-user-list"),
    path("users/create/", views.user_create, name="api-user-create"),
    path("users/<int:pk>/", views.user_update, name="api-user-update"),
    path("users/<int:pk>/delete/", views.user_delete, name="api-user-delete"),
]