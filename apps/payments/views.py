"""Razorpay webhook endpoint (CSRF-exempt, signature-verified).

Razorpay delivers ONE event object per webhook POST (unlike Stripe's batches).
The body shape is::

    {
      "entity": "event",
      "id": "evt_xxxx",          // globally unique
      "event": "order.paid",     // the event type
      "payload": {
        "payment": {"entity": {...}},
        "order":   {"entity": {...}}
      },
      ...
    }
"""
import json
import logging

from django.db import models as db_models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import RazorpayWebhookEvent
from .security import RazorpaySignatureError, verify_razorpay_signature
from .services import process_webhook_event

logger = logging.getLogger("payments")


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    raw_body = request.body

    # 1. Verify the signature before trusting any content.
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        verify_razorpay_signature(raw_body, signature)
    except RazorpaySignatureError as exc:
        logger.warning("Razorpay signature invalid: %s", exc)
        return JsonResponse({"error": "Invalid signature."}, status=403)
    except ValueError as exc:
        logger.error("Razorpay webhook secret not configured: %s", exc)
        return JsonResponse({"error": "Server configuration error."}, status=500)

    # 2. Parse the (signed) body.
    try:
        event_data = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    event_id = event_data.get("id", "")
    event_type = event_data.get("event", "")
    if not event_id or not event_type:
        logger.warning("Webhook body missing id/event: %r", event_data)
        return JsonResponse({"error": "Missing event id or type."}, status=400)

    order_entity = event_data.get("payload", {}).get("order", {}).get("entity", {})
    payment_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})

    # 3. Persist + process, idempotently keyed on event.id.
    event, created = RazorpayWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "event_type": event_type,
            "payload": event_data,
            "razorpay_order_id": order_entity.get("id", ""),
            "razorpay_payment_id": payment_entity.get("id", ""),
        },
    )

    if not created:
        # Already seen — bump a counter and return OK so Razorpay stops retrying.
        RazorpayWebhookEvent.objects.filter(event_id=event_id).update(
            status="duplicate",
            retry_count=db_models.F("retry_count") + 1,
        )
        return JsonResponse({"status": "ok", "duplicate": True})

    try:
        process_webhook_event(event)
        return JsonResponse({"status": "ok"})
    except Exception:
        # The event row is marked "failed" by the service; we still return 200
        # to stop Razorpay re-deliveries for the same payload. Reconcile via
        # the failed rows or a replay tool.
        logger.exception("Failed processing event %s", event_id)
        return JsonResponse({"status": "ok", "reconciled": False})