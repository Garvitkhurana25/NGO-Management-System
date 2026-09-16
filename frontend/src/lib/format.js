export function formatINR(value) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num)) return '—'
  return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function titleCase(s) {
  if (!s) return '—'
  return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}