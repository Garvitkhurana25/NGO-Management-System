import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import AuthShell from '../components/AuthShell.jsx'
import Icon from '../components/Icon.jsx'

export default function Login() {
  const { login, error } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState(null)

  const from = location.state?.from?.pathname || '/'

  async function handleSubmit(e) {
    e.preventDefault()
    if (!username.trim() || !password) {
      setFormError('Username and password are required.')
      return
    }
    setBusy(true)
    setFormError(null)
    const result = await login(username.trim(), password)
    setBusy(false)
    if (result.ok) {
      navigate(from, { replace: true })
    } else {
      setFormError(result.error || 'Login failed.')
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in with your organization account to manage donors, donations, campaigns and events."
      onSubmit={handleSubmit}
      footer={
        <p className="auth-footer">
          <span className="muted">Volunteer or donor?</span>
          <Link to="/register">Create an account</Link>
        </p>
      }
    >
      {(formError || error) && (
        <div className="error-block" role="alert">
          <Icon name="alert" size={16} />
          <span>{formError || error?.message || 'Login failed.'}</span>
        </div>
      )}

      <label className="field">
        Username
        <input
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="admin"
        />
      </label>
      <label className="field">
        Password
        <span className="password-wrap">
          <input
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="button"
            className="icon-btn password-toggle"
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((p) => !p)}
          >
            <Icon name={showPassword ? 'eyeOff' : 'eye'} size={16} />
          </button>
        </span>
      </label>

      <div className="auth-actions">
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </div>
    </AuthShell>
  )
}