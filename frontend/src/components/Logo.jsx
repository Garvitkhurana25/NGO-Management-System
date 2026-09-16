// Brand block: a warm monogram mark + wordmark. The name/motto live in one
// constant so re-branding the demo is a one-line change.
const BRAND = { name: 'NGO Platform', motto: 'Causes, cared for' }

export default function Logo({ compact = false }) {
  return (
    <div className={`logo${compact ? ' logo-compact' : ''}`}>
      <span className="logo-mark" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z" />
        </svg>
      </span>
      {!compact && (
        <span className="logo-text">
          <strong>{BRAND.name}</strong>
          <small>{BRAND.motto}</small>
        </span>
      )}
    </div>
  )
}

export { BRAND }