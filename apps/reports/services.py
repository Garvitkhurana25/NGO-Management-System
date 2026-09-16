"""Aggregation queries behind the dashboard and scheduled reports (FR-5.x).

All functions are pure DB aggregates; scheduled export is handled either by a
management command or by scheduling a URL fetch (see README).
"""
from datetime import datetime, timedelta, timezone

from core.models import Donation, ShiftSignup, Volunteer, VolunteerShift


def _donation_queryset(start=None, end=None, statuses=None):
    qs = Donation.objects.all()
    if statuses:
        qs = qs.filter(status__in=statuses)
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    return qs


def donation_totals(start=None, end=None):
    """Total raised and count of received donations in a period."""
    from django.db.models import Count, Sum

    qs = _donation_queryset(
        start, end, statuses=["captured", "succeeded", "part_refunded", "refunded"]
    )
    agg = qs.aggregate(total=Sum("amount"), count=Count("pk"))
    return {"total": agg["total"] or 0, "count": agg["count"], "currency": "INR"}


def campaign_performance():
    """Per-campaign raised vs goal (FR-3.2 / FR-5.2)."""
    from core.models import Campaign

    return [
        {
            "id": c.pk,
            "name": c.name,
            "status": c.status,
            "goal": c.goal_amount,
            "raised": c.raised_amount,
            "progress_percent": c.progress_percent,
        }
        for c in Campaign.objects.all()
    ]


def volunteer_hours_summary():
    """Active volunteers, hours logged, and upcoming shifts (FR-2.4)."""
    from django.db.models import Sum

    active_volunteers = Volunteer.objects.filter(is_active=True).count()
    hours = ShiftSignup.objects.filter(
        status__in=["checked_in", "checked_out", "no_show"]
    ).aggregate(total=Sum("hours_logged"))["total"] or 0
    upcoming_shifts = VolunteerShift.objects.filter(
        start_at__gte=datetime.now(timezone.utc), status="open"
    ).count()
    return {
        "active_volunteers": active_volunteers,
        "hours_logged": hours,
        "upcoming_open_shifts": upcoming_shifts,
    }


def donation_trend(months=6):
    """Last `months` months of captured donations, oldest-first, for the trend chart.

    Returns [{"month": "2026-04", "total": Decimal, "count": int}, ...].
    Months with no donations appear with a zero total so the axis is complete.

    Bucketing happens in Python (not SQL) so the query is identical on SQLite
    and Postgres — fine at NGO scale, where a 6-month window is < 10k rows.
    """
    from calendar import monthrange

    from django.db.models import Sum
    from django.utils import timezone as tz

    today = tz.localtime(tz.now())
    buckets = []
    for delta in range(months - 1, -1, -1):
        y, m = _shift_month(today.year, today.month, -delta)
        _, days = monthrange(y, m)
        buckets.append(
            {
                "month": f"{y:04d}-{m:02d}",
                "start": tz.make_aware(datetime(y, m, 1)),
                "end": tz.make_aware(datetime(y, m, days, 23, 59, 59)),
                "total": 0,
                "count": 0,
            }
        )

    totals = {}
    for bucket in buckets:
        agg = _donation_queryset(
            bucket["start"],
            bucket["end"],
            statuses=["captured", "succeeded", "part_refunded", "refunded"],
        ).filter(date__isnull=False)
        row = agg.aggregate(total=Sum("amount"))
        totals[bucket["month"]] = row["total"] or 0
        bucket["total"] = totals[bucket["month"]]
        bucket["count"] = agg.count()

    return buckets


def _shift_month(year, month, delta):
    total = year * 12 + (month - 1) + delta
    return divmod(total, 12)[0], divmod(total, 12)[1] + 1


def recent_donations(limit=10):
    """Most recent donor-facing donations for the dashboard table."""
    from core.models import Donation

    return [
        {
            "donor": d.donor.name,
            "email": d.donor.email,
            "campaign": d.campaign.name if d.campaign else "",
            "amount": d.amount,
            "currency": d.currency,
            "status": d.status,
            "date": d.date.isoformat() if d.date else "",
            "receipt": d.receipt_number,
        }
        for d in Donation.objects.select_related("donor", "campaign").order_by("-created_at")[:limit]
    ]


def monthly_donation_rows(year, month):
    """Rows for a monthly donation report (FR-5.2)."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    donations = (
        _donation_queryset(start, end, statuses=["captured", "succeeded", "part_refunded", "refunded"])
        .select_related("donor", "campaign")
    )
    return [
        {
            "donor": d.donor.name,
            "email": d.donor.email,
            "campaign": d.campaign.name if d.campaign else "",
            "amount": d.amount,
            "currency": d.currency,
            "status": d.status,
            "date": d.date.isoformat() if d.date else "",
            "receipt": d.receipt_number,
        }
        for d in donations
    ]