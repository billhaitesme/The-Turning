import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import SystemBadge from "../instruments/SystemBadge";

export default function IdentityPanel({ accent, data }) {
  return (
    <PanelShell title="Identity" accent={accent} lamp={<StatusLamp label="Identity" state={data.state} />} activityAt={data.activity_at}>
      <div className="badge-grid">
        <SystemBadge label="User" value={data.user || "Unknown"} />
        <SystemBadge label="Project" value={data.project || "Unspecified"} />
        <SystemBadge label="Session" value={data.session || "None"} />
        <SystemBadge label="Confidence" value={`${data.confidence ?? 0}%`} />
      </div>
    </PanelShell>
  );
}
