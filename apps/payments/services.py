"""Razorpay helper functions — thin wrappers around the official SDK.

These are synchronous (no Celery) at MVP stage. When a queue is available,
the receipt-generation step should be pushed to a background task.
"""
import hashlib
import hmac
import logging
import math

import razorpay
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("payments")


def is_razorpay_configured() -> bool:
    """True when API keys are set (test or live), enabling online payments."""
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def verify_payment_signature(*, order_id: str, payment_id: str, signature: str) -> bool:
    """Return True if a Razorpay checkout callback signature is genuine.

    Matches the algorithm Razorpay uses for the client-side handler — the
    signature is an HMAC-SHA256 over ``"{razorpay_order_id}|{razorpay_payment_id}"``
    keyed with the API secret, hex-encoded. Verifying here (server-side) means a
    tampered client can't mark a donation as paid.
    """
    secret = settings.RAZORPAY_KEY_SECRET
    if not secret:
        raise ValueError("RAZORPAY_KEY_SECRET is not configured.")
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return _client


def create_razorpay_order(donation, *, receipt: str = "") -> dict:
    """Create a Razorpay Order for a donation and update the donation record.

    Returns the Razorpay API response dict.
    """
    amount_paise = int(round(donation.amount * 100))
    payload = {
        "amount": amount_paise,
        "currency": donation.currency,
        "receipt": receipt or donation.receipt_number,
        "payment_capture": 1,  # auto-capture
        "notes": {"donation_id": str(donation.pk), "campaign": donation.campaign.name if donation.campaign else ""},
    }
    order = _get_client().order.create(payload)
    donation.razorpay_order_id = order["id"]
    donation.status = "order_created"
    donation.save(update_fields=["razorpay_order_id", "status", "updated_at"])
    logger.info("Created Razorpay order %s for donation #%s", order["id"], donation.pk)
    return order


def create_payment_link(*, amount: float, currency: str = "INR", donor=None, donation=None,
                       expire_in_seconds: int = 259200) -> dict:
    """Create a Razorpay Payment Link (for sharing with donors).

    Returns the raw Razorpay response; the caller saves a PaymentLink record.
    """
    amount_paise = int(round(amount * 100))
    payload = {
        "amount": amount_paise,
        "currency": currency,
        "accept_partial": False,
        "reference_id": donation.receipt_number if donation else "",
        "description": f"Donation to NGO" + (f" — {donation.campaign.name}" if donation and donation.campaign else ""),
        "callback_method": "redirect",
        "callback_url": "",  # can be filled in with a post-donation thank-you URL
        "expire_by": int(timezone.now().timestamp()) + expire_in_seconds,
        "notes": {
            "donor_id": str(donor.pk) if donor else "",
            "donation_id": str(donation.pk) if donation else "",
        },
    }
    link = _get_client().payment_link.create(payload)
    logger.info("Created payment link %s (short_url=%s)", link.get("id"), link.get("short_url"))
    return link


def process_webhook_event(event) -> None:
    """Dispatch a RazorpayWebhookEvent by event_type to the appropriate handler."""
    from core.models import Donation
    from django.utils.dateparse import parse_datetime

    payload = event.payload
    event_data = payload.get("payload", {})
    order_data = event_data.get("order", {}).get("entity", {})
    payment_data = event_data.get("payment", {}).get("entity", {})
    # The refund entity is nested under payload.refund.entity, not payment.
    refund_data = event_data.get("refund", {}).get("entity", {})

    event_type = event.event_type
    logger.info("Processing event %s for %s", event_type, event.event_id)

    try:
        if event_type == "order.paid":
            _handle_order_paid(order_data, payment_data)
        elif event_type == "payment.authorized":
            _handle_payment_authorized(payment_data)
        elif event_type == "payment.captured":
            _handle_payment_captured(payment_data)
        elif event_type == "payment.failed":
            _handle_payment_failed(payment_data)
        elif event_type == "refund.created":
            _handle_refund_created(refund_data)
        elif event_type in ("order.paid", "subscription.activated"):
            pass  # covered above / placeholder for future
        else:
            logger.info("Unhandled event type %s", event_type)
    except Exception as exc:
        event.status = "failed"
        event.error_message = str(exc)[:500]
        event.save(update_fields=["status", "error_message", "updated_at"])
        raise

    event.status = "processed"
    event.processed_at = timezone.now()
    event.save(update_fields=["status", "processed_at", "updated_at"])


# ---------------------------------------------------------------------------
# Individual event handlers
# ---------------------------------------------------------------------------

def _find_donation(*, razorpay_order_id=None, razorpay_payment_id=None):
    from core.models import Donation

    if razorpay_payment_id:
        try:
            return Donation.objects.get(razorpay_payment_id=razorpay_payment_id)
        except Donation.DoesNotExist:
            pass
    if razorpay_order_id:
        try:
            return Donation.objects.get(razorpay_order_id=razorpay_order_id)
        except Donation.DoesNotExist:
            pass
    return None


def _handle_order_paid(order_data, payment_data):
    from core.models import Donation

    order_id = order_data.get("id", "")
    payment_id = payment_data.get("id", "")
    amount_paid = payment_data.get("amount")  # in paise
    currency = payment_data.get("currency", "INR")
    created_at = payment_data.get("created_at")

    donation = _find_donation(razorpay_order_id=order_id, razorpay_payment_id=payment_id)

    if donation is None:
        logger.warning("No Donation found for order %s — cannot reconcile.", order_id)
        return

    donation.razorpay_order_id = order_id
    donation.razorpay_payment_id = payment_id
    donation.razorpay_signature = payment_data.get("signature", "")
    donation.currency = currency

    if amount_paid is not None:
        donation.amount = round(amount_paid / 100, 2)

    if created_at:
        from datetime import datetime
        donation.date = datetime.fromtimestamp(created_at)

    donation.status = "captured"
    donation.save()

    _trigger_acknowledgement(donation)


def _handle_payment_authorized(payment_data):
    from core.models import Donation

    payment_id = payment_data.get("id", "")
    donation = _find_donation(razorpay_payment_id=payment_id)
    if donation and donation.status not in ("captured", "succeeded"):
        donation.status = "payment_pending"
        donation.save(update_fields=["status", "updated_at"])


def _handle_payment_captured(payment_data):
    from core.models import Donation

    payment_id = payment_data.get("id", "")
    amount = payment_data.get("amount")  # paise

    donation = _find_donation(razorpay_payment_id=payment_id)
    if donation is None:
        logger.warning("No Donation found for payment %s on capture.", payment_id)
        return

    if amount is not None:
        donation.amount = round(amount / 100, 2)

    donation.status = "captured"
    donation.save()

    _trigger_acknowledgement(donation)


def _handle_payment_failed(payment_data):
    from core.models import Donation

    payment_id = payment_data.get("id", "")
    donation = _find_donation(razorpay_payment_id=payment_id)
    if donation:
        donation.status = "failed"
        donation.save(update_fields=["status", "updated_at"])
        logger.info("Donation #%s marked failed after payment failure.", donation.pk)


def _handle_refund_created(refund_data):
    from core.models import Donation

    payment_id = refund_data.get("payment_id", "")
    refund_amount = refund_data.get("amount", 0)  # paise

    donation = _find_donation(razorpay_payment_id=payment_id)
    if donation is None:
        logger.warning("No Donation found for refund on payment %s.", payment_id)
        return

    donation.refund_amount = round(refund_amount / 100, 2)
    donation.status = "refunded" if donation.refund_amount >= donation.amount else "part_refunded"
    donation.save()


def _trigger_acknowledgement(donation):
    """Queue or send the automated acknowledgement email (FR-4.1).

    This is synchronous at MVP. Push to a background task (Celery/django-mailer)
    once available.
    """
    if donation.acknowledgement_sent_at:
        return  # idempotent — only send once

    # Placeholder: in production this renders an email template and sends via
    # the configured email backend (SMTP, SES, Sendgrid, etc.).
    logger.info(
        "ACK for donation #%s — %s %s — TODO: send email",
        donation.pk, donation.amount, donation.currency,
    )
    donation.acknowledgement_sent_at = timezone.now()
    donation.save(update_fields=["acknowledgement_sent_at", "updated_at"])