import json
import logging
from functools import wraps
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, OperationalError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_http_methods

from .models import (
    Campaign,
    Donor,
    Donation,
    Event,
    EventRegistration,
    Tag,
    UserProfile,
    Volunteer,
    VolunteerShift,
)
from .services import donor_timeline
from payments.services import (
    create_razorpay_order,
    is_razorpay_configured,
    verify_payment_signature,
)

logger = logging.getLogger("core")


def api_login_required(view):
    """Like @login_required but returns a JSON 403 for unauthenticated API
    requests instead of redirecting to the admin login page (which returns HTML
    and confuses fetch clients).

    AuthenticationMiddleware populates ``request.user`` for every request, so
    the is_authenticated check is always safe here.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required. Please log in."},
                status=403,
            )
        return view(request, *args, **kwargs)

    return wrapper


def user_role(user):
    """The role ('volunteer' | 'donor') a registered account plays, else None.

    Staff/superusers have no UserProfile and therefore no role; Django's
    is_staff / is_superuser flags cover their permissions.
    """
    try:
        profile = getattr(user, "profile", None)
    except OperationalError:
        # Migration-lag guard: runserver auto-reloads code faster than `migrate`
        # applies it, so the profile table may briefly not exist. Degrade to
        # role-less instead of letting the whole /auth/me/ probe 500.
        return None
    return profile.role if profile is not None else None


def _admin_required(view):
    """Staff/view endpoints that are reserved for the admin (superuser).

    Donors and volunteers manage their own profiles through the self-service
    ``/api/me/profile/`` endpoint, so the staff screens are view + walk-in
    creation only; editing or removing a person's record is an admin action.
    """

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({"error": "Admin permission required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


def _staff_required(view):
    """Any staff member (admins included — superusers are staff too).

    The approval workflows that staff run day-to-day — accepting event signups
    and clearing background checks — live here, while general donor/volunteer
    editing stays admin-only via ``_admin_required``.
    """

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({"error": "Staff permission required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


def _campaign_goal_guard(camp, amount):
    """Ensure a new donation does not push a campaign past its goal.

    Returns None when the donation may proceed, otherwise an error message.
    ``goal_amount`` of 0 means "no goal" — unlimited until closed by staff.
    """
    if not camp.goal_amount or camp.goal_amount <= 0:
        return None
    remaining = Decimal(camp.goal_amount) - Decimal(camp.raised_amount)
    if remaining <= 0:
        return "This campaign has reached its goal and no longer accepts donations."
    if Decimal(str(amount)) > remaining:
        return f"The campaign needs only ₹{remaining:g} more to reach its goal — please enter an amount up to that."
    return None


def _json_donation(donation):
    return {
        "id": donation.pk,
        "donor": donation.donor.name,
        "campaign": donation.campaign.name if donation.campaign else None,
        "amount": str(donation.amount),
        "currency": donation.currency,
        "status": donation.status,
        "date": donation.date.isoformat() if donation.date else None,
        "receipt_number": donation.receipt_number,
        "razorpay_payment_id": donation.razorpay_payment_id,
    }


@require_GET
def donor_list(request):
    """Lightweight JSON API: /api/donors/"""
    donors = Donor.objects.filter(is_active=True).select_related("merged_into")
    items = [
        {
            "id": donor.pk,
            "name": donor.name,
            "email": donor.email,
            "phone": donor.phone,
            "type": donor.donor_type,
            "company": donor.company,
            "total_given": str(donor.total_given),
            "tags": [t.name for t in donor.tags.all()],
        }
        for donor in donors
    ]
    return JsonResponse({"count": len(items), "results": items})


@require_GET
def donation_list(request):
    """Lightweight JSON API: /api/donations/"""
    donations = Donation.objects.all().select_related("donor", "campaign")[:500]
    results = [_json_donation(d) for d in donations]
    return JsonResponse({"count": len(results), "results": results})


@require_GET
def campaign_list(request):
    """Lightweight JSON API: /api/campaigns/ (includes progress)"""
    campaigns = Campaign.objects.all().order_by("-created_at")
    items = [
        {
            "id": camp.pk,
            "name": camp.name,
            "slug": camp.slug,
            "status": camp.status,
            "goal": str(camp.goal_amount),
            "raised": str(camp.raised_amount),
            "progress_percent": camp.progress_percent,
        }
        for camp in campaigns
    ]
    return JsonResponse({"count": len(items), "results": items})


@require_GET
def donor_detail(request, pk):
    """GET /api/donors/<id>/ — donor profile + timeline (FR-1.4)."""
    try:
        donor = Donor.objects.get(pk=pk)
    except Donor.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    return JsonResponse(
        {
            "id": donor.pk,
            "name": donor.name,
            "email": donor.email,
            "phone": donor.phone,
            "type": donor.donor_type,
            "company": donor.company,
            "source": donor.source,
            "total_given": str(donor.total_given),
            "tags": [t.name for t in donor.tags.all()],
            "timeline": [
                {
                    "at": e["at"].isoformat() if e["at"] else None,
                    "kind": e["kind"],
                    "detail": e["detail"],
                }
                for e in donor_timeline(donor)
            ],
        }
    )


@require_GET
def campaign_detail(request, pk):
    """GET /api/campaigns/<id>/ — campaign + linked donations."""
    try:
        campaign = Campaign.objects.get(pk=pk)
    except Campaign.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    donations = campaign.donations.select_related("donor").order_by("-created_at")
    return JsonResponse(
        {
            "id": campaign.pk,
            "name": campaign.name,
            "slug": campaign.slug,
            "status": campaign.status,
            "goal": str(campaign.goal_amount),
            "raised": str(campaign.raised_amount),
            "progress_percent": campaign.progress_percent,
            "description": campaign.description,
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
            "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
            "donations": [_json_donation(d) for d in donations],
        }
    )


@require_GET
def volunteer_list(request):
    """Lightweight JSON API: /api/volunteers/"""
    volunteers = Volunteer.objects.filter(is_active=True)
    items = [
        {
            "id": vol.pk,
            "name": vol.name,
            "email": vol.email,
            "phone": vol.phone,
            "total_hours": str(vol.total_hours),
            "joined_at": vol.joined_at.isoformat() if vol.joined_at else None,
            "background_check_status": vol.background_check_status,
        }
        for vol in volunteers
    ]
    return JsonResponse({"count": len(items), "results": items})


@require_GET
def event_list(request):
    """Lightweight JSON API: /api/events/ (FR-6)"""
    events = Event.objects.all().select_related("campaign")
    items = [
        {
            "id": ev.pk,
            "name": ev.name,
            "start_at": ev.start_at.isoformat(),
            "end_at": ev.end_at.isoformat(),
            "location": ev.location,
            "capacity": ev.capacity,
            "ticket_price": str(ev.ticket_price),
            "campaign": ev.campaign.name if ev.campaign else None,
            "status": ev.status,
            "registrations": ev.registrations_count,
            "revenue": str(ev.revenue),
        }
        for ev in events
    ]
    return JsonResponse({"count": len(items), "results": items})


# ---------------------------------------------------------------------------
# Mutations (staff only)
# ---------------------------------------------------------------------------
def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _set_tags(donor, tag_names):
    tags = []
    for name in set((n or "").strip() for n in (tag_names or [])):
        if name:
            tags.append(Tag.objects.get_or_create(name=name)[0])
    donor.tags.set(tags)


def _donor_payload(donor):
    return {
        "id": donor.pk,
        "name": donor.name,
        "email": donor.email,
        "phone": donor.phone,
        "type": donor.donor_type,
        "company": donor.company,
        "source": donor.source,
        "total_given": str(donor.total_given),
        "tags": [t.name for t in donor.tags.all()],
    }


@login_required
@require_http_methods(["POST"])
def donor_create(request):
    data = _json_body(request)
    if not data or not (data.get("name") or "").strip():
        return JsonResponse({"error": "name is required."}, status=400)

    donor = Donor.objects.create(
        name=(data["name"] or "").strip(),
        donor_type=data.get("donor_type", Donor.DonorType.INDIVIDUAL),
        email=(data.get("email") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        company=(data.get("company") or "").strip(),
        source=(data.get("source") or "").strip(),
    )
    if data.get("tags") is not None:
        _set_tags(donor, data["tags"])
    return JsonResponse({"donor": _donor_payload(donor)}, status=201)


@_admin_required
@require_http_methods(["PATCH"])
def donor_update(request, pk):
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        donor = Donor.objects.get(pk=pk)
    except Donor.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    for field in ("name", "email", "phone", "company", "source"):
        if field in data and isinstance(data[field], str):
            setattr(donor, field, data[field].strip())
    if "donor_type" in data and data["donor_type"] in {c[0] for c in Donor.DonorType.choices}:
        donor.donor_type = data["donor_type"]
    if data.get("tags") is not None:
        _set_tags(donor, data["tags"])
    donor.save()
    return JsonResponse({"donor": _donor_payload(donor)})


@_admin_required
@require_http_methods(["DELETE"])
def donor_delete(request, pk):
    """Soft-delete: keep the row for donation history through FK PROTECT."""
    try:
        donor = Donor.objects.get(pk=pk)
    except Donor.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)
    donor.is_active = False
    donor.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"ok": True, "removed": donor.pk})


def _campaign_payload(camp):
    raised = camp.raised_amount
    goal = Decimal(camp.goal_amount or 0)
    return {
        "id": camp.pk,
        "name": camp.name,
        "slug": camp.slug,
        "status": camp.status,
        "goal": str(goal),
        "raised": str(raised),
        "remaining": str(max(goal - raised, 0)),
        "goal_reached": bool(goal > 0 and raised >= goal),
        "progress_percent": camp.progress_percent,
        "start_date": camp.start_date.isoformat() if camp.start_date else None,
        "end_date": camp.end_date.isoformat() if camp.end_date else None,
        "description": camp.description,
    }


def _unique_slug(base, exclude_pk=None):
    import uuid

    slug = slugify(base) or "campaign"
    candidate = slug
    while Campaign.objects.filter(slug=candidate).exclude(pk=exclude_pk).exists():
        candidate = f"{slug}-{uuid.uuid4().hex[:4]}"
    return candidate


@api_login_required
@require_http_methods(["POST"])
def campaign_create(request):
    from django.utils.dateparse import parse_date

    data = _json_body(request)
    if not data or not (data.get("name") or "").strip():
        return JsonResponse({"error": "name is required."}, status=400)

    try:
        camp = Campaign(
            name=(data["name"] or "").strip(),
            slug=_unique_slug(data.get("slug") or data["name"]),
            description=(data.get("description") or ""),
            status=data.get("status", Campaign.Status.DRAFT),
        )
        if "goal" in data and data["goal"] not in (None, ""):
            try:
                # Coerce to Decimal now so progress_percent divides a number,
                # not the original string the frontend sent.
                camp.goal_amount = Decimal(str(data["goal"]))
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({"error": "Goal amount must be a valid number."}, status=400)
        if data.get("start_date"):
            camp.start_date = parse_date(str(data["start_date"]))
        if data.get("end_date"):
            camp.end_date = parse_date(str(data["end_date"]))
        camp.save()
        payload = _campaign_payload(camp)
    except ValidationError as exc:
        # Bad field value (e.g. a goal string that isn't a number like "25,000")
        # surfaces here at save() time, not as a 500.
        msg = exc.messages[0] if exc.messages else "Invalid value for a field."
        return JsonResponse({"error": msg}, status=400)
    except (IntegrityError, DataError):
        logger.warning("campaign_create DB write error for name=%r", data.get("name"))
        return JsonResponse({"error": "A campaign with this name/slug or a bad value was rejected."}, status=409)
    except OperationalError:
        logger.exception("campaign_create DB connection error")
        return JsonResponse({"error": "Database unavailable. Please try again shortly."}, status=503)
    return JsonResponse({"campaign": payload}, status=201)


@api_login_required
@require_http_methods(["PATCH"])
def campaign_update(request, pk):
    from django.utils.dateparse import parse_date

    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        camp = Campaign.objects.get(pk=pk)
    except Campaign.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    if "name" in data and isinstance(data["name"], str) and data["name"].strip():
        camp.name = data["name"].strip()
    if "description" in data:
        camp.description = data["description"] or ""
    if "status" in data and data["status"] in {c[0] for c in Campaign.Status.choices}:
        camp.status = data["status"]
    if "goal" in data:
        if data["goal"] in (None, ""):
            camp.goal_amount = 0
        else:
            try:
                camp.goal_amount = Decimal(str(data["goal"]))
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse({"error": "Goal amount must be a valid number."}, status=400)
    for key in ("start_date", "end_date"):
        if key in data:
            val = data[key]
            setattr(camp, key, parse_date(str(val)) if val else None)
    try:
        camp.save()
        payload = _campaign_payload(camp)
    except ValidationError as exc:
        msg = exc.messages[0] if exc.messages else "Invalid value for a field."
        return JsonResponse({"error": msg}, status=400)
    except (IntegrityError, DataError):
        logger.warning("campaign_update DB write error for pk=%s", pk)
        return JsonResponse({"error": "A campaign with this name/slug or a bad value was rejected."}, status=409)
    except OperationalError:
        logger.exception("campaign_update DB connection error")
        return JsonResponse({"error": "Database unavailable. Please try again shortly."}, status=503)
    return JsonResponse({"campaign": payload})


@api_login_required
@require_http_methods(["DELETE"])
def campaign_delete(request, pk):
    try:
        camp = Campaign.objects.get(pk=pk)
    except Campaign.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)
    try:
        camp.delete()
    except OperationalError:
        logger.exception("campaign_delete DB connection error")
        return JsonResponse({"error": "Database unavailable. Please try again shortly."}, status=503)
    return JsonResponse({"ok": True, "removed": pk})


@login_required
@require_http_methods(["POST"])
def volunteer_create(request):
    data = _json_body(request)
    if not data or not (data.get("name") or "").strip():
        return JsonResponse({"error": "name is required."}, status=400)

    vol = Volunteer.objects.create(
        name=(data["name"] or "").strip(),
        email=(data.get("email") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        skills=(data.get("skills") or ""),
        background_check_status=data.get("background_check_status", Volunteer.BackgroundCheck.NOT_REQUIRED),
        notes=(data.get("notes") or ""),
    )
    return JsonResponse({"volunteer": _volunteer_payload(vol)}, status=201)


def _volunteer_payload(vol):
    return {
        "id": vol.pk,
        "name": vol.name,
        "email": vol.email,
        "phone": vol.phone,
        "skills": vol.skills,
        "background_check_status": vol.background_check_status,
        "total_hours": str(vol.total_hours),
        "joined_at": vol.joined_at.isoformat() if vol.joined_at else None,
    }


@_admin_required
@require_http_methods(["PATCH"])
def volunteer_update(request, pk):
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        vol = Volunteer.objects.get(pk=pk)
    except Volunteer.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    for field in ("name", "email", "phone"):
        if field in data and isinstance(data[field], str):
            setattr(vol, field, data[field].strip())
    if "skills" in data:
        vol.skills = data["skills"] or ""
    if "notes" in data:
        vol.notes = data["notes"] or ""
    if "background_check_status" in data and data["background_check_status"] in {c[0] for c in Volunteer.BackgroundCheck.choices}:
        vol.background_check_status = data["background_check_status"]
    vol.save()
    return JsonResponse({"volunteer": _volunteer_payload(vol)})


@_admin_required
@require_http_methods(["DELETE"])
def volunteer_delete(request, pk):
    """Soft-delete: keep the row (signups reference volunteers)."""
    try:
        vol = Volunteer.objects.get(pk=pk)
    except Volunteer.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)
    vol.is_active = False
    vol.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"ok": True, "removed": pk})


@login_required
@require_http_methods(["POST"])
def event_create(request):
    from datetime import timedelta

    from django.utils import timezone
    from django.utils.dateparse import parse_datetime

    data = _json_body(request)
    if not data or not (data.get("name") or "").strip():
        return JsonResponse({"error": "name is required."}, status=400)

    try:
        capacity = int(data.get("capacity") or 0)
    except (TypeError, ValueError):
        capacity = 0
    try:
        ticket_price = float(data.get("ticket_price") or 0)
    except (TypeError, ValueError):
        ticket_price = 0

    ev = Event(
        name=(data["name"] or "").strip(),
        description=(data.get("description") or ""),
        location=(data.get("location") or ""),
        capacity=capacity,
        ticket_price=ticket_price,
        status=data.get("status", Event.Status.DRAFT),
    )
    ev.start_at = parse_datetime(str(data["start_at"])) if data.get("start_at") else timezone.now()
    ev.end_at = parse_datetime(str(data["end_at"])) if data.get("end_at") else ev.start_at + timedelta(hours=2)
    if data.get("campaign_id"):
        ev.campaign = Campaign.objects.filter(pk=data["campaign_id"]).first()
    ev.save()
    return JsonResponse({"event": _event_payload(ev)}, status=201)


def _event_payload(ev):
    return {
        "id": ev.pk,
        "name": ev.name,
        "description": ev.description,
        "location": ev.location,
        "capacity": ev.capacity,
        "ticket_price": str(ev.ticket_price),
        "campaign": ev.campaign.name if ev.campaign else None,
        "campaign_id": ev.campaign_id,
        "status": ev.status,
        "start_at": ev.start_at.isoformat() if ev.start_at else None,
        "end_at": ev.end_at.isoformat() if ev.end_at else None,
        "registrations": ev.registrations_count,
        "revenue": str(ev.revenue),
    }


@login_required
@require_http_methods(["PATCH"])
def event_update(request, pk):
    from django.utils.dateparse import parse_datetime

    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        ev = Event.objects.get(pk=pk)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    for field in ("name", "description", "location"):
        if field in data and isinstance(data[field], str):
            setattr(ev, field, data[field])
    if "capacity" in data:
        ev.capacity = int(data["capacity"] or 0)
    if "ticket_price" in data:
        ev.ticket_price = data["ticket_price"] or 0
    if "status" in data and data["status"] in {c[0] for c in Event.Status.choices}:
        ev.status = data["status"]
    for key in ("start_at", "end_at"):
        if key in data and data[key]:
            setattr(ev, key, parse_datetime(str(data[key])))
    if "campaign_id" in data:
        ev.campaign = Campaign.objects.filter(pk=data["campaign_id"]).first()
    ev.save()
    return JsonResponse({"event": _event_payload(ev)})


@login_required
@require_http_methods(["DELETE"])
def event_delete(request, pk):
    try:
        ev = Event.objects.get(pk=pk)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)
    ev.delete()
    return JsonResponse({"ok": True, "removed": pk})


@login_required
@require_http_methods(["POST"])
def donation_create(request):
    """POST /api/donations/create/ — record a donation (e.g. cash/offline)."""
    from django.utils import timezone

    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    donor = Donor.objects.filter(pk=data.get("donor_id")).first()
    if donor is None:
        return JsonResponse({"error": "donor_id is required."}, status=400)

    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return JsonResponse({"error": "amount must be > 0."}, status=400)

    campaign = Campaign.objects.filter(pk=data.get("campaign_id")).first()
    if campaign is not None:
        goal_error = _campaign_goal_guard(campaign, amount)
        if goal_error:
            return JsonResponse({"error": goal_error}, status=400)

    d = Donation.objects.create(
        donor=donor,
        campaign=campaign,
        amount=amount,
        currency=data.get("currency", settings.DONATION_CURRENCY),
        status=data.get("status", Donation.Status.CAPTURED),
        frequency=data.get("frequency", Donation.Frequency.ONE_TIME),
        date=timezone.now(),
        notes=(data.get("notes") or ""),
    )
    return JsonResponse({"donation": _json_donation(d)}, status=201)


def _registration_payload(reg):
    ev = reg.event
    return {
        "id": reg.pk,
        "event_id": ev.pk,
        "event_name": ev.name,
        "event_start": ev.start_at.isoformat() if ev.start_at else None,
        "ticket_price": str(ev.ticket_price),
        "status": reg.status,
        "paid_amount": str(reg.paid_amount),
        "attendee_name": reg.attendee_name,
        "created_at": reg.created_at.isoformat() if reg.created_at else None,
    }


@login_required
@require_http_methods(["POST"])
def event_register(request, pk):
    """Volunteer self-service: register the caller for an event.

    Free events auto-confirm; paid events start PENDING (payment is collected
    offline/at the desk); a full event (capacity reached) goes on the waitlist.
    """
    if user_role(request.user) != UserProfile.Role.VOLUNTEER:
        return JsonResponse(
            {"error": "A volunteer account is required to register for events."}, status=403
        )
    vol = getattr(request.user, "volunteer_profile", None)
    if vol is None:
        return JsonResponse(
            {"error": "No volunteer profile is linked to this account."}, status=403
        )
    try:
        ev = Event.objects.get(pk=pk)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    active = ev.registrations.exclude(status=EventRegistration.Status.CANCELLED)
    if active.filter(volunteer=vol).exists():
        return JsonResponse({"error": "You are already registered for this event."}, status=409)

    if ev.capacity > 0 and active.count() >= ev.capacity:
        status = EventRegistration.Status.WAITLISTED
    elif ev.ticket_price <= 0:
        status = EventRegistration.Status.CONFIRMED  # free event auto-confirms
    else:
        status = EventRegistration.Status.PENDING  # payment collected at the desk

    reg = EventRegistration.objects.create(
        event=ev,
        volunteer=vol,
        attendee_name=vol.name,
        attendee_email=vol.email,
        status=status,
        paid_amount=0,
    )
    return JsonResponse({"registration": _registration_payload(reg)}, status=201)


@login_required
@require_http_methods(["POST"])
def event_cancel(request, pk):
    """Volunteer self-service: cancel their own registration for an event."""
    if user_role(request.user) != UserProfile.Role.VOLUNTEER:
        return JsonResponse({"error": "A volunteer account is required."}, status=403)
    vol = getattr(request.user, "volunteer_profile", None)
    if vol is None:
        return JsonResponse(
            {"error": "No volunteer profile is linked to this account."}, status=403
        )
    try:
        ev = Event.objects.get(pk=pk)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    reg = (
        ev.registrations.filter(volunteer=vol)
        .exclude(status=EventRegistration.Status.CANCELLED)
        .first()
    )
    if reg is None:
        return JsonResponse({"error": "No active registration to cancel."}, status=404)
    reg.status = EventRegistration.Status.CANCELLED
    reg.save(update_fields=["status", "updated_at"])
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Staff approval workflows
# ---------------------------------------------------------------------------
@_staff_required
@require_GET
def event_registrations_pending(request):
    """GET /api/events/registrations/pending/ — signups waiting for staff.

    Free events still auto-confirm instantly; this queue collects the paid
    ones (status ``pending``) and anyone on the waitlist, so staff can accept
    them for the upcoming event.
    """
    regs = (
        EventRegistration.objects.filter(
            status__in=[
                EventRegistration.Status.PENDING,
                EventRegistration.Status.WAITLISTED,
            ]
        )
        .select_related("event", "volunteer")
        .order_by("event__start_at", "created_at")
    )
    items = [
        {
            "id": reg.pk,
            "event_id": reg.event_id,
            "event_name": reg.event.name,
            "event_start": reg.event.start_at.isoformat() if reg.event.start_at else None,
            "volunteer": reg.volunteer.name if reg.volunteer else (reg.attendee_name or "—"),
            "volunteer_email": reg.volunteer.email if reg.volunteer else reg.attendee_email,
            "status": reg.status,
            "ticket_price": str(reg.event.ticket_price or 0),
        }
        for reg in regs
    ]
    return JsonResponse({"count": len(items), "results": items})


@_staff_required
@require_http_methods(["POST"])
def event_registration_confirm(request, pk):
    """POST /api/event-registrations/<id>/confirm/ — staff accepts a signup."""
    try:
        reg = EventRegistration.objects.select_related("event").get(pk=pk)
    except EventRegistration.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    if reg.status == EventRegistration.Status.CANCELLED:
        return JsonResponse({"error": "This registration was cancelled."}, status=400)

    reg.status = EventRegistration.Status.CONFIRMED
    reg.save(update_fields=["status", "updated_at"])
    return JsonResponse({"registration": _registration_payload(reg)})


@_staff_required
@require_http_methods(["POST"])
def volunteer_background_verify(request, pk):
    """POST /api/volunteers/<id>/background-verify/ — staff approves or rejects.

    The background verification workflow: a self-registered volunteer starts at
    ``pending``; any staff member can mark the check ``cleared`` (approved) or
    ``rejected``. Deliberately separate from the admin-only general volunteer
    edit, so running the check does not require superuser rights.
    """
    data = _json_body(request) or {}
    approved = data.get("approved")
    if not isinstance(approved, bool):
        return JsonResponse({"error": "approved must be true or false."}, status=400)

    try:
        vol = Volunteer.objects.get(pk=pk)
    except Volunteer.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    vol.background_check_status = (
        Volunteer.BackgroundCheck.CLEARED
        if approved
        else Volunteer.BackgroundCheck.REJECTED
    )
    vol.save(update_fields=["background_check_status", "updated_at"])
    return JsonResponse({"volunteer": _volunteer_payload(vol)})


@login_required
@require_http_methods(["POST"])
def campaign_donate(request, pk):
    """Donor self-service: record a one-time (offline/cash) donation."""
    if user_role(request.user) != UserProfile.Role.DONOR:
        return JsonResponse({"error": "A donor account is required to donate."}, status=403)
    donor = getattr(request.user, "donor_profile", None)
    if donor is None:
        return JsonResponse({"error": "No donor profile is linked to this account."}, status=403)
    try:
        camp = Campaign.objects.get(pk=pk)
    except Campaign.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    data = _json_body(request)
    try:
        amount = float((data or {}).get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return JsonResponse({"error": "amount must be > 0."}, status=400)

    goal_error = _campaign_goal_guard(camp, amount)
    if goal_error:
        return JsonResponse({"error": goal_error}, status=400)

    from django.utils import timezone

    d = Donation.objects.create(
        donor=donor,
        campaign=camp,
        amount=amount,
        currency=settings.DONATION_CURRENCY,
        status=Donation.Status.CAPTURED,
        date=timezone.now(),
    )
    return JsonResponse({"donation": _json_donation(d)}, status=201)


@login_required
@require_http_methods(["POST"])
def campaign_checkout(request, pk):
    """Start a donation.

    If Razorpay is configured (test keys in .env), creates an order and returns
    everything the frontend needs to open the Razorpay Checkout modal with
    ``"mode": "online"``. Otherwise records the gift as an offline/cash donation
    immediately and returns ``{"mode": "offline", "donation_id"}`` — a plain 200,
    so the expected fallback never shows a red console error.
    """
    if user_role(request.user) != UserProfile.Role.DONOR:
        return JsonResponse({"error": "A donor account is required to donate."}, status=403)
    donor = getattr(request.user, "donor_profile", None)
    if donor is None:
        return JsonResponse({"error": "No donor profile is linked to this account."}, status=403)
    try:
        camp = Campaign.objects.get(pk=pk)
    except Campaign.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    data = _json_body(request)
    try:
        amount = float((data or {}).get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return JsonResponse({"error": "amount must be > 0."}, status=400)
    if amount < 1:
        # Razorpay's minimum order is ₹1 (100 paise) — reject anything below so
        # the gateway never even sees an invalid amount.
        return JsonResponse(
            {"error": "Minimum donation amount is ₹1 (100 paise)."}, status=400
        )

    goal_error = _campaign_goal_guard(camp, amount)
    if goal_error:
        return JsonResponse({"error": goal_error}, status=400)

    if not is_razorpay_configured():
        # No Razorpay test keys yet — record the gift straight away as an
        # offline/cash donation. Return 200 (not 503): every non-2xx paints a
        # red error in the browser console, and this is an expected path that
        # should stay quiet during the demo.
        d = Donation.objects.create(
            donor=donor,
            campaign=camp,
            amount=amount,
            currency=settings.DONATION_CURRENCY,
            status=Donation.Status.CAPTURED,
            date=timezone.now(),
        )
        return JsonResponse({"mode": "offline", "donation_id": d.pk})

    d = Donation.objects.create(
        donor=donor,
        campaign=camp,
        amount=amount,
        currency=settings.DONATION_CURRENCY,
        status=Donation.Status.INITIATED,
    )
    try:
        order = create_razorpay_order(d)
    except Exception:
        # A gateway error (network, bad key, amount rejected) should never leave
        # the donor staring at a spinner. Drop the initiated row and return a
        # clean 500 instead of the raw Razorpay exception.
        logger.exception("Razorpay order creation failed (campaign #%s)", camp.pk)
        d.delete()
        return JsonResponse(
            {"error": "Could not start the payment. Please try again in a moment."},
            status=500,
        )
    return JsonResponse(
        {
            "mode": "online",
            "donation_id": d.pk,
            "order_id": order["id"],
            "key_id": settings.RAZORPAY_KEY_ID,
            "amount_paise": int(round(amount * 100)),
            "currency": d.currency,
            "name": "NGO Platform",
            "description": f"Donation to {camp.name}" if camp else "Donation",
            "prefill": {
                "name": donor.name,
                "email": donor.email,
                "contact": donor.phone,
            },
        }
    )


@login_required
@require_http_methods(["POST"])
def donation_verify(request):
    """Verify a Razorpay Checkout callback and capture the donation.

    The frontend opens the Razorpay modal and posts the returned
    order/payment/signature here. We re-check the signature server-side (the
    client alone is never trusted) and only then mark the donation captured.
    """
    donor = getattr(request.user, "donor_profile", None)
    if donor is None:
        return JsonResponse({"error": "A donor account is required."}, status=403)

    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        donation_id = int(data.get("donation_id"))
    except (TypeError, ValueError):
        donation_id = None
    order_id = (data.get("razorpay_order_id") or "").strip()
    payment_id = (data.get("razorpay_payment_id") or "").strip()
    signature = (data.get("razorpay_signature") or "").strip()
    if not all([donation_id, order_id, payment_id, signature]):
        return JsonResponse(
            {
                "error": (
                    "donation_id, razorpay_order_id, razorpay_payment_id and "
                    "razorpay_signature are required."
                )
            },
            status=400,
        )

    d = Donation.objects.filter(pk=donation_id, donor=donor).first()
    if d is None:
        return JsonResponse({"error": "Not found."}, status=404)

    if d.razorpay_order_id and d.razorpay_order_id != order_id:
        return JsonResponse({"error": "Order mismatch."}, status=400)

    try:
        valid = verify_payment_signature(order_id=order_id, payment_id=payment_id, signature=signature)
    except ValueError as exc:
        return JsonResponse({"error": f"Payment verification unavailable: {exc}"}, status=503)
    if not valid:
        return JsonResponse({"error": "Payment signature verification failed."}, status=400)

    d.razorpay_order_id = order_id
    d.razorpay_payment_id = payment_id
    d.razorpay_signature = signature
    d.status = Donation.Status.CAPTURED
    d.date = timezone.now()
    d.save(update_fields=["razorpay_order_id", "razorpay_payment_id", "razorpay_signature", "status", "date", "updated_at"])
    return JsonResponse({"donation": _json_donation(d)})