export default function SignalBus({ subsystems, activeSubsystem }) {
  return (
    <div className="signal-bus" aria-label="Cognitive bus">
      {subsystems.map((name) => {
        const active = activeSubsystem === name;
        return (
          <div key={name} className={`signal-node ${active ? "active" : ""}`}>
            <div className="signal-dot" />
            <span>{name}</span>
          </div>
        );
      })}
    </div>
  );
}
