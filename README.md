# NGO Operations Management Platform

A full-stack platform that gives a small NGO **one place** to manage donors,
campaigns, donations, volunteers, and events — with role-based access, live
analytics, and online payments.

Built for the final-round presentation on **16 September 2026**.

- **Backend** — Django 5.2 (Python) with JSON APIs and role-based auth
- **Frontend** — React 18 + Vite + Chart.js ("Warm Mission" design system)
- **Payments** — Razorpay online checkout + signature-verified webhooks, with an
  automatic offline / cash fallback
- **Database** — SQLite for development, Supabase (PostgreSQL) for production,
  switched purely through environment variables

---

## Key features

| Area | What the platform does |
|---|---|
| **Roles & auth** | Admin, Staff, Donor, and Volunteer accounts with role-scoped views and permissions |
| **Donors** | Complete profiles (individual / organisation), tags, giving history, and an activity timeline |
| **Campaigns** | Goals with live "raised" total and progress, automatic goal cap so a campaign stops once its target is reached |
| **Donations** | Razorpay online payment with verified signatures, plus an offline / cash fallback; lifecycle tracked to captured / failed / refunded |
| **Volunteers** | Profiles, registrations, and a background-check verification workflow approved by staff |
| **Events** | Sign-up with capacity + waitlist, and staff acceptance of registrations for upcoming events |
| **Self-service** | Donors and volunteers edit their own profiles through the dashboards |
| **Reporting** | Role-scoped dashboards (6-month donation trend, campaign progress, recent donations) and monthly CSV export |
| **UX** | Warm, human design system; dark mode; fully responsive; polished in-app toasts / confirmations instead of browser pop-ups |

---

## Quick start

Requires **Python 3.10+** and **Node 18+**.

```bash
# 1. Backend: virtualenv + install
python -m venv .venv
.venv\Scripts\activate           # PowerShell (Windows)
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt


# 3. Database + admin user
python manage.py migrate
python manage.py createsuperuser

# 4. Run the backend
python manage.py runserver       # http://127.0.0.1:8000
```

> On Windows, use `waitress` for production-like serving:
> `waitress-serve --port=8000 ngo_platform.wsgi:application`.

Then start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173 (proxies /api → :8000)
```

To build a production bundle of the frontend instead:

```bash
cd frontend
npm run build                    # outputs frontend/dist/
```

---

## Database — SQLite or Supabase

The database is chosen entirely by environment variables (see `.env.example`).
No code changes required to switch.

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_DB_ENGINE` | `sqlite3` or `postgresql` | `sqlite3` |
| `DJANGO_DB_NAME` | DB name / SQLite file path | `db.sqlite3` |
| `DJANGO_DB_HOST` / `_PORT` / `_USER` / `_PASSWORD` | Postgres connection | empty |
| `DJANGO_DB_SSLMODE` | TLS mode (auto-added for Postgres) | `require` |

**To connect Supabase (PostgreSQL):** copy `.env.example` → `.env`, set
`DJANGO_DB_ENGINE=postgresql`, and fill in the connection values from your
Supabase project's dashboard. The password belongs **only** in your local
gitignored `.env`, never in code or the template file.

---

## Project layout

```
ngo_platform/
├── manage.py
├── requirements.txt
├── ngo_platform/                # project config (settings, urls, wsgi/asgi)
├── apps/
│   ├── core/                    # donor, campaign, donation, volunteer, event,
│   │   │                        #   user-profile models + all API views
│   │   ├── models.py            # domain model + roles (Admin/Staff/Donor/Volunteer)
│   │   ├── views.py             # JSON APIs, staff workflows, donation checkout
│   │   ├── tests/               # 29 end-to-end tests (auth + CRUD + payments)
│   │   └── urls.py
│   ├── payments/                # Razorpay integration
│   │   ├── services.py          # create order, verify signature
│   │   ├── security.py          # HMAC webhook verification
│   │   └── views.py             # POST /webhooks/razorpay/
│   ├── reports/                 # dashboard aggregates + CSV export
│   └── api/                     # auth, self-service profile, user management
└── frontend/                    # React + Vite app (13 pages)
    ├── src/pages/               # login/register, 3 role dashboards, resource pages
    ├── src/components/          # design-system primitives (Logo, Icon, modals…)
    └── src/index.css            # "Warm Mission" design tokens
```

---

## Tests

```bash
python manage.py test apps.core.tests.test_auth_crud_e2e -v 2
```

29 end-to-end tests cover registration, role-based access control, CRUD on all
resources, campaign goal capping, event signup / waitlist / cancellation, and
the payment flow (Razorpay order + signature verification with a fake client).

---

## Payments (Razorpay)

- **Online:** `POST /api/campaigns/<id>/checkout/` creates a Razorpay order;
  `POST /api/donations/verify/` verifies the returned signature before marking
  the donation captured. (Test card: `4111 1111 1111 1111`.)
- **Offline fallback:** when `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` are empty
  in `.env`, donation records immediately as an offline / cash donation.
- **Webhook:** `POST /webhooks/razorpay/` reconciles `order.paid`,
  `payment.captured`, `payment.failed`, `refund.created`, … — idempotent,
  deduped by event id, and HMAC signature-verified.

See `explain.txt` in the project root for a walkthrough of both donation paths.

---

## Environment variables

Full reference in `.env.example`. Key ones:

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django signing key | `change-me-in-production` (insecure) |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | `localhost,127.0.0.1` |
| `RAZORPAY_KEY_ID` / `_SECRET` | Razorpay API credentials | empty (offline fallback) |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook signing secret | empty |
| `DONATION_CURRENCY` | Currency for donations | `INR` |
| `DJANGO_DB_*` | Database connection (see above) | SQLite |

---

## Project status

Complete and demo-ready: **45/45** feature tasks done, **29** end-to-end tests
passing, live data running on Supabase (PostgreSQL).
