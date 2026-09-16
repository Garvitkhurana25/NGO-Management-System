import Icon from './Icon.jsx'

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="card" role="status" aria-label={label}>
      <span className="skeleton skeleton-title" />
      <span className="skeleton skeleton-line" />
      <span className="skeleton skeleton-line" style={{ width: '82%' }} />
      <span className="skeleton skeleton-line" style={{ width: '58%' }} />
    </div>
  )
}

export function ErrorBlock({ error }) {
  return (
    <div className="error-block" role="alert">
      <Icon name="alert" size={16} />
      <span>
        <strong>Couldn't load data.</strong>{' '}
        {error?.message || 'Unknown error. Is the Django server running on :8000?'}
      </span>
    </div>
  )
}