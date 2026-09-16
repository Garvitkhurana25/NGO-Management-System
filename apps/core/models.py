"""Core domain models: donors, campaigns, donations, volunteers and shifts.

Amounts are stored as INDIAN RUPEES (INR) decimals. At the gateway boundary
(Razorpay) they are converted to paise (amount * 100) and back.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    """Base class providing created_at / updated_at on every concrete model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Donors
# ---------------------------------------------------------------------------
class Tag(TimestampedModel):
    """Free-form label ("monthly", "major donor", "corporate", ...)."""

    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Donor(TimestampedModel):
    class DonorType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        ORGANIZATION = "organization", "Organization"

    donor_type = models.CharField(
        max_length=20, choices=DonorType.choices, default=DonorType.INDIVIDUAL
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=100, blank=True, help_text="How this donor was acquired.")
    tags = models.ManyToManyField(Tag, blank=True, related_name="donors")

    # The auth account this donor record belongs to (self-service donors).
    # Null for records created by staff without a user account.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donor_profile",
    )

    # Deduplication support (FR-1.3). When two donor records are merged, the
    # "losing" record is soft-deleted and points merged_into at the survivor.
    merged_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="merged_records",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["email"])]

    def __str__(self):
        return self.name

    @property
    def total_given(self):
        from django.db.models import Sum

        agg = self.donations.filter(
            status__in=["captured", "succeeded", "part_refunded", "refunded"]
        ).aggregate(total=Sum("amount"))
        return agg["total"] or 0


class DonorCommunication(TimestampedModel):
    """One row per outbound communication to a donor (FR-4.3, audit log)."""

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        LETTER = "letter", "Letter"

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="communications")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    subject = models.CharField(max_length=200, blank=True)
    body_snippet = models.TextField(blank=True)
    sent_at = models.DateTimeField()
    external_id = models.CharField(max_length=200, blank=True, help_text="Provider message id (e.g. email id).")

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.donor} — {self.channel} ({self.sent_at:%Y-%m-%d})"


# ---------------------------------------------------------------------------
# Campaigns & donations
# ---------------------------------------------------------------------------
class Campaign(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    goal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def raised_amount(self):
        from django.db.models import Sum

        agg = self.donations.filter(
            status__in=["captured", "succeeded", "part_refunded", "refunded"]
        ).aggregate(raised=Sum("amount"))
        return agg["raised"] or 0

    @property
    def progress_percent(self):
        # goal_amount/raised_amount can arrive as str (e.g. a DecimalField that
        # was just assigned a string and not yet re-read from the DB, or legacy
        # SQLite-imported rows). Coerce to Decimal so the division never 500s.
        if not self.goal_amount:
            return 0
        try:
            goal = Decimal(self.goal_amount)
            raised = Decimal(self.raised_amount or 0)
        except (TypeError, ValueError):
            return 0
        if not goal:
            return 0
        return round((raised / goal) * 100, 1)


class Donation(TimestampedModel):
    """A single donation, originating from admin entry, a payment link, or a
    Razorpay webhook. Status mirrors the Razorpay payment lifecycle."""

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        ORDER_CREATED = "order_created", "Order created (link sent)"
        PAYMENT_PENDING = "payment_pending", "Payment pending"
        CAPTURED = "captured", "Captured"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        PART_REFUNDED = "part_refunded", "Partially refunded"
        REFUNDED = "refunded", "Refunded"

    class Frequency(models.TextChoices):
        ONE_TIME = "once", "One-time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    donor = models.ForeignKey(Donor, on_delete=models.PROTECT, related_name="donations")
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="donations"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default=settings.DONATION_CURRENCY)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    frequency = models.CharField(
        max_length=12, choices=Frequency.choices, default=Frequency.ONE_TIME
    )
    date = models.DateTimeField(null=True, blank=True, help_text="Time of successful payment, when known.")
    receipt_number = models.CharField(max_length=64, unique=True, blank=True)
    acknowledgement_sent_at = models.DateTimeField(null=True, blank=True)

    # Razorpay identifiers (populated by the payments integration).
    razorpay_order_id = models.CharField(max_length=64, blank=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    razorpay_signature = models.CharField(max_length=128, blank=True)
    razorpay_link_id = models.CharField(max_length=64, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    # Indempotency guard: one canonical record per Razorpay payment/order.
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["razorpay_payment_id"]),
            models.Index(fields=["razorpay_order_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"#{self.pk or '—'} {self.amount} {self.currency} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)

    def _generate_receipt_number(self):
        # Placeholder stamp: YYMM + milliseconds. The final receipt number is
        # issued by the receipts service once the donation is captured, using
        # the canonical primary key. Kept unique here to satisfy the DB unique
        # constraint during the initiated/pending lifecycle.
        from datetime import datetime
        import time

        stamp = datetime.now().strftime("%y%m")
        return f"ACK-{stamp}-{int(time.time() * 1000)}"


# ---------------------------------------------------------------------------
# Volunteers
# ---------------------------------------------------------------------------
class Volunteer(TimestampedModel):
    class BackgroundCheck(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not required"
        PENDING = "pending", "Pending"
        CLEARED = "cleared", "Cleared"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated skills or interests.")
    availability = models.JSONField(default=dict, blank=True, help_text="e.g. {'weekdays': ['evening']}")
    background_check_status = models.CharField(
        max_length=20, choices=BackgroundCheck.choices, default=BackgroundCheck.NOT_REQUIRED
    )
    joined_at = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    # The auth account this volunteer record belongs to (self-service
    # volunteers). Null for records created by staff without a user account.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="volunteer_profile",
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["email"])]

    def __str__(self):
        return self.name

    @property
    def total_hours(self):
        agg = self.signups.filter(status__in=["checked_in", "checked_out", "no_show"]).aggregate(
            total=models.Sum("hours_logged")
        )
        return agg["total"] or 0


class VolunteerShift(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open for signups"
        LOCKED = "locked", "Locked / signups closed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return self.title

    @property
    def filled_slots(self):
        return self.signups.filter(
            status__in=["signed_up", "confirmed", "checked_in", "checked_out"]
        ).count()


class ShiftSignup(TimestampedModel):
    class Status(models.TextChoices):
        SIGNED_UP = "signed_up", "Signed up"
        CONFIRMED = "confirmed", "Confirmed"
        WAITLISTED = "waitlisted", "Waitlisted"
        CHECKED_IN = "checked_in", "Checked in"
        CHECKED_OUT = "checked_out", "Checked out"
        NO_SHOW = "no_show", "No-show"
        CANCELLED = "cancelled", "Cancelled"

    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name="signups")
    shift = models.ForeignKey(VolunteerShift, on_delete=models.CASCADE, related_name="signups")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SIGNED_UP)
    hours_logged = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["volunteer", "shift"], name="uniq_volunteer_shift")
        ]

    def __str__(self):
        return f"{self.volunteer} @ {self.shift} ({self.status})"


# ---------------------------------------------------------------------------
# Events  (M1 — FR-6)
# ---------------------------------------------------------------------------
class Event(TimestampedModel):
    """A fundraising event, drive, or gathering. Links to an optional campaign
    so event revenue flows into the campaign total (FR-6.3)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    capacity = models.PositiveIntegerField(default=0, help_text="0 = unlimited.")
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="0 = free event.")
    campaign = models.ForeignKey(
        Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["-start_at"]

    def __str__(self):
        return self.name

    @property
    def registrations_count(self):
        return self.registrations.exclude(status="cancelled").count()

    @property
    def revenue(self):
        """Sum of paid ticket amounts (monetary, not paise)."""
        from django.db.models import Sum

        agg = self.registrations.filter(
            status__in=["confirmed", "attended"],
            paid_amount__gt=0,
        ).aggregate(total=Sum("paid_amount"))
        return agg["total"] or 0


class EventRegistration(TimestampedModel):
    """An individual registration (ticket) for an event (FR-6.2)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        CONFIRMED = "confirmed", "Confirmed"
        ATTENDED = "attended", "Attended"
        WAITLISTED = "waitlisted", "Waitlisted"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    donor = models.ForeignKey(Donor, null=True, blank=True, on_delete=models.SET_NULL, related_name="event_registrations")
    volunteer = models.ForeignKey(Volunteer, null=True, blank=True, on_delete=models.SET_NULL, related_name="event_registrations")
    attendee_name = models.CharField(max_length=200, blank=True)
    attendee_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        label = self.attendee_name or str(self.donor) or str(self.volunteer) or f"#{self.pk}"
        return f"{label} → {self.event}"


# ---------------------------------------------------------------------------
# Accounts & roles
# ---------------------------------------------------------------------------
class UserProfile(TimestampedModel):
    """The role a registered (self-service) account plays on the platform.

    Staff and superusers have no UserProfile; they are identified by Django's
    is_staff / is_superuser flags. Registered end-users are either a volunteer
    (registers for events) or a donor (makes donations), reflected in ``role``
    and in the linked ``Volunteer`` / ``Donor`` record.
    """

    class Role(models.TextChoices):
        VOLUNTEER = "volunteer", "Volunteer"
        DONOR = "donor", "Donor"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"