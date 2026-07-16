export default function Timeline({ steps = [], selected, onSelect }) {
  return (
    <div className="instrument timeline">
      <div className="engraved-label">System Chronicle</div>
      <div className="timeline-list">
        {steps.map((step) => (
          <button
            key={step}
            className={`timeline-step ${selected === step ? "selected" : ""}`}
            onClick={() => onSelect(step)}
            type="button"
          >
            {step}
          </button>
        ))}
      </div>
    </div>
  );
}
