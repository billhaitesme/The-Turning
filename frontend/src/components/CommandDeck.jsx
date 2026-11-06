// The Command Registry widget (XIII-A): renders the registry it is given, never defines it
// (ADR 0015). Direct commands form the QUICK REQUEST rail — one press, instant read. Gated
// commands initiate into IX-C and visibly wait for the mobile biometric. Forbidden commands are
// shown dimmed so the boundary stays visible. Categories come from the registry itself.
import { useEffect, useRef, useState } from "react";
import { fmtTime } from "./displays.jsx";

const API_BASE = "http://127.0.0.1:8001";

function statusTone(status) {
  if (status === "executed") return "green";
  if (status === "awaiting_approval") return "violet";
  if (status === "denied" || status === "forbidden" || status === "refused" || status === "failed") return "red";
  if (status === "expired") return "amber";
  return "steel";
}

export default function CommandDeck({ playCue = () => {} }) {
  const [registry, setRegistry] = useState({ commands: [], execution_enabled: true });
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState({});
  const [flash, setFlash] = useState({});
  const [params, setParams] = useState({});
  const [error, setError] = useState("");
  const [breaker, setBreaker] = useState({ on: false, changed_at: null });
  const [fetchLog, setFetchLog] = useState([]);
  const [capRequests, setCapRequests] = useState([]);
  const [capNeed, setCapNeed] = useState("");
  const [capWhy, setCapWhy] = useState("");
  const [capNote, setCapNote] = useState("");
  const [faces, setFaces] = useState({ people: [], engine_ready: false });
  const [faceName, setFaceName] = useState("");
  const [faceNote, setFaceNote] = useState("");
  const faceFileRef = useRef(null);
  const aliveRef = useRef(true);

  async function refreshHistory() {
    try {
      const res = await fetch(`${API_BASE}/system/commands/history?limit=8`);
      if (!res.ok) return;
      const data = await res.json();
      if (aliveRef.current) setHistory(data.history || []);
    } catch { /* polling failure shows via main sync chip */ }
  }

  async function refreshSenses() {
    try {
      const [b, f, t, fc] = await Promise.all([
        fetch(`${API_BASE}/system/breaker`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/system/fetch-log?limit=6`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/system/toolwright`).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/system/faces`).then((r) => (r.ok ? r.json() : null)),
      ]);
      if (!aliveRef.current) return;
      if (b) setBreaker(b);
      if (f) setFetchLog(f.entries || []);
      if (t) setCapRequests(t.requests || []);
      if (fc) setFaces(fc);
    } catch { /* same */ }
  }

  async function fileCapability() {
    if (!capNeed.trim()) return;
    playCue("navigation");
    try {
      const res = await fetch(`${API_BASE}/system/toolwright/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ need: capNeed.trim(), why: capWhy.trim() }),
      });
      if (res.ok) {
        setCapNeed("");
        setCapWhy("");
        setCapNote("Filed — press PREPARE to find, quarantine, and verify a candidate.");
        refreshSenses();
      }
    } catch { /* next poll surfaces it */ }
  }

  async function capAction(id, action) {
    playCue("navigation");
    try {
      const res = await fetch(`${API_BASE}/system/toolwright/requests/${id}/${action}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setCapNote(String(data?.detail || `HTTP ${res.status}`));
        playCue("alarm-amber");
      } else {
        setCapNote(String(data?.note || `${action} done`));
        playCue(data?.request?.status === "inducted" ? "completion" : "verified");
        if (data?.request?.status === "inducted") {
          // the registry just grew a command — re-render it
          fetch(`${API_BASE}/system/commands`).then((r) => (r.ok ? r.json() : null))
            .then((d) => { if (d && aliveRef.current) setRegistry(d); });
        }
      }
      refreshSenses();
    } catch { /* next poll */ }
  }

  async function flipBreaker() {
    playCue("navigation");
    try {
      const res = await fetch(`${API_BASE}/system/breaker`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ on: !breaker.on, changed_by: "desktop-console" }),
      });
      if (res.ok) {
        setBreaker(await res.json());
        playCue(breaker.on ? "ack" : "verified");
      }
    } catch { /* surfaces on next poll */ }
  }

  useEffect(() => {
    aliveRef.current = true;
    fetch(`${API_BASE}/system/commands`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (aliveRef.current) setRegistry(data);
      })
      .catch((err) => setError(String(err.message || err)));
    refreshHistory();
    refreshSenses();
    const timer = setInterval(() => {
      refreshHistory();
      refreshSenses();
    }, 8000);
    return () => {
      aliveRef.current = false;
      clearInterval(timer);
    };
  }, []);

  async function initiate(command) {
    const name = command.name;
    setBusy((prev) => ({ ...prev, [name]: true }));
    playCue("navigation");
    try {
      const args = {};
      const textParam = (command.parameters || []).find(
        (p) => (p.type === "text" || !p.type) && (p.required || p.name === "prompt")
      );
      const value = params[name];
      if (textParam && value) {
        args[textParam.name] = value;
      }
      const res = await fetch(`${API_BASE}/system/commands/${name}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arguments: args }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
      const entry = data.command;
      setFlash((prev) => ({ ...prev, [name]: { status: entry.status, at: Date.now() } }));
      playCue(entry.status === "executed" ? "verified" : "ack");
    } catch (err) {
      setFlash((prev) => ({ ...prev, [name]: { status: "failed", detail: String(err.message || err), at: Date.now() } }));
      playCue("alarm-amber");
    } finally {
      setBusy((prev) => ({ ...prev, [name]: false }));
      refreshHistory();
    }
  }

  const commands = registry.commands || [];
  const needsInput = (c) => (c.parameters || []).some((p) => p.required && (p.type === "text" || !p.type));
  const quick = commands.filter((c) => c.gate === "direct" && !needsInput(c));
  const quickWithInput = commands.filter((c) => c.gate === "direct" && needsInput(c));
  const gated = commands.filter((c) => c.gate === "approval");
  const forbidden = commands.filter((c) => c.gate === "forbidden");
  const categories = [...new Set(gated.map((c) => c.category || "uncategorized"))];

  return (
    <div className="command-deck">
      {error ? <div className="command-deck-error">REGISTRY UNREACHABLE // {error}</div> : null}

      <div className="command-deck-section senses-section">
        <small className="command-deck-label">THE SENSES // NETWORK BREAKER (XIII-B)</small>
        <div className="breaker-row">
          <button
            type="button"
            className={`breaker-switch ${breaker.on ? "is-on" : "is-off"}`}
            onClick={flipBreaker}
            title="The operator's standing switch for internet reads — flips are recorded"
          >
            <span className="breaker-lever" />
            <strong>{breaker.on ? "BREAKER ON — SENSES LIVE" : "BREAKER OFF — SENSES DARK"}</strong>
          </button>
          <small>{breaker.changed_at ? `last flip ${fmtTime(breaker.changed_at)}` : "never flipped"}</small>
        </div>
        <div className="fetch-log">
          {fetchLog.length ? fetchLog.map((entry, i) => (
            <div key={i} className={`fetch-log-row ${entry.ok ? "ok" : "err"}`}>
              <span>{fmtTime(entry.at)}</span>
              <strong>{entry.kind.toUpperCase()}</strong>
              <span className="fetch-target">{entry.target}</span>
              <span>{entry.detail || (entry.ok ? "OK" : "FAIL")}</span>
            </div>
          )) : <div className="empty">NO NETWORK READS LOGGED.</div>}
        </div>
      </div>

      <div className="command-deck-section">
        <small className="command-deck-label">QUICK REQUEST // DIRECT READS</small>
        <div className="quick-rail">
          {quick.map((command) => {
            const f = flash[command.name];
            return (
              <button
                key={command.name}
                type="button"
                className={`quick-chip cat-${command.category} ${busy[command.name] ? "is-busy" : ""} ${f ? `flash-${statusTone(f.status)}` : ""}`}
                title={command.description}
                disabled={Boolean(busy[command.name])}
                onClick={() => initiate(command)}
              >
                <span className="quick-cat">{String(command.category || "").toUpperCase()}</span>
                <strong>{command.title}</strong>
                <span className="quick-state">{busy[command.name] ? "RUNNING…" : f ? String(f.status).toUpperCase() : "READY"}</span>
              </button>
            );
          })}
        </div>
        {quickWithInput.length ? (
          <div className="gated-list" style={{ marginTop: "8px" }}>
            {quickWithInput.map((command) => {
              const f = flash[command.name];
              const textParam = (command.parameters || []).find((p) => p.required && (p.type === "text" || !p.type));
              return (
                <div key={command.name} className={`gated-row direct-row ${f ? `flash-${statusTone(f.status)}` : ""}`}>
                  <div className="gated-copy">
                    <strong>{command.title} <em className="row-cat">{String(command.category || "").toUpperCase()}</em></strong>
                    <span>{f?.detail || (f ? String(f.status).toUpperCase() : command.description)}</span>
                  </div>
                  <input
                    value={params[command.name] ?? ""}
                    placeholder={(textParam?.label || textParam?.name || "VALUE").toUpperCase() + "…"}
                    onChange={(e) => setParams((prev) => ({ ...prev, [command.name]: e.target.value }))}
                    onKeyDown={(e) => { if (e.key === "Enter" && !busy[command.name]) initiate(command); }}
                  />
                  <button type="button" disabled={Boolean(busy[command.name])} onClick={() => initiate(command)}>
                    {busy[command.name] ? "…" : "RUN"}
                  </button>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      {categories.map((category) => (
        <div key={category} className="command-deck-section">
          <small className="command-deck-label">{category.toUpperCase()} // BIOMETRIC-GATED</small>
          <div className="gated-list">
            {gated.filter((c) => (c.category || "uncategorized") === category).map((command) => {
              const f = flash[command.name];
              const hasPrompt = (command.parameters || []).some((p) => p.name === "prompt");
              return (
                <div key={command.name} className={`gated-row ${f ? `flash-${statusTone(f.status)}` : ""}`}>
                  <div className="gated-copy">
                    <strong>{command.title}</strong>
                    <span>{f?.status === "awaiting_approval" ? "AWAITING BIOMETRIC ON MOBILE" : f?.detail || command.description}</span>
                  </div>
                  {hasPrompt ? (
                    <input
                      value={params[command.name] ?? ""}
                      placeholder="PROMPT…"
                      onChange={(e) => setParams((prev) => ({ ...prev, [command.name]: e.target.value }))}
                    />
                  ) : null}
                  <button type="button" disabled={Boolean(busy[command.name])} onClick={() => initiate(command)}>
                    {busy[command.name] ? "…" : "INITIATE"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {forbidden.length ? (
        <div className="command-deck-section">
          <small className="command-deck-label">FORBIDDEN // VISIBLE BOUNDARY</small>
          <div className="forbidden-list">
            {forbidden.map((command) => (
              <div key={command.name} className="forbidden-row" title={command.description}>
                <strong>{command.title}</strong>
                <span>NEVER EXECUTES</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="command-deck-section">
        <small className="command-deck-label">
          THE GALLERY // ENROLLED FACES {faces.engine_ready ? "" : "(ENGINE AWAITING MODELS)"}
        </small>
        <div className="cap-file-row">
          <input value={faceName} placeholder="NAME…" onChange={(e) => setFaceName(e.target.value)} />
          <button type="button" disabled={!faceName.trim()}
                  onClick={() => faceFileRef.current?.click()}>ENROLL FROM PHOTO</button>
          <input ref={faceFileRef} type="file" accept="image/*" style={{ display: "none" }}
                 onChange={(e) => {
                   const file = e.target.files?.[0];
                   e.target.value = "";
                   if (!file) return;
                   const reader = new FileReader();
                   reader.onload = async () => {
                     playCue("navigation");
                     try {
                       const res = await fetch(`${API_BASE}/system/faces/enroll`, {
                         method: "POST",
                         headers: { "Content-Type": "application/json" },
                         body: JSON.stringify({ name: faceName.trim(), image: reader.result }),
                       });
                       const data = await res.json();
                       if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
                       setFaceNote(`Enrolled ${data.person.name} (${data.person.samples} sample(s)).`);
                       setFaceName("");
                       playCue("verified");
                       refreshSenses();
                     } catch (err) {
                       setFaceNote(String(err.message || err));
                       playCue("alarm-amber");
                     }
                   };
                   reader.readAsDataURL(file);
                 }} />
        </div>
        {faceNote ? <div className="cap-note">{faceNote}</div> : null}
        <div className="cap-list">
          {faces.people.map((p) => (
            <div key={p.person_id} className="cap-row status-inducted">
              <div className="cap-copy">
                <strong>{p.name}</strong>
                <span>{p.samples} SAMPLE(S) // {p.person_id}</span>
              </div>
              <div className="cap-actions">
                <button type="button" className="cap-deny" onClick={async () => {
                  await fetch(`${API_BASE}/system/faces/${p.person_id}`, { method: "DELETE" });
                  refreshSenses();
                }}>REMOVE</button>
              </div>
            </div>
          ))}
          {!faces.people.length ? <div className="empty">NO ONE ENROLLED — STRANGERS STAY UNKNOWN.</div> : null}
        </div>
      </div>

      <div className="command-deck-section">
        <small className="command-deck-label">THE TOOLWRIGHT // CAPABILITY REQUESTS (XIII-D)</small>
        <div className="cap-file-row">
          <input value={capNeed} placeholder="WHAT CAPABILITY IS NEEDED…"
                 onChange={(e) => setCapNeed(e.target.value)} />
          <input value={capWhy} placeholder="WHY…" onChange={(e) => setCapWhy(e.target.value)} />
          <button type="button" onClick={fileCapability}>FILE</button>
        </div>
        {capNote ? <div className="cap-note">{capNote}</div> : null}
        <div className="cap-list">
          {capRequests.slice(0, 6).map((req) => (
            <div key={req.request_id} className={`cap-row status-${req.status}`}>
              <div className="cap-copy">
                <strong>{req.need}</strong>
                <span>
                  {String(req.status).toUpperCase().replace("_", " ")}
                  {req.candidate?.name ? ` // ${req.candidate.name}` : ""}
                  {req.requested_by ? ` // by ${req.requested_by}` : ""}
                </span>
              </div>
              <div className="cap-actions">
                {req.status === "proposed" || req.status === "failed" ? (
                  <button type="button" onClick={() => capAction(req.request_id, "prepare")}>PREPARE</button>
                ) : null}
                {req.status === "verified" || req.status === "awaiting_induction" ? (
                  <button type="button" onClick={() => capAction(req.request_id, "induct")}>
                    {req.status === "verified" ? "INDUCT" : "COMPLETE"}
                  </button>
                ) : null}
                {!["inducted", "denied", "superseded"].includes(req.status) ? (
                  <button type="button" className="cap-deny" onClick={() => capAction(req.request_id, "deny")}>DENY</button>
                ) : null}
              </div>
            </div>
          ))}
          {!capRequests.length ? <div className="empty">NO CAPABILITY REQUESTS.</div> : null}
        </div>
      </div>

      <div className="command-deck-section">
        <small className="command-deck-label">RECENT COMMANDS</small>
        <div className="command-history">
          {history.length ? history.map((entry) => (
            <div key={entry.command_id} className={`command-history-row tone-${statusTone(entry.status)}`}>
              <span>{fmtTime(entry.requested_at)}</span>
              <strong>{entry.name}</strong>
              <span>{String(entry.status || "--").toUpperCase()}</span>
              <span className="command-channel">{String(entry.channel || "--").toUpperCase()}</span>
            </div>
          )) : <div className="empty">NO COMMAND HISTORY.</div>}
        </div>
      </div>
    </div>
  );
}
