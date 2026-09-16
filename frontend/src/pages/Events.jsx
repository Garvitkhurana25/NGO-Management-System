import { useCallback, useState } from 'react'
import { useData } from '../hooks/useData.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import FormCard from '../components/FormCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { toast } from '../components/Toast.jsx'
import { formatINR, titleCase } from '../lib/format.js'

const EMPTY = {
  name: '',
  description: '',
  location: '',
  capacity: '',
  ticket_price: '',
  status: 'published',
  start_at: '',
  end_at: '',
  campaign_id: '',
}

// For datetime-local inputs -> backend wants ISO YYYY-MM-DDTHH:MM (naive local).
function toLocalISO(dateVal) {
  if (!dateVal) return null
  const d = new Date(dateVal)
  if (Number.isNaN(d.getTime())) return null
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromISOLocal(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function Events() {
  const { user } = useAuth()
  const { data, loading, error, refresh } = useData(api.events)
  const { data: campaigns, refresh: refreshCamps } = useData(api.campaigns)
  const { data: my, loading: myLoading, error: myError, refresh: refreshMy } = useData(api.myRegistrations)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)

  const isStaff = !!user?.is_staff
  const pendingFn = useCallback(
    () => (isStaff ? api.eventRegistrationsPending() : Promise.resolve({ count: 0, results: [] })),
    [isStaff],
  )
  const {
    data: pending,
    loading: pendingLoading,
    error: pendingError,
    refresh: refreshPending,
  } = useData(pendingFn, [isStaff])

  const isVolunteer = user?.role === 'volunteer'
  const myRows = my?.results || []
  // Events this volunteer is currently registered for (cancelled ones don't count).
  const registeredIds = new Set(myRows.filter((r) => r.status !== 'cancelled').map((r) => r.event_id))

  const { query, setQuery, filtered } = useClientFilter(
    data?.results ?? [],
    ['name', 'location', 'campaign', 'status'],
  )

  async function submit(values) {
    const body = {
      name: values.name,
      description: values.description || '',
      location: values.location || '',
      capacity: values.capacity || null,
      ticket_price: values.ticket_price || 0,
      status: values.status,
      start_at: toLocalISO(values.start_at),
      end_at: toLocalISO(values.end_at),
      campaign_id: values.campaign_id || null,
    }
    if (editing) {
      await api.eventUpdate(editing.id, body)
      toast('Event updated.', 'success')
    } else {
      await api.eventCreate(body)
      toast('Event added.', 'success')
    }
    setEditing(null)
    setCreating(false)
    refresh()
    refreshCamps()
  }

  async function remove(e) {
    const ok = await confirmAction({
      title: `Delete “${e.name}”?`,
      message: 'Registrations for this event are deleted too. This can’t be undone.',
      confirmLabel: 'Delete event',
      danger: true,
    })
    if (!ok) return
    try {
      await api.eventDelete(e.id)
      toast('Event deleted.', 'info')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
    refreshCamps()
    refreshMy()
  }

  async function onRegister(e) {
    try {
      await api.eventRegister(e.id)
      toast(`You’re registered for “${e.name}” — see you there!`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
    refreshMy()
  }

  async function onCancel(eventId) {
    const ok = await confirmAction({
      title: 'Cancel registration?',
      message: 'You can register again later if you change your mind.',
      confirmLabel: 'Cancel registration',
      danger: true,
    })
    if (!ok) return
    try {
      await api.eventCancel(eventId)
      toast('Registration cancelled.', 'info')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
    refreshMy()
  }

  async function onAccept(reg) {
    try {
      await api.eventRegistrationConfirm(reg.id)
      toast(`Accepted ${reg.volunteer} for “${reg.event_name}”.`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
    refreshPending()
    refresh()
  }

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  const campOptions = (campaigns?.results || []).map((c) => (
    <option key={c.id} value={c.id}>{c.name}</option>
  ))

  return (
    <>
      <div className="page-head">
        <h1>Events</h1>
        <span className="count-chip">{data.count} events</span>
        {!isVolunteer && (
          <button className="btn btn-primary u-right" onClick={() => { setCreating(true); setEditing(null) }}>
            <Icon name="plus" size={15} />
            Add event
          </button>
        )}
      </div>

      {isStaff && (
        <div className="card">
          <h2>Registrations to accept</h2>
          {pendingError ? (
            <ErrorBlock error={pendingError} />
          ) : pendingLoading ? (
            <Loading />
          ) : (pending?.results ?? []).length === 0 ? (
            <p className="small muted">
              Nothing waiting for approval — paid signups and waitlisted volunteers show up here
              for you to accept.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Volunteer</th>
                    <th>Starts</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(pending.results ?? []).map((reg) => (
                    <tr key={reg.id}>
                      <td>{reg.event_name}</td>
                      <td>
                        {reg.volunteer}
                        {reg.volunteer_email ? <span className="muted"> · {reg.volunteer_email}</span> : null}
                      </td>
                      <td className="muted">{reg.event_start ? new Date(reg.event_start).toLocaleString('en-IN') : '—'}</td>
                      <td><StatusBadge status={titleCase(reg.status)} /></td>
                      <td className="flex" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn btn-sm btn-primary" onClick={() => onAccept(reg)}>
                          Accept
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {isVolunteer && (
        <div className="card">
          <h3>My registrations</h3>
          {myError ? (
            <ErrorBlock error={myError} />
          ) : myLoading ? (
            <Loading />
          ) : myRows.length === 0 ? (
            <p className="small muted">You haven’t registered for any events yet. Find one below and hit Register.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Starts</th>
                    <th>Status</th>
                    <th className="num">Ticket</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {myRows.map((r) => (
                    <tr key={r.id}>
                      <td>{r.event_name}</td>
                      <td className="muted">{r.event_start ? new Date(r.event_start).toLocaleString('en-IN') : '—'}</td>
                      <td><StatusBadge status={titleCase(r.status)} /></td>
                      <td className="num">{formatINR(r.ticket_price)}</td>
                      <td className="flex" style={{ justifyContent: 'flex-end' }}>
                        {r.status !== 'cancelled' && (
                          <button className="btn btn-sm" onClick={() => onCancel(r.event_id)}>Cancel</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {(creating || editing) && (
        <FormCard
          title={editing ? `Edit ${editing.name}` : 'Add event'}
          initial={
            editing
              ? { ...editing, start_at: fromISOLocal(editing.start_at), end_at: fromISOLocal(editing.end_at) }
              : { ...EMPTY }
          }
          onSubmit={submit}
          onCancel={() => { setCreating(false); setEditing(null) }}
          submitLabel={editing ? 'Save changes' : 'Add event'}
        >
          {({ values, set }) => (
            <div className="form-grid">
              <label>
                Name *
                <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
              </label>
              <label>
                Location
                <input value={values.location || ''} onChange={(e) => set('location', e.target.value)} />
              </label>
              <label>
                Starts
                <input type="datetime-local" value={values.start_at || ''} onChange={(e) => set('start_at', e.target.value)} />
              </label>
              <label>
                Ends
                <input type="datetime-local" value={values.end_at || ''} onChange={(e) => set('end_at', e.target.value)} />
              </label>
              <label>
                Capacity (0 = unlimited)
                <input type="number" min="0" value={values.capacity || ''} onChange={(e) => set('capacity', e.target.value)} />
              </label>
              <label>
                Ticket price (INR)
                <input type="number" min="0" step="0.01" value={values.ticket_price || ''} onChange={(e) => set('ticket_price', e.target.value)} />
              </label>
              <label>
                Status
                <select value={values.status || 'published'} onChange={(e) => set('status', e.target.value)}>
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
              <label>
                Linked campaign
                <select value={values.campaign_id || ''} onChange={(e) => set('campaign_id', e.target.value)}>
                  <option value="">— None —</option>
                  {campOptions}
                </select>
              </label>
              <label className="full">
                Description
                <textarea value={values.description || ''} onChange={(e) => set('description', e.target.value)} />
              </label>
            </div>
          )}
        </FormCard>
      )}

      <div className="search-box">
        <Icon name="search" size={15} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search events…"
          aria-label="Search events"
        />
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Campaign</th>
              <th>Starts</th>
              <th className="num">Registrations</th>
              <th className="num">Revenue</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id}>
                <td>{e.name}</td>
                <td><StatusBadge status={titleCase(e.status)} /></td>
                <td className="muted">{e.campaign || '—'}</td>
                <td className="muted">{new Date(e.start_at).toLocaleString('en-IN')}</td>
                <td className="num">{e.registrations}</td>
                <td className="num">{formatINR(e.revenue)}</td>
                <td className="flex" style={{ justifyContent: 'flex-end' }}>
                  {isVolunteer ? (
                    registeredIds.has(e.id) ? (
                      <span className="small muted">Registered ✓</span>
                    ) : (
                      <button className="btn btn-sm" onClick={() => onRegister(e)}>Register</button>
                    )
                  ) : (
                    <>
                      <button className="icon-btn" aria-label={`Edit ${e.name}`} title="Edit" onClick={() => { setEditing(e); setCreating(false) }}>
                        <Icon name="pencil" size={15} />
                      </button>
                      <button className="icon-btn" aria-label={`Delete ${e.name}`} title="Delete" onClick={() => remove(e)}>
                        <Icon name="trash" size={15} />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="state-block">
                  {query ? `No events match “${query}”.` : 'No events yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}