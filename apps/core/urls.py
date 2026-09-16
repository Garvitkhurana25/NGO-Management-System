from django.urls import path

from . import views

urlpatterns = [
    path("donors/", views.donor_list, name="api-donor-list"),
    path("donors/<int:pk>/", views.donor_detail, name="api-donor-detail"),
    path("donors/create/", views.donor_create, name="api-donor-create"),
    path("donors/<int:pk>/update/", views.donor_update, name="api-donor-update"),
    path("donors/<int:pk>/delete/", views.donor_delete, name="api-donor-delete"),
    path("donations/", views.donation_list, name="api-donation-list"),
    path("donations/create/", views.donation_create, name="api-donation-create"),
    path("campaigns/", views.campaign_list, name="api-campaign-list"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="api-campaign-detail"),
    path("campaigns/create/", views.campaign_create, name="api-campaign-create"),
    path("campaigns/<int:pk>/update/", views.campaign_update, name="api-campaign-update"),
    path("campaigns/<int:pk>/delete/", views.campaign_delete, name="api-campaign-delete"),
    path("volunteers/", views.volunteer_list, name="api-volunteer-list"),
    path("volunteers/create/", views.volunteer_create, name="api-volunteer-create"),
    path("volunteers/<int:pk>/update/", views.volunteer_update, name="api-volunteer-update"),
    path("volunteers/<int:pk>/delete/", views.volunteer_delete, name="api-volunteer-delete"),
    path("events/", views.event_list, name="api-event-list"),
    path("events/create/", views.event_create, name="api-event-create"),
    path("events/<int:pk>/update/", views.event_update, name="api-event-update"),
    path("events/<int:pk>/delete/", views.event_delete, name="api-event-delete"),
    path("events/<int:pk>/register/", views.event_register, name="api-event-register"),
    path("events/<int:pk>/cancel/", views.event_cancel, name="api-event-cancel"),
    path("events/registrations/pending/", views.event_registrations_pending, name="api-event-registrations-pending"),
    path("event-registrations/<int:pk>/confirm/", views.event_registration_confirm, name="api-event-registration-confirm"),
    path("volunteers/<int:pk>/background-verify/", views.volunteer_background_verify, name="api-volunteer-background-verify"),
    path("campaigns/<int:pk>/donate/", views.campaign_donate, name="api-campaign-donate"),
    path("campaigns/<int:pk>/checkout/", views.campaign_checkout, name="api-campaign-checkout"),
    path("donations/verify/", views.donation_verify, name="api-donation-verify"),
]