export default function ProgressRing({ label, value = 0 }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="instrument progress-ring">
      <div className="engraved-label">{label}</div>
      <div className="progress-ring-meter">
        <div className="progress-ring-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="muted">{pct.toFixed(0)}%</div>
    </div>
  );
}
