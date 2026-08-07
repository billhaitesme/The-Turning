export default function DataPlate({ title, lines = [] }) {
  return (
    <div className="instrument data-plate">
      <div className="engraved-label">{title}</div>
      <div className="data-plate-lines">
        {lines.map((line) => (
          <div key={line} className="data-plate-line">{line}</div>
        ))}
      </div>
    </div>
  );
}
