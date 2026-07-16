import PanelShell from "../components/PanelShell";
import StatusLamp from "../instruments/StatusLamp";

export default function ConversationPanel({ accent, data }) {
  const items = data.messages || [];
  const lines = items.slice(-6);

  return (
    <PanelShell title="Conversation" accent={accent} lamp={<StatusLamp label="Conversation" state={data.state} />}>
      <div className="conversation-lines">
        {lines.length === 0 ? <div className="muted">No dialogue loaded.</div> : null}
        {lines.map((entry, idx) => (
          <div key={`${entry.role}-${idx}`} className="conversation-entry">
            <span className="conversation-role">{entry.role}</span>
            <span className="conversation-text">{entry.content}</span>
          </div>
        ))}
      </div>
      <div className="sub-note">Reasoning summaries and planning output stream through this channel.</div>
    </PanelShell>
  );
}
