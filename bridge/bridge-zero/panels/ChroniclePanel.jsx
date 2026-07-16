import AurebeshTranslator from "../components/AurebeshTranslator";
import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";
import Timeline from "../instruments/Timeline";

export default function ChroniclePanel({ accent, data, steps, selected, onSelect }) {
  return (
    <PanelShell title="Chronicle" accent={accent} lamp={<StatusLamp label="Chronicle" state={data.state} />}>
      <Timeline steps={steps} selected={selected} onSelect={onSelect} />
      {data.record ? (
        <div className="chronicle-detail">
          <div className="engraved-label">{data.record.epoch}</div>
          <div className="muted">{data.record.title}</div>
          <div className="chronicle-block">
            <strong>ADRs</strong>
            <div>{data.record.adrs.join(", ")}</div>
          </div>
          <div className="chronicle-block">
            <strong>Architecture Changes</strong>
            <ul className="instrument-list">
              {data.record.architectureChanges.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </div>
      ) : null}
      <AurebeshTranslator />
    </PanelShell>
  );
}
