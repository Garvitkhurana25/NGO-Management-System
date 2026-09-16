import { Link } from 'react-router-dom'

/**
 * Dashboard stat tile. Pass `to` to make the whole tile a route link (e.g. a
 * stat that opens a "see all" page); without it the tile is static.
 */
export default function StatCard({ label, value, hint, to }) {
  const body = (
    <>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </>
  )

  if (to) {
    return (
      <Link to={to} className="card stat-tile stat-link">
        {body}
      </Link>
    )
  }
  return <div className="card stat-tile">{body}</div>
}