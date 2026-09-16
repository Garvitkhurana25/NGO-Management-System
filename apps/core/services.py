"""Business logic for the core app (donors, campaigns, volunteers)."""
from django.db import transaction


# ---------------------------------------------------------------------------
# Donor timeline / aggregation
# ---------------------------------------------------------------------------
def donor_timeline(donor):
    """Return a chronologically ordered list of events for a donor profile (FR-1.4)."""
    events = []

    for comm in donor.communications.order_by("sent_at"):
        events.append({"at": comm.sent_at, "kind": "communication", "detail": f"{comm.get_channel_display()}: {comm.subject}"})

    for donation in donor.donations.order_by("created_at"):
        events.append({"at": donation.created_at, "kind": "donation", "detail": f"{donation.amount} {donation.currency} ({donation.get_status_display()})"})

    events.sort(key=lambda e: e["at"])
    return events


def merge_donors(survivor, *losers, audit_notes=""):
    """Merge one or more donor records into `survivor` (FR-1.3).

    All donations and communications of the losers are reassigned to the
    survivor; the losers are soft-deleted via merged_into. Runs atomically.
    """
    if not survivor.pk:
        raise ValueError("survivor must be saved before merging")

    with transaction.atomic():
        for loser in losers:
            if loser.pk == survivor.pk:
                continue
            for related in ("donations", "communications"):
                for obj in getattr(loser, related).all():
                    setattr(obj, "donor", survivor)
                    obj.save(update_fields=["donor"])
            loser.merged_into = survivor
            loser.is_active = False
            loser.notes = (loser.notes + "\nMerged into #%s. %s" % (survivor.pk, audit_notes)).strip()
            loser.save(update_fields=["merged_into", "is_active", "notes"])
    return survivor


def find_duplicate_donors():
    """Naive duplicate detector: same normalized email or (name, phone) pair."""
    from .models import Donor

    seen = {}
    dupes = []
    for donor in Donor.objects.filter(is_active=True).order_by("created_at"):
        key = donor.email.strip().lower() or (donor.name.strip().lower(), donor.phone.strip())
        if key in seen and key:
            dupes.append({"survivor": seen[key], "duplicate": donor})
        elif key:
            seen[key] = donor
    return dupes


# ---------------------------------------------------------------------------
# Donations
# ---------------------------------------------------------------------------
def successful_donation_amount_sum(donor):
    from django.db.models import Sum

    return donor.donations.get_queryset().aggregate(total=Sum("amount")).get("total") or 0