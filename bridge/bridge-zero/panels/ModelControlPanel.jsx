import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import SystemBadge from "../instruments/SystemBadge";

function enabledLabel(value, enabled, disabled) {
  return value ? enabled : disabled;
}

export default function ModelControlPanel({ accent, data }) {
  return (
    <PanelShell
      title="Model Control"
      accent={accent}
      lamp={<StatusLamp label="Model Lock" state={data.state} />}
      activityAt={data.activity_at}
    >
      <div className="model-control-active">
        <span>ACTIVE MODEL</span>
        <strong>{data.activeModel || "Unknown"}</strong>
      </div>
      <div className="badge-grid">
        <SystemBadge label="Model Lock" value={enabledLabel(data.modelLock, "ENGAGED", "DISENGAGED")} />
        <SystemBadge label="Topic Routing" value={enabledLabel(data.topicRouting, "ENABLED", "DISABLED")} />
        <SystemBadge label="Secondary Rewrite" value={enabledLabel(data.secondaryRewrite, "ENABLED", "DISABLED")} />
        <SystemBadge label="Auto Fallback" value={enabledLabel(data.automaticFallback, "ENABLED", "DISABLED")} />
        <SystemBadge label="User Selected" value={data.userSelected ? "YES" : "NO"} />
      </div>
    </PanelShell>
  );
}
