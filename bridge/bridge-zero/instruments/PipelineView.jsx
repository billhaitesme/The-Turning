export default function PipelineView({ stages }) {
  return (
    <div className="instrument pipeline-view">
      <div className="engraved-label">Pipeline</div>
      <div className="pipeline-column">
        {stages.map((stage, idx) => (
          <div className="pipeline-stage" key={stage.name}>
            <div className={`pipeline-indicator ${stage.active ? "active" : ""}`} />
            <span>{stage.name}</span>
            {idx < stages.length - 1 ? <div className="pipeline-arrow">v</div> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
