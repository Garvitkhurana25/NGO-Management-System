import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { toast } from '../components/Toast.jsx'
import { useAuth } from '../auth/AuthContext.jsx'

const EMPTY = {
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  is_staff: true,
  is_superuser: false,
}

export default function Users() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [formError, setFormError] = useState(null)
  const [editing, setEditing] = useState(null) // pk being edited, or null

  const { query, setQuery, filtered } = useClientFilter(
    users ?? [],
    ['username', 'email', 'first_name', 'last_name'],
  )

  async function load() {
    try {
      setUsers((await api.users()).results)
    } catch (e) {
      setError(e)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function openCreate() {
    setEditing(null)
    setForm({ ...EMPTY })
    setFormError(null)
    setShowForm(true)
  }

  function openEdit(u) {
    setEditing(u.id)
    setForm({
      username: u.username,
      email: u.email,
      first_name: u.first_name,
      last_name: u.last_name,
      password: '',
      is_staff: u.is_staff,
      is_superuser: u.is_superuser,
    })
    setFormError(null)
    setShowForm(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setFormError(null)
    try {
      if (editing) {
        const body = {
          email: form.email,
          first_name: form.first_name,
          last_name: form.last_name,
          is_staff: form.is_staff,
          is_superuser: form.is_superuser,
        }
        if (form.password) body.password = form.password
        await api.userUpdate(editing, body)
        toast('User updated.', 'success')
      } else {
        await api.userCreate({
          username: form.username,
          password: form.password,
          email: form.email,
          first_name: form.first_name,
          last_name: form.last_name,
          is_staff: form.is_staff,
          is_superuser: form.is_superuser,
        })
        toast('User created.', 'success')
      }
      setShowForm(false)
      await load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleDeactivate(u) {
    const ok = await confirmAction({
      title: `Deactivate “${u.username}”?`,
      message: 'They can no longer sign in. You can create a new account to bring them back later.',
      confirmLabel: 'Deactivate user',
      danger: true,
    })
    if (!ok) return
    setBusy(true)
    try {
      await api.userDelete(u.id)
      toast('User deactivated.', 'info')
      await load()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  if (!users) {
    if (error) return <ErrorBlock error={error} />
    return <Loading />
  }

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  return (
    <>
      <div className="page-head">
        <h1>Users</h1>
        <button className="btn btn-primary u-right" onClick={openCreate} disabled={busy}>
          <Icon name="plus" size={15} />
          Add user
        </button>
      </div>

      {showForm && (
        <div className="card form-card">
          <h2>{editing ? `Edit ${form.username}` : 'New user'}</h2>
          {formError && (
            <div className="error-block" role="alert">{formError}</div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {!editing && (
                <>
                  <label>
                    Username *
                    <input
                      value={form.username}
                      onChange={(e) => set('username', e.target.value)}
                      required
                      autoComplete="off"
                    />
                  </label>
                  <label>
                    Password *
                    <input
                      type="password"
                      value={form.password}
                      onChange={(e) => set('password', e.target.value)}
                      required={!editing}
                      minLength={8}
                      placeholder={editing ? 'Leave blank to keep current' : 'min. 8 chars'}
                    />
                  </label>
                </>
              )}
              <label>
                Email
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                />
              </label>
              <label>
                First name
                <input
                  value={form.first_name}
                  onChange={(e) => set('first_name', e.target.value)}
                />
              </label>
              <label>
                Last name
                <input
                  value={form.last_name}
                  onChange={(e) => set('last_name', e.target.value)}
                />
              </label>
            </div>
            <div className="flex" style={{ gap: 16, marginTop: '0.5rem' }}>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.is_staff}
                  onChange={(e) => set('is_staff', e.target.checked)}
                />
                Staff (can manage donors, campaigns, etc.)
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.is_superuser}
                  onChange={(e) => set('is_superuser', e.target.checked)}
                />
                Superuser (can manage users)
              </label>
            </div>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? 'Saving…' : editing ? 'Save changes' : 'Create user'}
              </button>
              <button className="btn" type="button" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="search-box">
        <Icon name="search" size={15} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search users…"
          aria-label="Search users"
        />
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Name</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td>
                  <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Avatar name={u.username} size={26} />
                    {u.username}
                    {u.id === me?.id && <span className="small muted">(you)</span>}
                  </span>
                </td>
                <td className="muted">
                  {[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}
                </td>
                <td className="muted">{u.email || '—'}</td>
                <td>
                  {u.is_superuser ? (
                    <StatusBadge status="Superuser" />
                  ) : u.is_staff ? (
                    <StatusBadge status="Staff" />
                  ) : (
                    <StatusBadge status="viewer" />
                  )}
                </td>
                <td>
                  {u.is_active ? (
                    <span className="badge good">active</span>
                  ) : (
                    <span className="badge serious">deactivated</span>
                  )}
                </td>
                <td className="flex" style={{ justifyContent: 'flex-end' }}>
                  <button className="icon-btn" aria-label={`Edit ${u.username}`} title="Edit" onClick={() => openEdit(u)} disabled={busy}>
                    <Icon name="pencil" size={15} />
                  </button>
                  {u.id !== me?.id && (
                    <button
                      className="icon-btn"
                      aria-label={`Deactivate ${u.username}`}
                      title={u.is_active ? 'Deactivate' : 'Deactivated'}
                      onClick={() => handleDeactivate(u)}
                      disabled={busy || !u.is_active}
                    >
                      <Icon name="x" size={15} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="state-block">
                  {query ? `No users match “${query}”.` : 'No users yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}