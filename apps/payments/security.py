"""Razorpay webhook signature verification.

Matches the official ``razorpay.utility.Utility.verify_webhook_signature``:

    hmac-sha256(body) keyed with the RAW webhook-secret string, then
    base64-encoded, compared to the ``X-Razorpay-Signature`` header.
"""
import base64
import hashlib
import hmac

from django.conf import settings


class RazorpaySignatureError(Exception):
    """Raised when the supplied signature does not match."""


def verify_razorpay_signature(payload_body: bytes, signature: str) -> bool:
    """Return True if the payload was signed by Razorpay; raise on failure."""
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret:
        raise ValueError("RAZORPAY_WEBHOOK_SECRET is not configured.")
    if not signature:
        raise RazorpaySignatureError("Missing X-Razorpay-Signature header.")

    expected = base64.b64encode(
        hmac.new(webhook_secret.encode("utf-8"), payload_body, hashlib.sha256).digest()
    ).decode("ascii")

    if not hmac.compare_digest(expected, signature):
        raise RazorpaySignatureError("Invalid signature.")
    return True