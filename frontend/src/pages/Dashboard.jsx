import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  Tooltip,
  Filler,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import { Link } from 'react-router-dom'
import { useData } from '../hooks/useData.js'
import { api } from '../api.js'
import StatCard from '../components/StatCard.jsx'
import ProgressBar from '../components/ProgressBar.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Avatar from '../components/Avatar.jsx'
import { Loading, ErrorBlock } from '../components/States.jsx'
import { formatINR, titleCase } from '../lib/format.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, BarController, Tooltip, Filler)

function cssVar(name) {
  if (typeof document === 'undefined') return null
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || null
}

function TrendChart({ trend }) {
  // Chart palette is the validated dataviz ramp — read from the live theme.
  const color = cssVar('--series-1') || '#2a78d6'
  const grid = cssVar('--gridline') || 'rgba(0,0,0,0.1)'
  const muted = cssVar('--ink-muted') || '#898781'
  const baseline = cssVar('--baseline') || 'rgba(0,0,0,0.15)'

  const points = trend ?? []
  const labels = points.map((p) => p.month)
  const values = points.map((p) => Number(p.total || 0))

  return (
    <div className="chart-box">
      <Bar
        aria-label="Donations received per month, last six months"
        role="img"
        data={{
          labels,
          datasets: [
            {
              label: 'Donations',
              data: values,
              backgroundColor: color,
              borderRadius: 4, // 4px rounded data-ends
              maxBarThickness: 44,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            tooltip: {
              backgroundColor: cssVar('--card-strong') || '#ffffff',
              titleColor: cssVar('--ink-primary') || '#222',
              bodyColor: cssVar('--ink-primary') || '#222',
              borderColor: cssVar('--line') || '#ddd',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
              boxPadding: 4,
              callbacks: {
                label: (ctx) => ` ${formatINR(ctx.parsed.y)}`,
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              border: { color: baseline },
              ticks: { color: muted },
            },
            y: {
              beginAtZero: true,
              grid: { color: grid },
              border: { display: false },
              ticks: { color: muted, callback: (v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v) },
            },
          },
        }}
      />
    </div>
  )
}

function CampaignProgress({ campaigns }) {
  const items = campaigns ?? []
  if (items.length === 0) return <div className="muted">No campaigns yet.</div>
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '1rem' }}>
      {items.map((c) => (
        <li key={c.id}>
          <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <Link to={`/campaigns/${c.id}`} className="text-brand" style={{ fontWeight: 600 }}>
              {c.name}
            </Link>
            <StatusBadge status={titleCase(c.status)} />
          </div>
          <div className="flex" style={{ justifyContent: 'space-between', margin: '4px 0 6px' }}>
            <span className="small muted">{formatINR(c.raised)} raised</span>
            <span className="small muted num">of {formatINR(c.goal)}</span>
          </div>
          <ProgressBar percent={c.progress_percent} />
        </li>
      ))}
    </ul>
  )
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { data, loading, error } = useData(api.dashboard)

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  const { donations, trend, recent_donations, campaigns, volunteers } = data

  return (
    <>
      <div className="page-head">
        <h1>{greeting()} — here's where things stand.</h1>
        <span className="small muted">as of {data.as_of}</span>
      </div>

      <div className="stat-grid">
        <StatCard label="Total raised" value={formatINR(donations?.total)} hint={`${donations?.count ?? 0} donations`} />
        <StatCard label="Active campaigns" value={campaigns.filter((c) => c.status === 'active').length} hint={`${campaigns.length} total`} />
        <StatCard label="Volunteers" value={volunteers?.active_volunteers ?? 0} hint="active profiles" />
        <StatCard label="Hours logged" value={volunteers?.hours_logged ?? 0} hint={`${volunteers?.upcoming_open_shifts ?? 0} open shifts`} />
      </div>

      <div className="chart-grid">
        <div className="card">
          <h2>Donations — last 6 months</h2>
          <TrendChart trend={trend} />
          <details style={{ marginTop: '0.5rem' }}>
            <summary className="small">Data table</summary>
            <div className="table-wrap">
            <table>
              <caption className="small" style={{ textAlign: 'left' }}>Donations by month (accessibility view)</caption>
              <thead>
                <tr><th>Month</th><th className="num">Amount</th><th className="num">Count</th></tr>
              </thead>
              <tbody>
                {(trend ?? []).map((p) => (
                  <tr key={p.month}>
                    <td>{p.month}</td>
                    <td className="num">{formatINR(p.total)}</td>
                    <td className="num">{p.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </details>
        </div>

        <div className="card">
          <h2>Campaign progress</h2>
          <CampaignProgress campaigns={campaigns} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="page-head">
          <h2>Recent donations</h2>
          <Link to="/donations" className="small">View all</Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Donor</th>
                <th>Campaign</th>
                <th className="num">Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {(recent_donations ?? []).map((d, i) => (
                <tr key={i}>
                  <td>
                    <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                      <Avatar name={d.donor} size={26} />
                      {d.donor}
                    </span>
                  </td>
                  <td className="muted">{d.campaign || '—'}</td>
                  <td className="num">{formatINR(d.amount)}</td>
                  <td><StatusBadge status={titleCase(d.status)} /></td>
                  <td className="muted">{d.date ? new Date(d.date).toLocaleDateString('en-IN') : '—'}</td>
                </tr>
              ))}
              {(recent_donations ?? []).length === 0 && (
                <tr><td colSpan={5} className="state-block">No donations yet. Add one in the Django admin.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}