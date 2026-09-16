import Icon from './Icon.jsx'

// Warm left-hand brand panel for the auth pages (login/register). Everything
// here is pure presentation — the forms live in the right-hand `children` slot.

const BULLETS = [
  { icon: 'heart', text: 'Track donors, donations and campaigns in one warm, clear place.' },
  { icon: 'users', text: 'Coordinate volunteers and event registrations across the team.' },
  { icon: 'sparkles', text: 'Reporting that reads like a mission — not a spreadsheet.' },
]

export default function AuthShell({ title, subtitle, onSubmit, children, footer }) {
  return (
    <div className="auth-shell">
      <aside className="auth-panel">
        <div className="auth-brand">
          <span className="logo-mark">
            <Icon name="heart" size={18} />
          </span>
          <span className="logo-text">
            <strong>NGO Platform</strong>
            <small>Causes, cared for</small>
          </span>
        </div>
        <div className="auth-panel-body">
          <h2>Together, the work gets done.</h2>
          <ul className="auth-bullets">
            {BULLETS.map((b) => (
              <li key={b.icon}>
                <span className="auth-bullet-icon">
                  <Icon name={b.icon} size={16} />
                </span>
                <span>{b.text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="auth-panel-foot">
          A demo of mission-led operations — built for the hackathon.
        </p>
      </aside>
      <main className="auth-form">
        <form className="auth-card" onSubmit={onSubmit}>
          <h1 className="auth-title">{title}</h1>
          <p className="auth-sub">{subtitle}</p>
          {children}
          {footer}
        </form>
      </main>
    </div>
  )
}