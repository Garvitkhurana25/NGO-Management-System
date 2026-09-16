import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import Toaster from './Toast.jsx'
import ConfirmHost from './ConfirmModal.jsx'
import Avatar from './Avatar.jsx'
import Logo from './Logo.jsx'
import Icon from './Icon.jsx'
import { useTheme } from '../lib/theme.js'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [theme, toggleTheme] = useTheme()

  const isRoleUser = user?.role === 'volunteer' || user?.role === 'donor'
  const whoami = user?.is_superuser
    ? 'Superuser'
    : user?.is_staff
      ? 'Staff'
      : user?.role
        ? user.role[0].toUpperCase() + user.role.slice(1)
        : 'Viewer'

  // Registered end-users get shortcuts to every page their role can open.
  // Staff/superusers get the full grouped operations navigation.
  const groups = isRoleUser
    ? user?.role === 'donor'
      ? [
          {
            label: 'My giving',
            items: [
              { to: '/', label: 'My dashboard', icon: 'home', end: true },
              { to: '/me/donations', label: 'My donations', icon: 'banknote' },
              { to: '/me/campaigns', label: 'Active campaigns', icon: 'target' },
              { to: '/me/profile', label: 'Edit profile', icon: 'pencil' },
            ],
          },
        ]
      : [
          {
            label: 'My activity',
            items: [
              { to: '/', label: 'My dashboard', icon: 'home', end: true },
              { to: '/me/profile', label: 'Edit profile', icon: 'pencil' },
            ],
          },
        ]
    : [
        {
          label: 'Overview',
          items: [{ to: '/', label: 'Dashboard', icon: 'grid', end: true }],
        },
        {
          label: 'People',
          items: [
            { to: '/donors', label: 'Donors', icon: 'heart' },
            { to: '/volunteers', label: 'Volunteers', icon: 'users' },
          ],
        },
        {
          label: 'Fundraising',
          items: [
            { to: '/donations', label: 'Donations', icon: 'banknote' },
            { to: '/campaigns', label: 'Campaigns', icon: 'target' },
          ],
        },
        {
          label: 'Events',
          items: [{ to: '/events', label: 'Events', icon: 'calendar' }],
        },
        ...(user?.is_superuser
          ? [{ label: 'Admin', items: [{ to: '/users', label: 'Users', icon: 'settings' }] }]
          : []),
      ]

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Logo />
        <nav className="nav">
          {groups.map((g) => (
            <div key={g.label || 'home'} className="nav-section">
              {g.label && <span className="nav-label">{g.label}</span>}
              {g.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                >
                  <Icon name={item.icon} size={17} />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="icon-btn theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          >
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={17} />
          </button>
          <Link to="/me/profile" className="whoami whoami-link" title="Manage profile">
            <Avatar name={user?.username} size={34} />
            <span className="whoami-text">
              <strong>{user?.username}</strong>
              <small className="muted">{whoami}</small>
            </span>
          </Link>
          <button className="btn btn-sm btn-ghost" onClick={handleLogout}>
            <Icon name="logout" size={14} />
            <span className="btn-label">Sign out</span>
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
      <Toaster />
      <ConfirmHost />
    </div>
  )
}