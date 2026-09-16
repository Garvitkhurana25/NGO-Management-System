export default function ProgressBar({ percent, color }) {
  const p = Math.max(0, Math.min(100, Number(percent) || 0))
  return (
    <div className="progress-track">
      <div className="progress-fill" style={{ width: `${p}%`, ...(color ? { background: color } : {}) }} />
    </div>
  )
}