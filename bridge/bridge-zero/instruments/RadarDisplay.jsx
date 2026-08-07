export default function RadarDisplay({ points = [] }) {
  return (
    <div className="instrument radar-display">
      <div className="engraved-label">Radar Display</div>
      <div className="radar-grid">
        {points.slice(0, 20).map((point, idx) => (
          <span
            key={`${point.x}-${point.y}-${idx}`}
            className="radar-point"
            style={{ left: `${point.x}%`, top: `${point.y}%` }}
            title={point.label || "signal"}
          />
        ))}
      </div>
    </div>
  );
}
