import { useState } from 'react'
import { useData } from '../hooks/useData.js'
import { useClientFilter } from '../hooks/useClientFilter.js'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../api.js'
import { Loading, ErrorBlock } from '../components/States.jsx'
import FormCard from '../components/FormCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import Avatar from '../components/Avatar.jsx'
import Icon from '../components/Icon.jsx'
import { confirmAction } from '../components/ConfirmModal.jsx'
import { toast } from '../components/Toast.jsx'

const EMPTY = {
  name: '',
  email: '',
  phone: '',
  skills: '',
  background_check_status: 'not_required',
  notes: '',
}

export default function Volunteers() {
  const { user } = useAuth()
  const canEdit = user?.is_superuser // only the admin edits/deletes volunteer records
  const isStaff = !!user?.is_staff
  const { data, loading, error, refresh } = useData(api.volunteers)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)

  const { query, setQuery, filtered } = useClientFilter(
    data?.results ?? [],
    ['name', 'email', 'phone', 'skills'],
  )

  async function submit(values) {
    const body = {
      name: values.name,
      email: values.email,
      phone: values.phone,
      skills: values.skills || '',
      background_check_status: values.background_check_status,
      notes: values.notes || '',
    }
    if (editing) {
      await api.volunteerUpdate(editing.id, body)
      toast('Volunteer updated.', 'success')
    } else {
      await api.volunteerCreate(body)
      toast('Volunteer added.', 'success')
    }
    setEditing(null)
    setCreating(false)
    refresh()
  }

  async function remove(v) {
    const ok = await confirmAction({
      title: `Remove “${v.name}”?`,
      message: 'Their volunteer history is kept — only the profile is removed.',
      confirmLabel: 'Remove volunteer',
      danger: true,
    })
    if (!ok) return
    try {
      await api.volunteerDelete(v.id)
      toast('Volunteer removed.', 'info')
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
  }

  async function verifyBackground(v, approved) {
    try {
      await api.volunteerBackgroundVerify(v.id, approved)
      toast(
        approved
          ? `Background check cleared for ${v.name}.`
          : `Background check rejected for ${v.name}.`,
        approved ? 'success' : 'info',
      )
    } catch (err) {
      toast(err.message, 'error')
    }
    refresh()
  }

  if (loading) return <Loading />
  if (error) return <ErrorBlock error={error} />

  return (
    <>
      <div className="page-head">
        <h1>Volunteers</h1>
        <span className="count-chip">{data.count} volunteers</span>
        <button className="btn btn-primary u-right" onClick={() => { setCreating(true); setEditing(null) }}>
          <Icon name="plus" size={15} />
          Add volunteer
        </button>
      </div>

      {isStaff && (
        <div className="card">
          <h2>Background verification</h2>
          {(data.results ?? []).filter((v) => v.background_check_status === 'pending').length === 0 ? (
            <p className="small muted">
              No volunteers waiting on a background check — self-registered volunteers appear here
              for you to approve or reject.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Volunteer</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(data.results ?? [])
                    .filter((v) => v.background_check_status === 'pending')
                    .map((v) => (
                      <tr key={v.id}>
                        <td>{v.name}</td>
                        <td className="muted">{v.email || '—'}</td>
                        <td><StatusBadge status={v.background_check_status} /></td>
                        <td className="flex" style={{ justifyContent: 'flex-end', gap: 8 }}>
                          <button className="btn btn-sm btn-primary" onClick={() => verifyBackground(v, true)}>
                            Approve
                          </button>
                          <button className="btn btn-sm" onClick={() => verifyBackground(v, false)}>
                            Reject
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {(creating || editing) && (
        <FormCard
          title={editing ? `Edit ${editing.name}` : 'Add volunteer'}
          initial={editing ? { ...editing } : { ...EMPTY }}
          onSubmit={submit}
          onCancel={() => { setCreating(false); setEditing(null) }}
          submitLabel={editing ? 'Save changes' : 'Add volunteer'}
        >
          {({ values, set }) => (
            <div className="form-grid">
              <label>
                Full name *
                <input value={values.name || ''} onChange={(e) => set('name', e.target.value)} required />
              </label>
              <label>
                Email
                <input type="email" value={values.email || ''} onChange={(e) => set('email', e.target.value)} />
              </label>
              <label>
                Phone
                <input value={values.phone || ''} onChange={(e) => set('phone', e.target.value)} />
              </label>
              <label>
                Skills / interests
                <input value={values.skills || ''} onChange={(e) => set('skills', e.target.value)} placeholder="teaching, events, fundraising" />
              </label>
              <label>
                Background check
                <select
                  value={values.background_check_status || 'not_required'}
                  onChange={(e) => set('background_check_status', e.target.value)}
                >
                  <option value="not_required">Not required</option>
                  <option value="pending">Pending</option>
                  <option value="cleared">Cleared</option>
                  <option value="rejected">Rejected</option>
                </select>
              </label>
              <label>
                Notes
                <textarea value={values.notes || ''} onChange={(e) => set('notes', e.target.value)} />
              </label>
            </div>
          )}
        </FormCard>
      )}

      <div className="search-box">
        <Icon name="search" size={15} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search volunteers…"
          aria-label="Search volunteers"
        />
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th className="num">Hours</th>
              <th>Background</th>
              {canEdit && <th></th>}
            </tr>
          </thead>
          <tbody>
            {filtered.map((v) => (
              <tr key={v.id}>
                <td>
                  <span className="flex" style={{ alignItems: 'center', gap: 8 }}>
                    <Avatar name={v.name} size={28} />
                    {v.name}
                  </span>
                </td>
                <td className="muted">{v.email || '—'}</td>
                <td className="muted">{v.phone || '—'}</td>
                <td className="num">{v.total_hours}</td>
                <td><StatusBadge status={v.background_check_status} /></td>
                {canEdit && (
                  <td className="flex" style={{ justifyContent: 'flex-end' }}>
                    <button className="icon-btn" aria-label={`Edit ${v.name}`} title="Edit" onClick={() => { setEditing(v); setCreating(false) }}>
                      <Icon name="pencil" size={15} />
                    </button>
                    <button className="icon-btn" aria-label={`Remove ${v.name}`} title="Remove" onClick={() => remove(v)}>
                      <Icon name="trash" size={15} />
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={canEdit ? 6 : 5} className="state-block">
                  {query ? `No volunteers match “${query}”.` : 'No volunteers yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}