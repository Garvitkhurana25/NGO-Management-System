import { Link, useNavigate } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { useDonate } from '../hooks/useDonate.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import { formatINR, titleCase } from '../lib/format.js'
import DonateModal from '../components/DonateModal.jsx'

export default function DonorDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useData(api.meSummary)
  const { paying, donateFor, setDonateFor, handleDonate } = useDonate({ refresh })

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  const donations = data.donations ?? []
  const campaigns = data.campaigns ?? []
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
        <span className="badge good">Donor</span>
        <button className="btn btn-sm u-right" onClick={() => navigate('/me/profile')}>
          <Icon name="pencil" size={14} />
          Edit profile
        </button>
      </div>

      <div className="stat-grid">
        <StatCard to="/me/donations" label="Total given" value={formatINR(stats.total_given)} hint="lifetime donations" />
        <StatCard to="/me/donations" label="Donations" value={stats.donations_count ?? 0} hint="recent transactions" />
        <StatCard to="/me/campaigns" label="Active campaigns" value={stats.active_campaigns ?? 0} hint="you can support these" />
        <StatCard label="Donor type" value={profile?.donor_type ? titleCase(profile.donor_type) : '—'} hint={profile?.company || '—'} />
      </div>

      <div className="card">
        <div className="flex card-head-row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Active campaigns</h2>
          <Link to="/me/campaigns" className="small">View all →</Link>
        </div>
        {campaigns.length === 0 ? (
          <p className="small muted">No active campaigns right now. Check back soon.</p>
        ) : (
          <div className="event-grid">
            {campaigns.map((c) => (
              <div className="event-card" key={c.id}>
                <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <h3>{c.name}</h3>
                  <StatusBadge status={titleCase(c.status)} />
                </div>
                <div>
                  <div className="flex" style={{ justifyContent: 'space-between', margin: '4px 0 6px' }}>
                    <span className="small muted">{formatINR(c.raised)} raised</span>
                    <span className="small muted num">of {formatINR(c.goal)}</span>
                  </div>
                  <ProgressBar percent={c.progress_percent} />
                </div>
                <div className="event-actions">
                  {c.goal_reached ? (
                    <span className="badge good">Goal reached ✓</span>
                  ) : (
                    <>
                      <span className="small muted num">{c.progress_percent}% funded</span>
                      <button className="btn btn-sm" disabled={paying} onClick={() => setDonateFor(c)}>
                        <span>Donate</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="flex card-head-row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>My donations</h2>
          <Link to="/me/donations" className="small">View all →</Link>
        </div>
        {donations.length === 0 ? (
          <p className="small muted">You haven’t made any donations yet. Pick a campaign above and give.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th className="num">Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((d) => (
                  <tr key={d.id}>
                    <td className="muted">{d.campaign || '—'}</td>
                    <td className="num">{formatINR(d.amount)}</td>
                    <td><StatusBadge status={titleCase(d.status)} /></td>
                    <td className="muted">{d.date ? new Date(d.date).toLocaleDateString('en-IN') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {donateFor && (
        <DonateModal
          campaign={donateFor}
          onCancel={() => setDonateFor(null)}
          onConfirm={(amount) => {
            setDonateFor(null)
            handleDonate(donateFor, amount)
          }}
        />
      )}
    </>
  )
}