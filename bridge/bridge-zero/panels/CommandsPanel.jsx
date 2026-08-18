import { useState } from "react";
import PanelShell from "../components/PanelShell";
import ConsoleButton from "../instruments/ConsoleButton";
import StatusLamp from "../instruments/StatusLamp";

// IX-D (ADR 0015): the operator INITIATES bounded runtime commands from the desktop. The list is the
// runtime's command registry, rendered as-is — the console never defines it. Direct commands run now;
// approval-gated commands create an IX-C approval that completes ONLY on a mobile biometric (this
// surface cannot self-approve); forbidden commands are shown so the boundary is visible, never runnable.

const GATE_LABEL = {
  direct: "DIRECT — executes now",
  approval: "APPROVAL — biometric on your phone",
  forbidden: "FORBIDDEN",
};

const GATE_CLASS = {
  direct: "gate-direct",
  approval: "gate-approval",
  forbidden: "gate-forbidden",
};

function statusClass(status) {
  if (status === "executed") return "cmd-status-ok";
  if (status === "awaiting_approval" || status === "executing") return "cmd-status-wait";
  return "cmd-status-bad";
}

function shortStamp(iso) {
  if (!iso) return "";
  return String(iso).slice(0, 16).replace("T", " ");
}

export default function CommandsPanel({ accent, data, onInitiate, onDismissNotice }) {
  const registry = Array.isArray(data.registry) ? data.registry : [];
  const history = Array.isArray(data.history) ? data.history : [];
  const canInitiate = typeof onInitiate === "function" && data.state !== "OFFLINE";

  return (
    <PanelShell
      title="Commands"
      accent={accent}
      lamp={<StatusLamp label="Commands" state={data.state} />}
      activityAt={data.activity_at}
    >
      {data.notice ? (
        <div className="cmd-notice" role="status">
          <span>{data.notice}</span>
          {typeof onDismissNotice === "function" ? (
            <button type="button" className="cmd-notice-dismiss" onClick={onDismissNotice} aria-label="Dismiss notice">
              ×
            </button>
          ) : null}
        </div>
      ) : null}

      {!data.executionEnabled ? (
        <div className="cmd-policy-warning">Command execution is disabled by runtime policy — requests are recorded but will not run.</div>
      ) : null}

      <div className="cmd-list">
        {registry.length === 0 ? <div className="cmd-empty">No commands available.</div> : null}
        {registry.map((command) => {
          const gate = command.gate || "forbidden";
          const gateClass = GATE_CLASS[gate] || GATE_CLASS.forbidden;
          const isForbidden = gate === "forbidden";
          return (
            <div key={command.name} className={`cmd-card ${gateClass}`}>
              <div className="cmd-card-head">
                <span className="cmd-title">{String(command.title || command.name).toUpperCase()}</span>
                <span className={`cmd-risk ${gateClass}`}>{String(command.risk || "").toUpperCase()}</span>
              </div>
              {command.description ? <div className="cmd-desc">{command.description}</div> : null}
              <div className={`cmd-gate ${gateClass}`}>{GATE_LABEL[gate] || GATE_LABEL.forbidden}</div>
              <CommandControls
                command={command}
                isForbidden={isForbidden}
                gate={gate}
                canInitiate={canInitiate}
                onInitiate={onInitiate}
              />
            </div>
          );
        })}
      </div>

      <div className="cmd-history-title">HISTORY</div>
      <div className="cmd-history">
        {history.length === 0 ? <div className="cmd-empty">Nothing commanded yet.</div> : null}
        {history.slice(0, 8).map((entry) => (
          <div key={entry.command_id} className="cmd-history-row">
            <div className="cmd-history-main">
              <span className="cmd-history-name">{entry.name}</span>
              <span className="cmd-history-meta">
                {[entry.channel, shortStamp(entry.requested_at)].filter(Boolean).join("  ")}
              </span>
            </div>
            <span className={`cmd-history-status ${statusClass(entry.status)}`}>{String(entry.status || "?").toUpperCase()}</span>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}

// Renders a command's parameter form (prompt / cfg / denoise / …) from its registry spec, then
// initiates with the collected values. Commands without a spec keep the plain RUN/REQUEST button.
function CommandControls({ command, isForbidden, gate, canInitiate, onInitiate }) {
  const params = Array.isArray(command.parameters) ? command.parameters : [];
  const initial = {};
  for (const p of params) initial[p.name] = p.default !== undefined ? String(p.default) : "";
  const [values, setValues] = useState(initial);
  const label = isForbidden ? "FORBIDDEN" : gate === "approval" ? "REQUEST" : "RUN";

  const set = (name, v) => setValues((prev) => ({ ...prev, [name]: v }));

  const submit = () => {
    if (params.length === 0) {
      onInitiate(command.name);
      return;
    }
    const args = {};
    for (const p of params) {
      const raw = values[p.name];
      if (raw === "" || raw === undefined || raw === null) continue; // omit blanks (defaults/random apply)
      if (p.type === "number") args[p.name] = Number(raw);
      else if (p.type === "integer") args[p.name] = parseInt(raw, 10);
      else args[p.name] = raw;
    }
    onInitiate(command.name, args);
  };

  const promptMissing = params.some((p) => p.required && p.type === "text" && !String(values[p.name] || "").trim());

  return (
    <>
      {params.map((p) => (
        <label key={p.name} className="cmd-field">
          <span className="cmd-field-label">{p.label || p.name}</span>
          {p.type === "text" ? (
            <textarea
              className="cmd-field-input cmd-field-textarea"
              rows={p.name === "prompt" ? 2 : 1}
              value={values[p.name] ?? ""}
              onChange={(e) => set(p.name, e.target.value)}
            />
          ) : (
            <input
              className="cmd-field-input"
              type="number"
              min={p.min}
              max={p.max}
              step={p.step ?? (p.type === "integer" ? 1 : "any")}
              value={values[p.name] ?? ""}
              onChange={(e) => set(p.name, e.target.value)}
            />
          )}
        </label>
      ))}
      <ConsoleButton
        label={label}
        disabled={isForbidden || !canInitiate || promptMissing}
        onClick={submit}
      />
    </>
  );
}
