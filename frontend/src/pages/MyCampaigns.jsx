import { Navigate, useNavigate } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { useDonate } from '../hooks/useDonate.js'
import { api } from '../api.js'
import { useAuth } from '../auth/AuthContext.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import DonateModal from '../components/DonateModal.jsx'
import Icon from '../components/Icon.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import { formatINR, titleCase } from '../lib/format.js'

/**
 * /me/campaigns — every active campaign the donor can support, with the same
 * donate flow as the dashboard. Reached from the "Active campaigns" stat card.
 */
export default function MyCampaigns() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useData(api.myCampaigns)
  const { paying, donateFor, setDonateFor, handleDonate } = useDonate({ refresh })

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />
  if (user?.role !== 'donor') return <Navigate to="/" replace />

  const campaigns = data.results ?? []

  return (
    <>
      <div className="page-head">
        <h1>Active campaigns</h1>
        <button className="btn btn-sm" onClick={() => navigate('/')}>
          <Icon name="arrowLeft" size={14} />
          Dashboard
        </button>
      </div>

      <div className="card">
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