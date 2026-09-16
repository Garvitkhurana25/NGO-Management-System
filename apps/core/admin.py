from django.contrib import admin

from .models import (
    Campaign,
    Donation,
    Donor,
    DonorCommunication,
    Event,
    EventRegistration,
    ShiftSignup,
    Tag,
    Volunteer,
    VolunteerShift,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 0
    fields = ("amount", "currency", "status", "date", "campaign", "razorpay_payment_id")
    readonly_fields = ("razorpay_payment_id",)
    can_delete = False


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    fields = ("attendee_name", "attendee_email", "donor", "volunteer", "status", "paid_amount")
    can_delete = False


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "donor_type", "company", "total_given", "is_active")
    list_filter = ("donor_type", "is_active", "tags")
    search_fields = ("name", "email", "phone", "company")
    filter_horizontal = ("tags",)
    inlines = [DonationInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "donor_type", "email", "phone", "company", "source")}),
        ("Relationships", {"fields": ("tags",)}),
        ("Deduplication", {"fields": ("merged_into", "is_active")}),
        ("Notes & audit", {"fields": ("notes", "created_at", "updated_at")}),
    )

    def total_given(self, obj):
        return f"₹{obj.total_given:,.2f}"

    total_given.short_description = "Total given"


@admin.register(DonorCommunication)
class DonorCommunicationAdmin(admin.ModelAdmin):
    list_display = ("donor", "channel", "subject", "sent_at")
    list_filter = ("channel",)
    search_fields = ("donor__name", "donor__email", "subject")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "goal_amount", "raised_amount", "progress_percent", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [DonationInline]

    def raised_amount(self, obj):
        return f"₹{obj.raised_amount:,.2f}"

    def progress_percent(self, obj):
        return f"{obj.progress_percent}%"

    raised_amount.short_description = "Raised"
    progress_percent.short_description = "Progress"


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("pk", "donor", "campaign", "amount", "currency", "status", "date", "receipt_number")
    list_filter = ("status", "currency", "frequency")
    search_fields = ("donor__name", "donor__email", "receipt_number", "razorpay_payment_id", "razorpay_order_id")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Donor", {"fields": ("donor", "campaign")}),
        ("Payment", {"fields": ("amount", "currency", "frequency", "status", "date", "refund_amount")}),
        ("Razorpay", {"fields": ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature", "razorpay_link_id")}),
        ("Receipt & audit", {"fields": ("receipt_number", "acknowledgement_sent_at", "notes", "created_at", "updated_at")}),
    )


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "background_check_status", "is_active", "total_hours")
    list_filter = ("background_check_status", "is_active")
    search_fields = ("name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VolunteerShift)
class VolunteerShiftAdmin(admin.ModelAdmin):
    list_display = ("title", "start_at", "end_at", "filled_slots", "capacity", "status")
    list_filter = ("status",)
    search_fields = ("title", "description", "location")


@admin.register(ShiftSignup)
class ShiftSignupAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "shift", "status", "hours_logged", "checked_in_at")
    list_filter = ("status",)
    search_fields = ("volunteer__name", "shift__title")
    list_editable = ("status", "hours_logged")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_at", "end_at", "registrations_count", "revenue", "capacity", "campaign", "status")
    list_filter = ("status",)
    search_fields = ("name", "description", "location")
    inlines = [EventRegistrationInline]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "attendee_name", "attendee_email", "donor", "volunteer", "status", "paid_amount", "checked_in_at")
    list_filter = ("status",)
    search_fields = ("attendee_name", "attendee_email", "donor__name", "volunteer__name", "event__name")
    list_editable = ("status",)