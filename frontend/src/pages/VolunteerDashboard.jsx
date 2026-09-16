import { Link, useNavigate } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { toast } from '../components/Toast.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import { formatINR, titleCase } from '../lib/format.js'

function dateChip(iso) {
  const d = iso ? new Date(iso) : null
  if (!d || Number.isNaN(d.getTime())) return null
  return { day: d.getDate(), month: d.toLocaleDateString('en-IN', { month: 'short' }) }
}

export default function VolunteerDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useData(api.meSummary)

  async function onRegister(eventId) {
    try {
      await api.eventRegister(eventId)
      toast('You’re registered — see you there!', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
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
  }

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  const regs = data.registrations ?? []
  const upcoming = data.upcoming_events ?? []
  const profile = data.profile
  const stats = data.stats ?? {}

  return (
    <>
      <div className="page-head">
        <h1>
          <Link
            to="/me/profile"
            className="flex whoami-link"
            style={{ alignItems: 'center', gap: 10 }}
            title="Manage profile"
          >
            <Avatar name={profile?.name ?? user?.username} size={38} />
            {profile?.name ?? user?.username}
          </Link>
        </h1>
        <span className="badge good">Volunteer</span>
        <button className="btn btn-sm u-right" onClick={() => navigate('/me/profile')}>
          <Icon name="pencil" size={14} />
          Edit profile
        </button>
      </div>

      <div className="stat-grid">
        <StatCard label="Active registrations" value={stats.active_registrations ?? 0} hint="events you’re signed up for" />
        <StatCard label="Upcoming events" value={stats.upcoming_events ?? 0} hint="you can register for these" />
        <StatCard label="Hours logged" value={stats.total_hours ?? '0'} hint="volunteer hours" />
        {profile?.background_check_status ? (
          <StatCard label="Background check" value={titleCase(profile.background_check_status)} hint={profile?.skills ? `Skills: ${profile.skills}` : '—'} />
        ) : (
          <StatCard label="Skills" value={profile?.skills ? 'Listed' : '—'} hint="comma-separated" />
        )}
      </div>

      <div className="card">
        <h2>My registrations</h2>
        {regs.length === 0 ? (
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
                {regs.map((r) => (
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

      <div className="card">
        <h2>Upcoming events</h2>
        {upcoming.length === 0 ? (
          <p className="small muted">No upcoming events right now. Check back soon.</p>
        ) : (
          <div className="event-grid">
            {upcoming.map((e) => {
              const chip = dateChip(e.start_at)
              return (
                <div className="event-card" key={e.id}>
                  <div className="flex" style={{ alignItems: 'center', gap: 12 }}>
                    {chip && (
                      <span className="date-chip">
                        <strong>{chip.day}</strong>
                        <small>{chip.month}</small>
                      </span>
                    )}
                    <div>
                      <h3>{e.name}</h3>
                      <span className="small muted">{e.start_at ? new Date(e.start_at).toLocaleString('en-IN', { weekday: 'short', hour: 'numeric', minute: '2-digit' }) : '—'}</span>
                    </div>
                  </div>
                  <div className="event-meta">
                    {e.location && (
                      <span><Icon name="grid" size={13} /> {e.location}</span>
                    )}
                    <span><Icon name="banknote" size={13} /> {formatINR(e.ticket_price)}</span>
                  </div>
                  <div className="event-actions">
                    {e.registered ? (
                      <span className="small muted">Registered ✓</span>
                    ) : (
                      <button className="btn btn-sm btn-primary" onClick={() => onRegister(e.id)}>
                        Register
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}