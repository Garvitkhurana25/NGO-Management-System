import { useEffect, useState } from 'react'
import Icon from './Icon.jsx'

// In-app notification toasts — replaces browser-native alert()/confirm boxes so
// the demo never shows the "localhost says:" browser chrome. Any module can call
// toast(message, type) and the single <Toaster /> mounted in the Layout shows it.
//
// Types: 'info' (neutral), 'success' (green), 'error' (red), 'warning' (amber).

const listeners = new Set()

export function toast(message, type = 'info') {
  const item = { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, message, type }
  listeners.forEach((cb) => cb(item))
}

const ICONS = { success: 'check', error: 'alert', warning: 'info', info: 'info' }

export default function Toaster({ duration = 6000 }) {
  const [items, setItems] = useState([])

  useEffect(() => {
    const onToast = (item) => {
      setItems((list) => [...list, item])
      setTimeout(() => setItems((list) => list.filter((t) => t.id !== item.id)), duration)
    }
    listeners.add(onToast)
    return () => listeners.delete(onToast)
  }, [duration])

  return (
    <div className="toaster" aria-live="polite" role="status">
      {items.map((t) => (
        <div
          key={t.id}
          className={`toast ${t.type || 'info'}`}
          onClick={() => setItems((list) => list.filter((x) => x.id !== t.id))}
          title="Dismiss"
        >
          <Icon name={ICONS[t.type] || 'info'} size={15} />
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  )
}