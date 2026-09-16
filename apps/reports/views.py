"""Dashboard + CSV export endpoints (FR-5.1, FR-5.2)."""
import csv
from datetime import date
from io import StringIO

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from . import services


@require_GET
def dashboard(request):
    """GET /api/dashboard/ — lightweight JSON metrics for the live dashboard."""
    return JsonResponse(
        {
            "as_of": date.today().isoformat(),
            "donations": services.donation_totals(),
            "trend": services.donation_trend(months=6),
            "recent_donations": services.recent_donations(limit=8),
            "campaigns": services.campaign_performance(),
            "volunteers": services.volunteer_hours_summary(),
        }
    )


@require_GET
def monthly_donation_export(request):
    """GET /api/reports/monthly-donations.csv?year=YYYY&month=MM (FR-5.2)

    Downloads a CSV of donations in the given month. Fine at NGO scale
    (hundreds of rows); swap to streaming when records exceed ~10k.
    """
    year = int(request.GET.get("year", date.today().year))
    month = int(request.GET.get("month", date.today().month))
    rows = services.monthly_donation_rows(year, month)

    buf = StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["donor", "email", "campaign", "amount", "currency", "status", "date", "receipt"],
    )
    writer.writeheader()
    writer.writerows(rows)

    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="monthly-donations-{year}-{month:02d}.csv"'
    return response