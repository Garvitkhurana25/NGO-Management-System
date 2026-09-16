"""Payment infrastructure models — Razorpay event log and payment links."""
from django.conf import settings
from django.db import models


class RazorpayWebhookEvent(models.Model):
    """Immutable audit log of every Razorpay webhook received (FR-1.4 / FR-4.3)."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        DUPLICATE = "duplicate", "Duplicate"
        FAILED = "failed", "Failed"
        SIGNATURE_INVALID = "signature_invalid", "Signature invalid"

    event_id = models.CharField(
        max_length=64, unique=True, help_text="Razorpay event.id (globally unique)."
    )
    event_type = models.CharField(
        max_length=80, help_text="Razorpay event.event (e.g. order.paid)."
    )
    payload = models.JSONField(help_text="Full Razorpay event payload.")
    razorpay_order_id = models.CharField(max_length=64, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"


class PaymentLink(models.Model):
    """Tracks a Razorpay Payment Link created for a donor/donation (FR-2.2)."""

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        ACTIVE = "active", "Active"
        PARTIAL = "partial", "Partially paid"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        PAID = "paid", "Paid"

    link_id = models.CharField(max_length=64, blank=True, help_text="Razorpay payment_link.id")
    short_url = models.URLField(blank=True, help_text="Public URL donors click to pay.")
    donor = models.ForeignKey(
        "core.Donor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_links",
    )
    donation = models.ForeignKey(
        "core.Donation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_links",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default=settings.DONATION_CURRENCY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PaymentLink #{self.pk} ({self.get_status_display()}) — ₹{self.amount}"