// Avatar — initials circle with a deterministic warm tone from the name.
const TONES = ['teal', 'amber', 'blue', 'rose', 'violet', 'green']

function toneFor(name) {
  const s = String(name || '?')
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + (s.codePointAt(i) || 0)) >>> 0
  return TONES[h % TONES.length]
}

export default function Avatar({ name, size = 36, className = '' }) {
  const initials =
    String(name || '')
      .trim()
      .split(/\s+/)
      .map((w) => w[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || '?'
  return (
    <span
      className={`avatar avatar-${toneFor(name)} ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}