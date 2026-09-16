// Maps a domain status string to the dataviz status/neutral badge classes.
const GOOD = new Set(['captured', 'succeeded', 'confirmed', 'attended', 'cleared', 'active', 'completed', 'open', 'published', 'paid'])
const WARNING = new Set(['pending', 'initiated', 'part_refunded', 'order_created', 'waitlisted', 'signed_up', 'checked_in', 'scheduled'])
const SERIOUS = new Set(['refunded', 'draft', 'positive', 'locked', 'no_show'])
const CRITICAL = new Set(['failed', 'cancelled', 'rejected', 'expired'])

export function statusClass(status) {
  if (!status) return 'neutral'
  const key = String(status).toLowerCase()
  if (GOOD.has(key)) return 'good'
  if (WARNING.has(key)) return 'warning'
  if (SERIOUS.has(key)) return 'serious'
  if (CRITICAL.has(key)) return 'critical'
  return 'neutral'
}

export default function StatusBadge({ status }) {
  return <span className={`badge ${statusClass(status)}`}>{status ?? '—'}</span>
}