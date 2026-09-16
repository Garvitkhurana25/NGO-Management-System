import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import AuthShell from '../components/AuthShell.jsx'
import Icon from '../components/Icon.jsx'

/**
 * Public self-service signup. A registered account is either a volunteer
 * (can register for events) or a donor (can donate to campaigns). Creating the
 * account logs the user straight in.
 */
export default function Register() {
  const { register, error } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [role, setRole] = useState('volunteer')
  const [donorType, setDonorType] = useState('individual')
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!username.trim() || !password || password.length < 6) {
      setFormError('Username and a password of at least 6 characters are required.')
      return
    }
    setBusy(true)
    setFormError(null)
    const result = await register({
      username: username.trim(),
      email: email.trim(),
      password,
      role,
      donor_type: donorType,
    })
    setBusy(false)
    if (result.ok) {
      navigate('/', { replace: true })
    } else {
      setFormError(result.error || 'Registration failed.')
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle={
        role === 'volunteer'
          ? 'Volunteers can register for events, and your profile appears in the volunteers list.'
          : 'Donors can contribute to campaigns, and your profile appears in the donors list.'
      }
      onSubmit={handleSubmit}
      footer={
        <p className="auth-footer">
          <span className="muted">Staff? Ask an admin to create your account.</span>
          <Link to="/login">Sign in instead</Link>
        </p>
      }
    >
      {(formError || error) && (
        <div className="error-block" role="alert">
          <Icon name="alert" size={16} />
          <span>{formError || error?.message || 'Registration failed.'}</span>
        </div>
      )}

      <label className="field">
        I am a
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="volunteer">Volunteer — register for events</option>
          <option value="donor">Donor — contribute to campaigns</option>
        </select>
      </label>
      {role === 'donor' && (
        <label className="field">
          Donor type *
          <select value={donorType} onChange={(e) => setDonorType(e.target.value)}>
            <option value="individual">Individual</option>
            <option value="organization">Organization</option>
          </select>
        </label>
      )}
      <label className="field">
        Username *
        <input
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="e.g. asha.verma"
        />
      </label>
      <label className="field">
        Email
        <input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
      </label>
      <label className="field">
        Password *
        <span className="password-wrap">
          <input
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
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
          {busy ? 'Creating account…' : 'Create account & sign in'}
        </button>
      </div>
    </AuthShell>
  )
}