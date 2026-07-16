export default function CircularGauge({ label, value = 0, max = 100, color = "#7cb8d9" }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const dash = `${pct} ${100 - pct}`;
  return (
    <div className="instrument gauge-wrap">
      <div className="engraved-label">{label}</div>
      <svg viewBox="0 0 36 36" className="gauge-svg" role="img" aria-label={`${label} ${pct.toFixed(0)} percent`}>
        <path className="gauge-track" d="M18 2.5a15.5 15.5 0 1 1 0 31a15.5 15.5 0 1 1 0-31" />
        <path className="gauge-fill" stroke={color} strokeDasharray={dash} d="M18 2.5a15.5 15.5 0 1 1 0 31a15.5 15.5 0 1 1 0-31" />
        <text x="18" y="20.7" className="gauge-value" textAnchor="middle">{pct.toFixed(0)}%</text>
      </svg>
    </div>
  );
}
