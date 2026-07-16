import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";

export default function ToolsPanel({ accent, data }) {
  return (
    <PanelShell title="Tools" accent={accent} lamp={<StatusLamp label="Tools" state={data.state} />}>
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
      <div className="sub-note">Execution remains disabled by default.</div>
    </PanelShell>
  );
}
