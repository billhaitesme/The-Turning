import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import PipelineView from "../instruments/PipelineView";

export default function DeliberationPanel({ accent, data }) {
  const stages = [
    { name: "Candidates", active: true },
    { name: "Compare", active: true },
    { name: "Recommend", active: true },
    { name: "Approve", active: String(data.approvalState || "").toLowerCase() === "approved" },
  ];

  return (
    <PanelShell title="Deliberation" accent={accent} lamp={<StatusLamp label="Deliberation" state={data.state} />}>
      <div className="planning-headline">Recommendation: {data.recommendation || "none"}</div>
      <div className="planning-headline">Approval: {data.approvalState || "pending"}</div>
      <ul className="instrument-list">
        {(data.alternatives || []).map((item) => <li key={item}>{item}</li>)}
      </ul>
      <PipelineView stages={stages} />
    </PanelShell>
  );
}
