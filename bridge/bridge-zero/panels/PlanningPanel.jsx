import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import DependencyGraph from "../instruments/DependencyGraph";

export default function PlanningPanel({ accent, data }) {
  return (
    <PanelShell title="Planning" accent={accent} lamp={<StatusLamp label="Planning" state={data.state} />} activityAt={data.activity_at}>
      <div className="planning-headline">Active Goal: {data.activeGoal || "none"}</div>
      <div className="planning-headline">Next Action: {data.nextAction || "none"}</div>
      <DependencyGraph nodes={data.steps || []} />
    </PanelShell>
  );
}
