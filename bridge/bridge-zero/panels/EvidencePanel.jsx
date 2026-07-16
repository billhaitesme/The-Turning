import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import EvidenceStack from "../instruments/EvidenceStack";
import VerificationIndicator from "../instruments/VerificationIndicator";

export default function EvidencePanel({ accent, data }) {
  return (
    <PanelShell title="Evidence" accent={accent} lamp={<StatusLamp label="Evidence" state={data.state} />} activityAt={data.activity_at}>
      <EvidenceStack counts={data.counts || {}} />
      <div className="verification-grid">
        {(data.indicators || []).map((item) => (
          <VerificationIndicator key={item.label} label={item.label} state={item.state} />
        ))}
      </div>
    </PanelShell>
  );
}
