import { useParams, Link } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Icon from '../components/Icon.jsx'
import { formatINR, titleCase, formatDate } from '../lib/format.js'

function Ring({ percent, size = 170 }) {
  const p = Math.max(0, Math.min(100, Number(percent) || 0))
  const r = 74
  const c = 2 * Math.PI * r
  const offset = c * (1 - p / 100)
  return (
    <svg className="progress-ring" width={size} height={size} viewBox="0 0 170 170" role="img"
      aria-label={`${p}% funded`}>
      <circle className="track" cx="85" cy="85" r={r} strokeWidth="12" />
      <circle
        className="bar"
        cx="85" cy="85" r={r}
        strokeWidth="12"
        strokeDasharray={c}
        strokeDashoffset={offset}
        transform="rotate(-90 85 85)"
      />
      <text className="ring-label" x="85" y="78">{p}%</text>
      <text className="ring-sub" x="85" y="102">funded</text>
    </svg>
  )
}

export default function CampaignDetail() {
  const { id } = useParams()
  const { data, loading, error } = useData(() => api.campaign(id), [id])

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  return (
    <>
      <div className="page-head">
        <Link to="/campaigns" className="btn btn-sm btn-ghost">
          <Icon name="arrowLeft" size={14} />
          Campaigns
        </Link>
      </div>

      <div className="card">
        <div className="flex" style={{ alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
          <Ring percent={data.progress_percent} />
          <div style={{ minWidth: 240, flex: 1 }}>
            <h1 style={{ marginBottom: 6 }}>{data.name}</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <StatusBadge status={titleCase(data.status)} />
              <span className="small muted">{data.donations.length} donations</span>
            </div>
            <div className="flex" style={{ alignItems: 'baseline', gap: 12, marginBottom: 10 }}>
              <span className="stat-value text-brand">{formatINR(data.raised)}</span>
              <span className="small muted">raised of {formatINR(data.goal)} goal</span>
            </div>
            <div style={{ maxWidth: 420 }}>
              <ProgressBar percent={data.progress_percent} />
            </div>
          </div>
        </div>

        {data.description ? (
          <p className="muted" style={{ marginTop: 16 }}>{data.description}</p>
        ) : null}
      </div>

      <div className="card">
        <h2>Details</h2>
        <dl className="kv-grid" style={{ marginTop: 8 }}>
          <div className="kv">
            <dt>Starts</dt>
            <dd>{formatDate(data.start_date)}</dd>
          </div>
          <div className="kv">
            <dt>Ends</dt>
            <dd>{formatDate(data.end_date)}</dd>
          </div>
          <div className="kv">
            <dt>Goal</dt>
            <dd>{formatINR(data.goal)}</dd>
          </div>
          <div className="kv">
            <dt>Raised</dt>
            <dd>{formatINR(data.raised)}</dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <h2>Donations ({data.donations.length})</h2>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Donor</th>
                <th className="num">Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.donations.map((d) => (
                <tr key={d.id}>
                  <td>{d.donor}</td>
                  <td className="num">{formatINR(d.amount)}</td>
                  <td><StatusBadge status={titleCase(d.status)} /></td>
                  <td className="muted">{formatDate(d.date)}</td>
                </tr>
              ))}
              {data.donations.length === 0 && (
                <tr><td colSpan={4} className="state-block">No donations against this campaign yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}