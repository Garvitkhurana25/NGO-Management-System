# NGO Platform — React frontend

Vite + React 18 + React Router + Chart.js. Consumes the Django JSON APIs in the
parent directory via a dev-time `/api` proxy (no CORS involved).

## Run

Requires the Django dev server on `:8000`:

```bash
cd ../                    # ngo_platform/
python manage.py runserver
```

Then, in this directory:

```bash
npm install
npm run dev               # http://localhost:5173
```

## Pages

| Route | Data source |
|---|---|
| `/` (Dashboard) | `/api/dashboard/` — stat tiles, 6-month donation bar chart, campaign progress, recent donations |
| `/donors`, `/donors/:id` | `/api/donors/`, `/api/donors/:id/` (profile + timeline) |
| `/donations` | `/api/donations/` |
| `/campaigns`, `/campaigns/:id` | `/api/campaigns/`, `/api/campaigns/:id/` (progress + donations) |
| `/volunteers` | `/api/volunteers/` |
| `/events` | `/api/events/` |

## Notes

- The APIs are currently **read-only**. Write flows (add donor, log donation,
  sign up a volunteer) go through the Django admin at
  `http://127.0.0.1:8000/admin/` for now.
- Charts use the validated dataviz palette (blue single-series bar chart); a
  `<details>` data-table gives an accessible fallback per chart.
- The prod build (`npm run build`) emits static files into `dist/` — the Django
  backend has no serving config for them yet (see roadmap step below).

## Roadmap (frontend)

1. `npm run build` + serve `dist/` from Django (or a CDN).
2. Write endpoints in Django (`POST /api/donors/`, etc.) + auth; wire forms.
3. Real campaigns detail chart (donation trend per campaign).