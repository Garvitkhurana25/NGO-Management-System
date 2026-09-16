// In-app confirmation dialog — replaces the last window.confirm() calls so the
// demo never shows native browser chrome. Any module can call
//   const ok = await confirmAction({ title, message, confirmLabel, danger })
// and the single <ConfirmHost /> mounted in Layout renders the dialog.
// Same module-level-listener pattern as Toast.jsx.
import { useEffect, useRef, useState } from 'react'
import Icon from './Icon.jsx'

const listeners = new Set()
let nextId = 0

export function confirmAction({
  title = 'Are you sure?',
  message = '',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
} = {}) {
  return new Promise((resolve) => {
    listeners.forEach((cb) =>
      cb({ id: ++nextId, title, message, confirmLabel, cancelLabel, danger, resolve }),
    )
  })
}

export default function ConfirmHost() {
  const [item, setItem] = useState(null)
  const confirmRef = useRef(null)

  useEffect(() => {
    const onConfirm = (pending) => setItem(pending)
    listeners.add(onConfirm)
    return () => listeners.delete(onConfirm)
  }, [])

  useEffect(() => {
    if (!item) return
    confirmRef.current?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setItem(null)
        item.resolve(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [item])

  if (!item) return null

  const close = (result) => {
    setItem(null)
    item.resolve(result)
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close(false)
      }}
    >
      <div
        className="modal-card confirm-card"
        role="alertdialog"
        aria-modal="true"
        aria-label={item.title}
      >
        <div className={`confirm-icon${item.danger ? ' danger' : ' brand'}`}>
          <Icon name={item.danger ? 'trash' : 'sparkles'} size={20} />
        </div>
        <h2 className="confirm-title">{item.title}</h2>
        {item.message ? <p className="small muted confirm-message">{item.message}</p> : null}
        <div className="flex confirm-actions" style={{ justifyContent: 'flex-end', marginTop: '0.5rem' }}>
          <button type="button" className="btn" onClick={() => close(false)}>
            {item.cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            className={item.danger ? 'btn btn-danger-solid' : 'btn btn-primary'}
            onClick={() => close(true)}
          >
            {item.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}