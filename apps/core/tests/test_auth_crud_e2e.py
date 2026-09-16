"""End-to-end auth + CRUD validation.

Runs the REAL URLconf, views, session auth and CSRF enforcement (test client
with enforce_csrf_checks=True, so the CSRF cookie -> X-CSRFToken dance is
required exactly like a real browser). Uses the in-memory test DB; every row is
rolled back. Mirrors exactly what the React frontend's api.js does.

Run:  .venv/Scripts/python.exe manage.py test apps.core.tests.test_auth_crud_e2e -v 2
"""
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import Campaign, Donation, Donor, Event, EventRegistration, Volunteer

User = get_user_model()


class FakeRazorpayOrderAPI:
    def create(self, payload):
        return {"id": "order_test123", "amount": payload["amount"], "currency": payload["currency"]}


class FakeRazorpayClient:
    order = FakeRazorpayOrderAPI()

API = "/api"


def _post(c, path, payload, csrf=None):
    headers = {"HTTP_X_CSRFTOKEN": csrf} if csrf else {}
    return c.post(f"{API}{path}", data=json.dumps(payload), content_type="application/json", **headers)


def _patch(c, path, payload, csrf=None):
    headers = {"HTTP_X_CSRFTOKEN": csrf} if csrf else {}
    return c.patch(f"{API}{path}", data=json.dumps(payload), content_type="application/json", **headers)


def _delete(c, path, csrf=None):
    headers = {"HTTP_X_CSRFTOKEN": csrf} if csrf else {}
    return c.delete(f"{API}{path}", **headers)


class AuthCrudE2ETest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "admin12345")
        self.staff = User.objects.create_user("staff1", password="staff12345", is_staff=True)
        # Browser-like client: CSRF token required on every write.
        self.c = Client(enforce_csrf_checks=True)

    # -- helpers ----------------------------------------------------------
    def login(self, username="admin", password="admin12345"):
        # auth_login is @csrf_exempt (like the real endpoint), so this works
        # even with enforce_csrf_checks=True and establishes the real session.
        r = _post(self.c, "/auth/login/", {"username": username, "password": password})
        # ensure a csrftoken cookie is present for subsequent writes
        self.c.get("/api/auth/me/")
        return r

    def csrf(self):
        token = self.c.cookies["csrftoken"].value if "csrftoken" in self.c.cookies else None
        self.assertIsNotNone(token, "expected csrftoken cookie to be planted")
        return token

    # -- auth ---------------------------------------------------------------
    def test_login_success_plants_session_and_csrf(self):
        r = self.login()
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertTrue(body["user"]["is_superuser"])

        me = self.c.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.json()["authenticated"])
        self.assertEqual(me.json()["user"]["username"], "admin")
        self.assertIsNotNone(self.csrf())

    def test_bad_credentials_rejected(self):
        r = _post(self.c, "/auth/login/", {"username": "admin", "password": "wrong"})
        self.assertEqual(r.status_code, 401)

    def test_anonymous_write_is_blocked(self):
        anon = Client(enforce_csrf_checks=True)
        r = _post(anon, "/donors/create/", {"name": "x"})
        self.assertEqual(r.status_code, 403)  # @login_required -> 403 for non-HTML

    def test_write_without_csrf_token_is_blocked(self):
        self.login()
        r = self.c.post(
            "/api/donors/create/",
            data=json.dumps({"name": "x"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="",
        )
        self.assertEqual(r.status_code, 403)  # CSRF check enforced

    # -- donor CRUD (soft delete) ----------------------------------------
    def test_donor_crud(self):
        self.login()
        tok = self.csrf()

        r = _post(self.c, "/donors/create/", {"name": "Smoke Donor", "email": "smoke@example.com", "tags": ["demo"]}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        did = r.json()["donor"]["id"]
        self.assertEqual(r.json()["donor"]["tags"], ["demo"])

        r = _patch(self.c, f"/donors/{did}/update/", {"name": "Smoke Donor 2"}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["donor"]["name"], "Smoke Donor 2")

        listing = self.c.get("/api/donors/").json()
        self.assertIn("Smoke Donor 2", [d["name"] for d in listing["results"]])

        r = _delete(self.c, f"/donors/{did}/delete/", tok)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        listing = self.c.get("/api/donors/").json()
        self.assertNotIn("Smoke Donor 2", [d["name"] for d in listing["results"]])
        self.assertTrue(Donor.objects.filter(pk=did).exists(), "soft-delete keeps the row for history")

    # -- campaign CRUD (hard delete) -------------------------------------
    def test_campaign_crud(self):
        self.login()
        tok = self.csrf()

        r = _post(self.c, "/campaigns/create/", {"name": "Smoke Campaign", "goal": "5000"}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        cid = r.json()["campaign"]["id"]

        r = _patch(self.c, f"/campaigns/{cid}/update/", {"status": "active"}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["campaign"]["status"], "active")

        self.assertTrue(Campaign.objects.filter(pk=cid).exists())

        r = _delete(self.c, f"/campaigns/{cid}/delete/", tok)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Campaign.objects.filter(pk=cid).exists(), "hard delete")

    # -- volunteer CRUD (soft delete) ------------------------------------
    def test_volunteer_crud(self):
        self.login()
        tok = self.csrf()

        r = _post(self.c, "/volunteers/create/", {"name": "Smoke Vol", "background_check_status": "cleared"}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        vid = r.json()["volunteer"]["id"]
        self.assertEqual(r.json()["volunteer"]["background_check_status"], "cleared")

        r = _patch(self.c, f"/volunteers/{vid}/update/", {"skills": "teaching, events"}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["volunteer"]["skills"], "teaching, events")

        r = _delete(self.c, f"/volunteers/{vid}/delete/", tok)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Volunteer.objects.filter(pk=vid).exists(), "soft-delete keeps the row")

    # -- event CRUD (hard delete) ----------------------------------------
    def test_event_crud(self):
        self.login()
        tok = self.csrf()

        r = _post(self.c, "/events/create/", {
            "name": "Smoke Event",
            "start_at": "2026-09-12T10:00",
            "end_at": "2026-09-12T12:00",
            "capacity": 100,
            "ticket_price": "250.00",
        }, tok)
        self.assertEqual(r.status_code, 201, r.content)
        eid = r.json()["event"]["id"]
        self.assertEqual(r.json()["event"]["capacity"], 100)

        r = _patch(self.c, f"/events/{eid}/update/", {"status": "published"}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["event"]["status"], "published")

        r = _delete(self.c, f"/events/{eid}/delete/", tok)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Event.objects.filter(pk=eid).exists(), "hard delete")

    def test_event_create_defaults_dates_when_missing(self):
        self.login()
        tok = self.csrf()
        r = _post(self.c, "/events/create/", {"name": "No Dates Event"}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        ev = r.json()["event"]
        self.assertIsNotNone(ev["start_at"])
        self.assertIsNotNone(ev["end_at"])

    # -- donation create --------------------------------------------------
    def test_donation_create(self):
        self.login()
        tok = self.csrf()
        donor = Donor.objects.create(name="Seed Donor")
        r = _post(self.c, "/donations/create/", {"donor_id": donor.pk, "amount": "1500.00"}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(Donation.objects.filter(pk=r.json()["donation"]["id"]).exists())

    # -- user management (superuser only) ---------------------------------
    def test_user_management(self):
        self.login()
        tok = self.csrf()

        r = _post(self.c, "/users/create/", {"username": "staff_smoke", "password": "Staf12345!", "is_staff": True}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        uid = r.json()["user"]["id"]
        self.assertTrue(r.json()["user"]["is_staff"])

        listing = self.c.get("/api/users/").json()
        self.assertIn("staff_smoke", [u["username"] for u in listing["results"]])

        r = _patch(self.c, f"/users/{uid}/", {"is_staff": False}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["user"]["is_staff"])

        r = _delete(self.c, f"/users/{uid}/delete/", tok)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_cannot_deactivate_self(self):
        self.login()
        tok = self.csrf()
        r = _patch(self.c, f"/users/{self.admin.pk}/", {"is_active": False}, tok)
        self.assertEqual(r.status_code, 400)

    # -- permissions ------------------------------------------------------
    def test_staff_can_write_but_not_manage_users(self):
        self.login("staff1", "staff12345")
        tok = self.csrf()

        r = _post(self.c, "/donors/create/", {"name": "Staff Made"}, tok)
        self.assertEqual(r.status_code, 201, r.content)

        r = self.c.get("/api/users/")
        self.assertEqual(r.status_code, 403, r.content)  # superuser required

    def test_logout_then_me(self):
        self.login()
        tok = self.csrf()
        r = _post(self.c, "/auth/logout/", {}, tok)
        self.assertEqual(r.status_code, 200)
        me = self.c.get("/api/auth/me/")
        self.assertFalse(me.json()["authenticated"])

    # -- registration & roles ---------------------------------------------
    def register(self, role, username="newvol", password="Newpass123!"):
        r = _post(
            self.c,
            "/auth/register/",
            {"username": username, "password": password, "email": f"{username}@example.com", "role": role},
        )
        # register is @csrf_exempt like login; plant the csrf cookie for later writes.
        self.c.get("/api/auth/me/")
        return r

    def _event(self):
        now = timezone.now()
        return Event.objects.create(
            name="Volunteer Fest",
            start_at=now,
            end_at=now + timedelta(hours=2),
            ticket_price=0,
        )

    def test_register_volunteer(self):
        r = self.register("volunteer", "vol_a")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["user"]["role"], "volunteer")
        self.assertFalse(r.json()["user"]["is_staff"], "self-service cannot grant staff")
        me = self.c.get("/api/auth/me/").json()
        self.assertTrue(me["authenticated"], "registration logs the user straight in")
        self.assertEqual(me["user"]["role"], "volunteer")
        self.assertTrue(Volunteer.objects.filter(user_id=r.json()["user"]["id"]).exists())

    def test_register_donor(self):
        r = self.register("donor", "don_a")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["user"]["role"], "donor")
        self.assertTrue(Donor.objects.filter(user_id=r.json()["user"]["id"]).exists())

    def test_register_validation(self):
        r = self.register("superuser")  # invalid role
        self.assertEqual(r.status_code, 400)
        self.register("donor", "dupuser")
        dup = self.register("volunteer", "dupuser")
        self.assertEqual(dup.status_code, 409)

    def test_staff_user_has_no_role(self):
        self.login("staff1", "staff12345")
        self.assertIsNone(self.c.get("/api/auth/me/").json()["user"]["role"])

    def test_volunteer_registers_and_cancels_event(self):
        self.register("volunteer", "vol_b")
        tok = self.csrf()
        ev = self._event()

        r = _post(self.c, f"/events/{ev.pk}/register/", {}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        reg = r.json()["registration"]
        self.assertEqual(reg["status"], "confirmed")  # free event auto-confirms
        self.assertEqual(reg["attendee_name"], "vol_b")
        self.assertEqual(reg["event_id"], ev.pk)

        dup = _post(self.c, f"/events/{ev.pk}/register/", {}, tok)
        self.assertEqual(dup.status_code, 409, "duplicate registration refused")

        mine = self.c.get("/api/me/registrations/").json()
        self.assertEqual(mine["count"], 1)
        self.assertEqual(mine["results"][0]["status"], "confirmed")

        r = _post(self.c, f"/events/{ev.pk}/cancel/", {}, tok)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["ok"], True)
        mine = self.c.get("/api/me/registrations/").json()
        self.assertEqual(mine["results"][0]["status"], "cancelled")
        self.assertEqual(
            EventRegistration.objects.filter(event=ev, status="cancelled").count(), 1
        )

    def test_waitlist_when_capacity_is_full(self):
        self.register("volunteer", "vol_c")
        tok = self.csrf()
        ev = Event.objects.create(
            name="Tiny Event",
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(hours=1),
            capacity=1,
            ticket_price=0,
        )
        r = _post(self.c, f"/events/{ev.pk}/register/", {}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["registration"]["status"], "confirmed", "first seat confirmed")

        # a second volunteer fills the list -> waitlisted
        self.register("volunteer", "vol_d")
        tok2 = self.csrf()
        r2 = _post(self.c, f"/events/{ev.pk}/register/", {}, tok2)
        self.assertEqual(r2.status_code, 201, r2.content)
        self.assertEqual(r2.json()["registration"]["status"], "waitlisted")

    def test_donor_donates_to_campaign(self):
        self.register("donor", "don_b")
        tok = self.csrf()
        camp = Campaign.objects.create(name="Clean Water", goal_amount=100000)

        r = _post(self.c, f"/campaigns/{camp.pk}/donate/", {"amount": "2500"}, tok)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["donation"]["amount"], "2500.00")
        camp.refresh_from_db()
        self.assertEqual(camp.raised_amount, Decimal("2500.00"))

        bad = _post(self.c, f"/campaigns/{camp.pk}/donate/", {"amount": "-5"}, tok)
        self.assertEqual(bad.status_code, 400)

    def test_role_boundaries(self):
        # a donor cannot register for events
        self.register("donor", "don_c")
        tok = self.csrf()
        ev = self._event()
        r = _post(self.c, f"/events/{ev.pk}/register/", {}, tok)
        self.assertEqual(r.status_code, 403)

        # an anonymous user cannot register or donate
        anon = Client(enforce_csrf_checks=True)
        r_anon = anon.post(f"/api/events/{ev.pk}/register/")
        self.assertEqual(r_anon.status_code, 403)
        camp = Campaign.objects.create(name="Boundary", goal_amount=1000)
        r_anon = anon.post(f"/api/campaigns/{camp.pk}/donate/")
        self.assertEqual(r_anon.status_code, 403)

    # -- role dashboards summary -------------------------------------------
    def test_volunteer_summary(self):
        self.register("volunteer", "sum_vol")
        now = timezone.now()
        ev = Event.objects.create(
            name="Summary Fest",
            start_at=now,
            end_at=now + timedelta(hours=2),
            ticket_price=0,
            status=Event.Status.PUBLISHED,
        )
        _post(self.c, f"/events/{ev.pk}/register/", {}, self.csrf())

        s = self.c.get("/api/me/summary/").json()
        self.assertEqual(s["role"], "volunteer")
        self.assertEqual(s["profile"]["name"], "sum_vol")
        self.assertEqual(s["stats"]["active_registrations"], 1)
        self.assertEqual(len(s["registrations"]), 1)
        self.assertEqual(s["registrations"][0]["event_id"], ev.pk)
        self.assertIn(ev.pk, [u["id"] for u in s["upcoming_events"]])
        self.assertTrue(any(u["registered"] for u in s["upcoming_events"]))

    def test_donor_summary(self):
        self.register("donor", "sum_don")
        camp = Campaign.objects.create(name="River Cleanup", goal_amount=50000)
        _post(self.c, f"/campaigns/{camp.pk}/donate/", {"amount": "1200"}, self.csrf())

        s = self.c.get("/api/me/summary/").json()
        self.assertEqual(s["role"], "donor")
        self.assertEqual(s["stats"]["total_given"], "1200.00")
        self.assertEqual(s["stats"]["donations_count"], 1)
        self.assertEqual(len(s["donations"]), 1)
        self.assertEqual(s["donations"][0]["amount"], "1200.00")
        self.assertIn(camp.pk, [c["id"] for c in s["campaigns"]])

    def test_staff_summary_is_role_free(self):
        self.login("staff1", "staff12345")
        s = self.c.get("/api/me/summary/").json()
        self.assertIsNone(s["role"])

    # -- donor payment flow (Razorpay) ------------------------------------
    def _donor_campaign(self):
        self.register("donor", "pay_donor")
        return Campaign.objects.create(name="Payment Test", goal_amount=100000)

    @override_settings(RAZORPAY_KEY_ID="", RAZORPAY_KEY_SECRET="")
    def test_checkout_offline_when_unconfigured(self):
        # No Razorpay keys -> the checkout endpoint itself records the gift as
        # an offline/cash donation and returns 200 (not 503), so the demo
        # console never paints the expected fallback as an error.
        camp = self._donor_campaign()
        r = _post(self.c, f"/campaigns/{camp.pk}/checkout/", {"amount": "500"}, self.csrf())
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["mode"], "offline")
        d = Donation.objects.get(pk=body["donation_id"])
        self.assertEqual(d.campaign, camp)
        self.assertEqual(d.amount, Decimal("500.00"))
        self.assertEqual(d.status, Donation.Status.CAPTURED)

    @override_settings(RAZORPAY_KEY_ID="rzp_test_abc", RAZORPAY_KEY_SECRET="secret")
    def test_checkout_creates_razorpay_order(self):
        camp = self._donor_campaign()
        with mock.patch("payments.services._client", FakeRazorpayClient()):
            r = _post(self.c, f"/campaigns/{camp.pk}/checkout/", {"amount": "500"}, self.csrf())
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["mode"], "online")
        self.assertEqual(body["order_id"], "order_test123")
        self.assertEqual(body["key_id"], "rzp_test_abc")
        self.assertEqual(body["amount_paise"], 50000)
        self.assertEqual(body["currency"], "INR")
        self.assertEqual(body["prefill"]["name"], "pay_donor")
        d = Donation.objects.get(pk=body["donation_id"])
        self.assertEqual(d.status, "order_created")
        self.assertEqual(d.razorpay_order_id, "order_test123")

    @override_settings(RAZORPAY_KEY_SECRET="secret")
    def test_donation_verify_captures(self):
        camp = self._donor_campaign()
        donor = Donor.objects.get(user__username="pay_donor")
        d = Donation.objects.create(
            donor=donor,
            campaign=camp,
            amount=Decimal("500.00"),
            currency="INR",
            status="initiated",
            razorpay_order_id="order_abc",
        )
        signature = hmac.new(b"secret", b"order_abc|pay_xyz", hashlib.sha256).hexdigest()

        r = _post(
            self.c,
            "/donations/verify/",
            {
                "donation_id": d.pk,
                "razorpay_order_id": "order_abc",
                "razorpay_payment_id": "pay_xyz",
                "razorpay_signature": signature,
            },
            self.csrf(),
        )
        self.assertEqual(r.status_code, 200, r.content)
        d.refresh_from_db()
        self.assertEqual(d.status, "captured")
        self.assertEqual(d.razorpay_payment_id, "pay_xyz")
        self.assertEqual(d.razorpay_signature, signature)
        self.assertIsNotNone(d.date, "capture records the payment time")

    @override_settings(RAZORPAY_KEY_SECRET="secret")
    def test_verify_rejects_wrong_owner_and_bad_signature(self):
        camp = self._donor_campaign()
        donor = Donor.objects.get(user__username="pay_donor")
        d = Donation.objects.create(
            donor=donor,
            campaign=camp,
            amount=Decimal("500.00"),
            currency="INR",
            status="order_created",
            razorpay_order_id="order_abc",
        )

        # The owner posts a tampered signature -> rejected.
        r_bad = _post(
            self.c,
            "/donations/verify/",
            {
                "donation_id": d.pk,
                "razorpay_order_id": "order_abc",
                "razorpay_payment_id": "pay_xyz",
                "razorpay_signature": "deadbeef",
            },
            self.csrf(),
        )
        self.assertEqual(r_bad.status_code, 400, r_bad.content)

        # A different donor cannot verify someone else's donation -> not found.
        self.register("donor", "pay_other")
        signature = hmac.new(b"secret", b"order_abc|pay_xyz", hashlib.sha256).hexdigest()
        r_other = _post(
            self.c,
            "/donations/verify/",
            {
                "donation_id": d.pk,
                "razorpay_order_id": "order_abc",
                "razorpay_payment_id": "pay_xyz",
                "razorpay_signature": signature,
            },
            self.csrf(),
        )
        self.assertEqual(r_other.status_code, 404, r_other.content)

        d.refresh_from_db()
        self.assertNotEqual(d.status, "captured")