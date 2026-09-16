/**
 * Shared inline add/edit card. `onSubmit(values)` may throw; the error is shown
 * inside the card. `children` (the input fields) are passed the current values
 * and a `set(name, value)` updater so pages stay declarative.
 */
import { useState } from 'react'

export default function FormCard({
  title,
  initial = {},
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  submittingLabel = 'Saving…',
  children,
}) {
  const [values, setValues] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function set(name, value) {
    setValues((v) => ({ ...v, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await onSubmit(values)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="card form-card">
      <h2>{title}</h2>
      {error && (
        <div className="error-block" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        {children({ values, set })}
        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? submittingLabel : submitLabel}
          </button>
          <button className="btn" type="button" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}