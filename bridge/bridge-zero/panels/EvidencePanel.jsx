import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import EvidenceStack from "../instruments/EvidenceStack";
import VerificationIndicator from "../instruments/VerificationIndicator";
import ProgressRing from "../instruments/ProgressRing";

export default function EvidencePanel({ accent, data }) {
  const timeline = data.timeline || [];

  return (
    <PanelShell title="Evidence" accent={accent} lamp={<StatusLamp label="Evidence" state={data.state} />} activityAt={data.activity_at}>
      <EvidenceStack counts={data.counts || {}} />
      <div className="evidence-confidence-grid">
        <ProgressRing label="Verified Ratio" value={data.confidence?.verifiedRatio || 0} />
        <ProgressRing label="Result Success" value={data.confidence?.successRatio || 0} />
      </div>
      <div className="verification-grid">
        {(data.indicators || []).map((item) => (
          <VerificationIndicator key={item.label} label={item.label} state={item.state} />
        ))}
      </div>
      <div className="instrument evidence-meta-grid">
        <div className="engraved-label">Freshness + Expiry</div>
        <div className="muted">Observed At: {data.freshness?.observedAt || "unknown"}</div>
        <div className={`evidence-freshness ${data.freshness?.state || "unknown"}`}>
          Freshness: {String(data.freshness?.state || "unknown").toUpperCase()}
          {typeof data.freshness?.ageSeconds === "number" ? ` (${data.freshness.ageSeconds}s)` : ""}
        </div>
        <ul className="instrument-list">
          {(data.expiryMarkers || []).length === 0 ? <li>No pending approvals nearing expiry.</li> : null}
          {(data.expiryMarkers || []).map((item) => (
            <li key={item.requestId}>
              {item.toolName} | {item.requestId} | {item.expired ? "EXPIRED" : `T-${item.remainingSeconds}s`} | {item.expiresAt || "unknown"}
            </li>
          ))}
        </ul>
      </div>
      <div className="instrument evidence-meta-grid">
        <div className="engraved-label">Dependency Invalidation</div>
        <ul className="instrument-list">
          {(data.invalidations || []).length === 0 ? <li>No invalidated evidence dependencies.</li> : null}
          {(data.invalidations || []).map((item) => (
            <li key={`${item.requestId}-${item.at}`}>
              {item.toolName} | {item.requestId} | {String(item.reason || "unknown").toUpperCase()} | {item.at}
            </li>
          ))}
        </ul>
      </div>
      <div className="instrument evidence-meta-grid">
        <div className="engraved-label">Provenance Badges</div>
        <div className="evidence-badge-row">
          {(data.provenance || []).length === 0 ? <span className="muted">No verified provenance records yet.</span> : null}
          {(data.provenance || []).map((item) => (
            <span className="evidence-badge" key={item.candidateId} title={`${item.adapter} | ${item.requestId}`}>
              {item.toolName} @ {item.checkedEndpoint}
            </span>
          ))}
        </div>
      </div>
      <div className="instrument evidence-meta-grid">
        <div className="engraved-label">Compact Evidence Timeline</div>
        <ul className="instrument-list">
          {timeline.length === 0 ? <li>No evidence timeline entries yet.</li> : null}
          {timeline.map((item, idx) => (
            <li key={`${item.type}-${item.at}-${idx}`}>
              {item.at} | {item.type.toUpperCase()} | {item.detail}
            </li>
          ))}
        </ul>
      </div>
    </PanelShell>
  );
}
