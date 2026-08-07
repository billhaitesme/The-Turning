export default function EvidenceStack({ counts }) {
  const rows = [
    ["declared", counts.declared || 0],
    ["configured", counts.configured || 0],
    ["observed", counts.observed || 0],
    ["verified", counts.verified || 0],
    ["unknown", counts.unknown || 0],
  ];

  return (
    <div className="instrument evidence-stack">
      <div className="engraved-label">Verification Stack</div>
      {rows.map(([label, value]) => (
        <div className="evidence-row" key={label}>
          <span className="evidence-label">{label.toUpperCase()}</span>
          <div className="evidence-bar-shell">
            <div className="evidence-bar-fill" style={{ width: `${Math.min(100, value * 18)}%` }} />
          </div>
          <span className="evidence-value">{value}</span>
        </div>
      ))}
    </div>
  );
}
