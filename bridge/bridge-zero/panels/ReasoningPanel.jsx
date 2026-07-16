import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import CircularGauge from "../instruments/CircularGauge";

export default function ReasoningPanel({ accent, data }) {
  return (
    <PanelShell title="Reasoning" accent={accent} lamp={<StatusLamp label="Reasoning" state={data.state} />}>
      <CircularGauge label="Inference Confidence" value={data.confidence || 0} color={accent} />
      <ul className="instrument-list">
        {(data.inferences || []).map((item) => <li key={item}>{item}</li>)}
      </ul>
      <div className="muted">Assumptions: {(data.assumptions || []).join(", ") || "none"}</div>
    </PanelShell>
  );
}
