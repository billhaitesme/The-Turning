export default function SystemBadge({ label, value }) {
  return (
    <div className="instrument system-badge">
      <span className="system-badge-label">{label}</span>
      <span className="system-badge-value">{value}</span>
    </div>
  );
}
