"""JSON auth + user management.

Auth uses Django's session framework (the same sessions as the /admin site), so
one login works across the React app and the Django admin. CSRF: the login and
``me`` views emit the ``csrftoken`` cookie (``ensure_csrf_cookie``); the
frontend echoes it back in the ``X-CSRFToken`` header on every write request.

Permissions:
- Reading all data: anonymous (open for now — see roadmap).
- Writing resources (donors, campaigns, ...): ``is_staff``.
- User management: ``is_superuser``.
"""
import json

from django.contrib import auth as django_auth
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.models import Campaign, Donation, Donor, Event, EventRegistration, UserProfile, Volunteer
from core.views import _campaign_payload, _json_donation, _registration_payload, user_role

User = get_user_model()


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _user_payload(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "role": user_role(user),
    }


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@ensure_csrf_cookie
@csrf_exempt
@require_POST
def auth_login(request):
    """POST /api/auth/login/  JSON: {"username", "password"}"""
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "Username and password are required."}, status=400)

    user = django_auth.authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return JsonResponse({"error": "Invalid credentials."}, status=401)

    login(request, user)
    return JsonResponse({"user": _user_payload(user)})


@login_required
@require_POST
def auth_logout(request):
    """POST /api/auth/logout/"""
    logout(request)
    response = JsonResponse({"ok": True})
    response.delete_cookie("csrftoken")
    return response


@ensure_csrf_cookie
@require_GET
def auth_me(request):
    """GET /api/auth/me/ — current user + establishes the CSRF cookie."""
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})
    return JsonResponse({"authenticated": False, "user": None})


@ensure_csrf_cookie
@require_GET
def auth_csrf(request):
    """GET /api/auth/csrf/ — explicit CSRF token for any custom tooling."""
    return JsonResponse({"csrfToken": get_token(request)})


@ensure_csrf_cookie
@csrf_exempt
@require_POST
def auth_register(request):
    """POST /api/auth/register/  JSON: {"username", "password", "email", "role"}.

    Public self-service signup. Creates the account plus a linked Volunteer (role
    == "volunteer") or Donor (role == "donor") record, then logs the user in so
    the very next page load is authenticated. Staff/superusers are not creatable
    here — those are provisioned by an admin.
    """
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    username = (data.get("username") or "").strip()
    if not username or not (data.get("password") or ""):
        return JsonResponse({"error": "username and password are required."}, status=400)

    role = (data.get("role") or "").strip().lower()
    if role not in UserProfile.Role.values:
        return JsonResponse({"error": "role must be 'volunteer' or 'donor'."}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "username already exists."}, status=409)

    email = (data.get("email") or "").strip()
    user = User(
        username=username,
        email=email,
        first_name=(data.get("first_name") or "").strip(),
        last_name=(data.get("last_name") or "").strip(),
    )
    user.set_password(data["password"])
    user.save()

    UserProfile.objects.create(user=user, role=role)
    if role == UserProfile.Role.VOLUNTEER:
        # A self-registered volunteer is new to the org: the background check is
        # submitted but not yet reviewed, so it starts as "pending".
        Volunteer.objects.create(
            name=user.get_full_name() or username,
            email=email,
            user=user,
            background_check_status=Volunteer.BackgroundCheck.PENDING,
        )
    else:
        donor_type = (data.get("donor_type") or Donor.DonorType.INDIVIDUAL).strip().lower()
        if donor_type not in Donor.DonorType.values:
            donor_type = Donor.DonorType.INDIVIDUAL
        Donor.objects.create(
            name=user.get_full_name() or username,
            email=email,
            donor_type=donor_type,
            user=user,
        )

    login(request, user)
    return JsonResponse({"user": _user_payload(user)}, status=201)


@login_required
@require_GET
def me_registrations(request):
    """GET /api/me/registrations/ — the caller's own event registrations."""
    vol = getattr(request.user, "volunteer_profile", None)
    if vol is None:
        return JsonResponse({"count": 0, "results": []})
    regs = (
        EventRegistration.objects.filter(volunteer=vol)
        .select_related("event")
        .order_by("-created_at")
    )
    items = [_registration_payload(r) for r in regs]
    return JsonResponse({"count": len(items), "results": items})


def _volunteer_payload(vol):
    if vol is None:
        return None
    return {
        "name": vol.name,
        "email": vol.email,
        "phone": vol.phone,
        "skills": vol.skills,
        "background_check_status": vol.background_check_status,
        "total_hours": str(vol.total_hours or 0),
    }


def _donor_payload(donor):
    if donor is None:
        return None
    return {
        "name": donor.name,
        "email": donor.email,
        "phone": donor.phone,
        "donor_type": donor.donor_type,
        "company": donor.company,
        "source": donor.source,
        "total_given": str(donor.total_given or "0"),
    }


@login_required
@require_GET
def me_summary(request):
    """GET /api/me/summary/ — role-scoped dashboard data.

    Volunteers get their profile, registration history and upcoming published
    events to sign up for; donors get their profile, recent donations and the
    active campaigns they can support. Staff/superusers have no role and use
    the analytics ``/api/dashboard/`` instead, so this returns just ``{role}``.
    """
    role = user_role(request.user)
    from datetime import timedelta

    if role == UserProfile.Role.VOLUNTEER:
        vol = getattr(request.user, "volunteer_profile", None)
        regs = (
            EventRegistration.objects.filter(volunteer=vol)
            .select_related("event")
            .order_by("-created_at")
            if vol is not None
            else EventRegistration.objects.none()
        )
        registered_ids = set(regs.exclude(status=EventRegistration.Status.CANCELLED).values_list("event_id", flat=True))
        upcoming = Event.objects.filter(
            status=Event.Status.PUBLISHED,
            start_at__gte=timezone.now() - timedelta(hours=6),
        ).order_by("start_at")[:8]
        return JsonResponse(
            {
                "role": UserProfile.Role.VOLUNTEER,
                "profile": _volunteer_payload(vol),
                "registrations": [_registration_payload(r) for r in regs],
                "stats": {
                    "active_registrations": regs.exclude(status=EventRegistration.Status.CANCELLED).count(),
                    "total_hours": str(vol.total_hours or 0) if vol else "0",
                    "upcoming_events": len(upcoming),
                },
                "upcoming_events": [
                    {
                        "id": ev.pk,
                        "name": ev.name,
                        "start_at": ev.start_at.isoformat() if ev.start_at else None,
                        "location": ev.location,
                        "ticket_price": str(ev.ticket_price),
                        "registered": ev.pk in registered_ids,
                    }
                    for ev in upcoming
                ],
            }
        )

    if role == UserProfile.Role.DONOR:
        donor = getattr(request.user, "donor_profile", None)
        donations = (
            Donation.objects.filter(donor=donor)
            .select_related("campaign")
            .order_by("-date")[:10]
            if donor is not None
            else Donation.objects.none()
        )
        donation_rows = list(donations)
        campaigns = Campaign.objects.filter(status=Campaign.Status.ACTIVE).order_by("-created_at")[:8]
        return JsonResponse(
            {
                "role": UserProfile.Role.DONOR,
                "profile": _donor_payload(donor),
                "donations": [_json_donation(d) for d in donation_rows],
                "stats": {
                    "total_given": str(donor.total_given or "0") if donor else "0",
                    "donations_count": len(donation_rows) if donor else 0,
                    "active_campaigns": campaigns.count(),
                },
                "campaigns": [_campaign_payload(c) for c in campaigns],
            }
        )

    # Staff / superuser: hand them their normal dashboard data shape.
    return JsonResponse({"role": None, "needs_profile": False})


@login_required
@require_GET
def me_donations(request):
    """GET /api/me/donations/ — the caller's own donation transactions (all of
    them, no dashboard cap). Donor-only; other roles have no donations."""
    role = user_role(request.user)
    if role != UserProfile.Role.DONOR:
        return JsonResponse({"error": "Only donor accounts have donations."}, status=403)
    donor = getattr(request.user, "donor_profile", None)
    if donor is None:
        return JsonResponse({"error": "No donor profile is linked to this account."}, status=404)
    donations = (
        Donation.objects.filter(donor=donor)
        .select_related("campaign")
        .order_by("-date", "-pk")
    )
    donation_rows = list(donations)
    return JsonResponse({
        "donor": _donor_payload(donor),
        "count": len(donation_rows),
        "total_given": str(donor.total_given or "0"),
        "results": [_json_donation(d) for d in donation_rows],
    })


@login_required
@require_GET
def me_campaigns(request):
    """GET /api/me/campaigns/ — every active campaign a donor can support."""
    campaigns = Campaign.objects.filter(status=Campaign.Status.ACTIVE).order_by("-created_at")
    campaign_rows = list(campaigns)
    return JsonResponse({
        "count": len(campaign_rows),
        "results": [_campaign_payload(c) for c in campaign_rows],
    })


@login_required
@require_http_methods(["PATCH"])
def me_profile_update(request):
    """PATCH /api/me/profile/ — a donor or volunteer updates their own profile.

    The editable fields mirror what the admin sees when editing the linked
    Donor/Volunteer record, minus the tags (donor) and the background-check
    decision (volunteer), which stay admin-managed.
    """
    role = user_role(request.user)
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    if role == UserProfile.Role.VOLUNTEER:
        vol = getattr(request.user, "volunteer_profile", None)
        if vol is None:
            return JsonResponse({"error": "No volunteer profile is linked to this account."}, status=404)
        for field in ("name", "email", "phone", "skills"):
            if field in data and isinstance(data[field], str):
                setattr(vol, field, data[field].strip())
        vol.save()
        return JsonResponse({"profile": _volunteer_payload(vol)})

    if role == UserProfile.Role.DONOR:
        donor = getattr(request.user, "donor_profile", None)
        if donor is None:
            return JsonResponse({"error": "No donor profile is linked to this account."}, status=404)
        for field in ("name", "email", "phone", "company", "source"):
            if field in data and isinstance(data[field], str):
                setattr(donor, field, data[field].strip())
        if "donor_type" in data and data["donor_type"] in Donor.DonorType.values:
            donor.donor_type = data["donor_type"].strip().lower()
        donor.save()
        return JsonResponse({"profile": _donor_payload(donor)})

    return JsonResponse({"error": "Only donor and volunteer accounts have a profile."}, status=403)


# ---------------------------------------------------------------------------
# Users (superuser only)
# ---------------------------------------------------------------------------
def _superuser_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({"error": "Superuser permission required."}, status=403)
        return view(request, *args, **kwargs)

    return wrapper


@_superuser_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return JsonResponse({"results": [_user_payload(u) for u in users]})


@_superuser_required
def user_create(request):
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"error": "username and password are required."}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "username already exists."}, status=409)

    user = User.objects.create_user(username=username, password=password)
    user.email = (data.get("email") or "").strip()
    user.first_name = (data.get("first_name") or "").strip()
    user.last_name = (data.get("last_name") or "").strip()
    user.is_staff = bool(data.get("is_staff", False))
    user.is_superuser = bool(data.get("is_superuser", False))
    user.save()
    return JsonResponse({"user": _user_payload(user)}, status=201)


@_superuser_required
def user_update(request, pk):
    data = _json_body(request)
    if not data:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    if "username" in data and data["username"] != user.username:
        return JsonResponse({"error": "Username cannot be changed."}, status=400)

    for field in ("email", "first_name", "last_name"):
        if field in data:
            setattr(user, field, (data[field] or "").strip())
    if "is_staff" in data:
        user.is_staff = bool(data["is_staff"])
    if "is_superuser" in data:
        user.is_superuser = bool(data["is_superuser"])
    if "is_active" in data:
        if int(user.pk) == int(request.user.pk) and not data["is_active"]:
            return JsonResponse({"error": "You cannot deactivate your own account."}, status=400)
        user.is_active = bool(data["is_active"])
    if data.get("password"):
        user.set_password(data["password"])

    user.save()
    return JsonResponse({"user": _user_payload(user)})


@_superuser_required
def user_delete(request, pk):
    """Soft-delete: deactivate but keep the row (auth constraints)."""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return JsonResponse({"error": "Not found."}, status=404)

    if int(user.pk) == int(request.user.pk):
        return JsonResponse({"error": "You cannot deactivate your own account."}, status=400)

    user.is_active = False
    user.save()
    return JsonResponse({"ok": True, "is_active": False})