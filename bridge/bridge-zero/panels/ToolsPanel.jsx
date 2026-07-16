import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";

export default function ToolsPanel({ accent, data, connection }) {
  const timeline = data.timeline || [];

  return (
    <PanelShell title="Tools" accent={accent} lamp={<StatusLamp label="Tools" state={data.state} />} activityAt={data.activity_at}>
      <div className="planning-headline">Connection: {connection?.state || "INITIALIZING"}</div>
      <div className="planning-headline">Last Successful Poll: {connection?.lastSuccessfulPollAt || "none"}</div>
      <div className="planning-headline">Poll Interval: {connection?.pollIntervalMs || 0} ms</div>
      <div className="planning-headline">Stale Data: {connection?.stale ? "YES" : "NO"}</div>
      <div className="planning-headline">Execution Enabled: {String(data.executionEnabled)}</div>
      <div className="tools-table">
        <div className="tools-row tools-head">
          <span>Name</span>
          <span>Enabled</span>
          <span>Risk</span>
          <span>Approval</span>
        </div>
        {(data.tools || []).map((tool) => (
          <div className="tools-row" key={tool.name}>
            <span>{tool.name}</span>
            <span>{String(tool.enabled)}</span>
            <span>{tool.risk_level}</span>
            <span>{String(tool.requires_approval)}</span>
          </div>
        ))}
      </div>
      <div className="engraved-label">Tool Execution Timeline</div>
      <ul className="instrument-list">
        {timeline.length === 0 ? <li>No tool timeline entries yet.</li> : null}
        {timeline.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <div className="sub-note">Execution remains disabled by default.</div>
    </PanelShell>
  );
}
