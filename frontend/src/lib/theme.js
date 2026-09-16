// Theme (light/dark) with persistence. Defaults to the OS preference on first
// load; a sun/moon toggle overrides it. The resolved theme is always written
// to <html data-theme="…"> so index.css only needs the [data-theme=dark] rule.
import { useState } from 'react'

const KEY = 'ngo-theme'

function systemPref() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function getTheme() {
  const saved = (typeof localStorage !== 'undefined' && localStorage.getItem(KEY)) || ''
  const t = saved === 'dark' || saved === 'light' ? saved : systemPref()
  document.documentElement.setAttribute('data-theme', t)
  return t
}

export function toggleTheme() {
  const t = getTheme() === 'dark' ? 'light' : 'dark'
  localStorage.setItem(KEY, t)
  document.documentElement.setAttribute('data-theme', t)
  return t
}

export function useTheme() {
  const [theme, setTheme] = useState(getTheme)
  const apply = () => setTheme(toggleTheme())
  return [theme, apply]
}