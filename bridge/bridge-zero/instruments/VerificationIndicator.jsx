export default function VerificationIndicator({ label, state }) {
  return (
    <div className="instrument verification-indicator">
      <span className="verification-label">{label}</span>
      <span className={`verification-state ${state}`}>{String(state || "unknown").toUpperCase()}</span>
    </div>
  );
}
