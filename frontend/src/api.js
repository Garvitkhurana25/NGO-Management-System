// Fetch wrapper for the Django JSON APIs.
//
// Auth model: Django session cookies (+ CSRF). Same origin is guaranteed by the
// Vite dev proxy (`/api` → http://127.0.0.1:8000), so fetch sends our session
// cookie automatically. We echo the CSRF cookie back via the `X-CSRFToken`
// header on every non-GET request. Django 5.2's login_required returns 403 for
// requests that don't accept text/html (all plain fetches), so an expired
// session surfaces as a 403 with no body -> handled by the UI.
const BASE = '/api'

function getCsrfToken() {
  const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : null
}

async function request(path, options = {}) {
  const { method = 'GET', body, headers = {} } = options
  const csrf = getCsrfToken()

  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(csrf && method !== 'GET' ? { 'X-CSRFToken': csrf } : {}),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  if (!res.ok) {
    const err = new Error(`${method} ${path} → ${res.status} ${res.statusText}`)
    err.status = res.status
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) {
      try {
        const payload = await res.json()
        if (payload && payload.error) err.message = payload.error
        if (payload && payload.code) err.code = payload.code
      } catch {
        /* keep generic message */
      }
    }
    throw err
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return null
}

function get(path) {
  return request(path)
}

export const api = {
  // ---- auth ----
  login: (username, password) =>
    request('/auth/login/', { method: 'POST', body: { username, password } }),
  register: (body) => request('/auth/register/', { method: 'POST', body }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  me: () => request('/auth/me/'),
  myRegistrations: () => get('/me/registrations/'),
  myDonations: () => get('/me/donations/'),
  myCampaigns: () => get('/me/campaigns/'),
  meSummary: () => get('/me/summary/'),
  meProfileUpdate: (body) => request('/me/profile/', { method: 'PATCH', body }),

  // ---- user management (superuser) ----
  users: () => request('/users/'),
  userCreate: (body) => request('/users/create/', { method: 'POST', body }),
  userUpdate: (id, body) => request(`/users/${id}/`, { method: 'PATCH', body }),
  userDelete: (id) => request(`/users/${id}/delete/`, { method: 'DELETE' }),

  // ---- dashboard + read ----
  dashboard: () => get('/dashboard/'),
  donors: () => get('/donors/'),
  donor: (id) => get(`/donors/${id}/`),
  donations: () => get('/donations/'),
  campaigns: () => get('/campaigns/'),
  campaign: (id) => get(`/campaigns/${id}/`),
  volunteers: () => get('/volunteers/'),
  events: () => get('/events/'),
  monthlyCsv: (year, month) =>
    `${BASE}/reports/monthly-donations.csv?year=${year}&month=${month}`,

  // ---- resource mutations (staff) ----
  donorCreate: (body) => request('/donors/create/', { method: 'POST', body }),
  donorUpdate: (id, body) => request(`/donors/${id}/update/`, { method: 'PATCH', body }),
  donorDelete: (id) => request(`/donors/${id}/delete/`, { method: 'DELETE' }),
  donationCreate: (body) => request('/donations/create/', { method: 'POST', body }),
  campaignCreate: (body) => request('/campaigns/create/', { method: 'POST', body }),
  campaignUpdate: (id, body) => request(`/campaigns/${id}/update/`, { method: 'PATCH', body }),
  campaignDelete: (id) => request(`/campaigns/${id}/delete/`, { method: 'DELETE' }),
  volunteerCreate: (body) => request('/volunteers/create/', { method: 'POST', body }),
  volunteerUpdate: (id, body) => request(`/volunteers/${id}/update/`, { method: 'PATCH', body }),
  volunteerDelete: (id) => request(`/volunteers/${id}/delete/`, { method: 'DELETE' }),
  eventCreate: (body) => request('/events/create/', { method: 'POST', body }),
  eventUpdate: (id, body) => request(`/events/${id}/update/`, { method: 'PATCH', body }),
  eventDelete: (id) => request(`/events/${id}/delete/`, { method: 'DELETE' }),

  // ---- role actions (registered users) ----
  eventRegister: (id) => request(`/events/${id}/register/`, { method: 'POST' }),
  eventCancel: (id) => request(`/events/${id}/cancel/`, { method: 'POST' }),

  // ---- staff approval workflows ----
  eventRegistrationsPending: () => get('/events/registrations/pending/'),
  eventRegistrationConfirm: (id) => request(`/event-registrations/${id}/confirm/`, { method: 'POST' }),
  volunteerBackgroundVerify: (id, approved) =>
    request(`/volunteers/${id}/background-verify/`, { method: 'POST', body: { approved } }),
  campaignDonate: (id, amount) =>
    request(`/campaigns/${id}/donate/`, { method: 'POST', body: { amount } }),
  // ---- online payment (real Razorpay checkout + client-side verify) ----
  donationCheckout: (id, amount) =>
    request(`/campaigns/${id}/checkout/`, { method: 'POST', body: { amount } }),
  donationVerify: (donationId, payment) =>
    request('/donations/verify/', {
      method: 'POST',
      body: { donation_id: donationId, ...payment },
    }),
}