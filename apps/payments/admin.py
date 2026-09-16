from django.contrib import admin

from .models import PaymentLink, RazorpayWebhookEvent


@admin.register(RazorpayWebhookEvent)
class RazorpayWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "status", "razorpay_order_id", "razorpay_payment_id", "received_at", "processed_at")
    list_filter = ("event_type", "status")
    search_fields = ("event_id", "razorpay_order_id", "razorpay_payment_id")
    readonly_fields = ("event_id", "event_type", "payload", "razorpay_order_id", "razorpay_payment_id", "received_at")
    date_hierarchy = "received_at"


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = ("pk", "donor", "donation", "amount", "status", "short_url", "created_at", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("donor__name", "donor__email", "short_url", "link_id")
    readonly_fields = ("link_id", "short_url", "created_at")