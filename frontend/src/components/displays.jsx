// Display primitives of the Bridge Zero web console — the Imperial instrument library.
// Extracted from the App monolith in the XIII-A deck refactor; behavior preserved.
import { useEffect, useRef, useState } from "react";

export function fmtTime(value) {
  if (!value) return "--";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "--";
  return d.toLocaleTimeString();
}

export function phaseLabel(name) {
  const labels = {
    none: "NO ACTIVE PHASE",
    whisper: "WHISPER",
    bridge: "BRIDGE",
    mirror: "MIRROR",
    guide: "GUIDE",
    silence: "SILENCE",
  };
  return labels[name] || String(name || "none").toUpperCase();
}

export function statusFromError(error) {
  return error ? "ERROR" : "READY";
}

export function panelPattern({ error = false, waiting = false, input = false, output = false }) {
  if (error) return "error";
  if (waiting) return "wait";
  if (output) return "output";
  if (input) return "input";
  return "idle";
}

export function cadenceBand(load) {
  const value = Math.max(0, Math.min(100, Number(load) || 0));
  if (value >= 72) return "overdrive";
  if (value >= 36) return "active";
  return "idle";
}

function cadenceFromBand(band) {
  if (band === "overdrive") return 1.95;
  if (band === "active") return 1.28;
  return 0.82;
}

function patternCadenceBoost(pattern) {
  if (pattern === "error") return 1.24;
  if (pattern === "output") return 1.15;
  if (pattern === "input") return 1.08;
  if (pattern === "wait") return 0.9;
  return 1;
}

export function tunedCadence(band, pattern) {
  const raw = cadenceFromBand(band) * patternCadenceBoost(pattern);
  return Math.max(0.65, Math.min(2.35, raw));
}

export function pushHistory(history, value) {
  const bounded = Math.max(0, Math.min(100, Number(value) || 0));
  const next = [...history, bounded];
  return next.length > 24 ? next.slice(next.length - 24) : next;
}

export function ratioPct(part, total) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.max(0, Math.min(100, (part / total) * 100));
}

export function toAurebeshGlyphText(text) {
  return String(text || "").toUpperCase().trim();
}

export function playTone(context, {
  frequency = 440,
  duration = 0.08,
  type = "sine",
  gain = 0.025,
  offset = 0,
}) {
  const osc = context.createOscillator();
  const amp = context.createGain();
  const start = context.currentTime + offset;
  const end = start + duration;
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, start);
  amp.gain.setValueAtTime(0.0001, start);
  amp.gain.exponentialRampToValueAtTime(gain, start + Math.min(0.02, duration * 0.35));
  amp.gain.exponentialRampToValueAtTime(0.0001, end);
  osc.connect(amp);
  amp.connect(context.destination);
  osc.start(start);
  osc.stop(end + 0.01);
}

export function PanelFrame({
  title,
  accent = "cyan",
  subtitle,
  size = "normal",
  serial,
  live = false,
  blink = false,
  throughput = 0,
  flow = 0,
  sparkValues = [],
  signalTone = "cyan",
  pattern = "idle",
  cadence = 1,
  band = "idle",
  collapsed = false,
  deckControls = null,
  children,
}) {
  const boundedThroughput = Math.max(0, Math.min(100, Number(throughput) || 0));
  const boundedFlow = Math.max(0, Math.min(100, Number(flow) || 0));
  const boundedCadence = Math.max(0.6, Math.min(2.4, Number(cadence) || 1));
  const warmTarget = live || pattern !== "idle";
  const [warmStage, setWarmStage] = useState(warmTarget ? 4 : 0);
  const warmTimersRef = useRef([]);
  const warmPrevRef = useRef(false);

  useEffect(() => {
    const clearWarmTimers = () => {
      warmTimersRef.current.forEach((timer) => clearTimeout(timer));
      warmTimersRef.current = [];
    };

    if (warmTarget && !warmPrevRef.current) {
      setWarmStage(0);
      const ticks = [90, 180, 300, 460];
      ticks.forEach((delay, index) => {
        const timer = setTimeout(() => setWarmStage(index + 1), delay);
        warmTimersRef.current.push(timer);
      });
    } else if (!warmTarget) {
      setWarmStage(0);
      clearWarmTimers();
    }

    warmPrevRef.current = warmTarget;

    return () => {
      clearWarmTimers();
    };
  }, [warmTarget]);

  return (
    <section
      className={`panel-frame panel-${accent} panel-${size} ${live ? "is-live" : ""} ${blink ? "is-blink" : ""} pattern-${pattern} band-${band} warm-stage-${warmStage} ${warmStage < 4 ? "is-warming" : ""} ${collapsed ? "is-collapsed" : ""}`}
      style={{ "--panel-rate": String(boundedCadence) }}
    >
      <div className="panel-chassis">
        <div className="panel-bezel">
          <div className="panel-glass">
            <div className="panel-header">
              <div className="panel-title-stack">
                <h3>{title}</h3>
                <div className="panel-title-accent aurebesh" aria-hidden="true">
                  {title.toUpperCase()}
                </div>
                {subtitle && !collapsed ? <p>{subtitle}</p> : null}
              </div>
              <div className="panel-aux">
                {serial ? <small className="panel-serial">{serial}</small> : null}
                <div className={`panel-relay-rail stage-${warmStage}`} aria-hidden="true">
                  <span className={warmStage >= 1 ? "is-on" : ""} />
                  <span className={warmStage >= 2 ? "is-on" : ""} />
                  <span className={warmStage >= 3 ? "is-on" : ""} />
                  <span className={warmStage >= 4 ? "is-on" : ""} />
                </div>
                <div className={`panel-instruments tone-${signalTone} ${blink ? "is-blink" : ""} pattern-${pattern} band-${band}`} aria-hidden="true">
                  <div className="panel-light-bank">
                    <span className={`panel-led ${live ? "is-on" : "is-off"}`} />
                    <span className={`panel-led ${boundedFlow > 8 ? "is-on" : "is-off"}`} />
                    <span className={`panel-led ${boundedThroughput > 12 ? "is-on" : "is-off"}`} />
                  </div>
                  {!collapsed ? (
                    <>
                      <div className="panel-meter-stack">
                        <div className="panel-meter-row">
                          <span>THR</span>
                          <div className="panel-meter-track">
                            <div className="panel-meter-fill" style={{ width: `${boundedThroughput}%` }} />
                          </div>
                        </div>
                        <div className="panel-meter-row">
                          <span>FLOW</span>
                          <div className="panel-meter-track">
                            <div className="panel-meter-fill flow" style={{ width: `${boundedFlow}%` }} />
                          </div>
                        </div>
                      </div>
                      <div className="panel-strip-chart" aria-hidden="true">
                        {(sparkValues.length ? sparkValues : [0, 0, 0, 0, 0, 0]).map((value, index) => (
                          <span key={`${title}-spark-${index}`} style={{ height: `${Math.max(12, value)}%` }} />
                        ))}
                      </div>
                    </>
                  ) : null}
                </div>
                {deckControls}
              </div>
            </div>
            {!collapsed ? <div className="panel-display">{children}</div> : null}
          </div>
        </div>
      </div>
    </section>
  );
}

export function StatusLamp({ status, pulse }) {
  const normalized = String(status || "OFFLINE").toLowerCase();
  return (
    <div className={`status-lamp lamp-${normalized} ${pulse ? "lamp-pulse" : ""}`}>
      <span className="dot" />
      <span>{String(status || "OFFLINE").toUpperCase()}</span>
    </div>
  );
}

export function SystemBadge({ label, value }) {
  return (
    <div className="system-badge">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}

export function DataPlate({ label, value }) {
  return (
    <div className="data-plate">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}

export function SignalBar({ value = 0 }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="signal-bar">
      <div className="signal-fill" style={{ width: `${bounded}%` }} />
    </div>
  );
}

export function SegmentMeter({ segments = 5, active = 0 }) {
  const items = Array.from({ length: segments }, (_, i) => i < active);
  return (
    <div className="segment-meter">
      {items.map((on, i) => (
        <span key={i} className={on ? "on" : "off"} />
      ))}
    </div>
  );
}

export function CircularGauge({ label, value = 0 }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="circular-gauge">
      <div
        className="ring"
        style={{
          background: `conic-gradient(var(--accent-cyan) ${bounded * 3.6}deg, #202833 0deg)`,
        }}
      >
        <div className="inner">{Math.round(bounded)}%</div>
      </div>
      <small>{label}</small>
    </div>
  );
}

export function RadarDisplay({ value = 0 }) {
  return (
    <div className="radar-display">
      <div className="sweep" style={{ transform: `rotate(${value * 3.6}deg)` }} />
    </div>
  );
}

export function ScopeTrace({ value = 0 }) {
  const points = Array.from({ length: 22 }, (_, idx) => {
    const phase = (idx / 21) * Math.PI * 2;
    const amp = 7 + (value / 100) * 12;
    const y = 20 + Math.sin(phase * 1.8) * amp;
    return `${(idx / 21) * 100},${y}`;
  }).join(" ");
  return (
    <div className="scope-trace">
      <svg viewBox="0 0 100 40" preserveAspectRatio="none">
        <polyline points={points} />
      </svg>
    </div>
  );
}

export function MeterStack({ values = [] }) {
  return (
    <div className="meter-stack">
      {values.map((item) => (
        <div key={item.label} className="meter-row">
          <span>{item.label}</span>
          <div className="meter-track">
            <div className="meter-fill" style={{ width: `${Math.max(0, Math.min(100, item.value || 0))}%` }} />
          </div>
          <strong>{Math.round(item.value || 0)}%</strong>
        </div>
      ))}
    </div>
  );
}

export function EvidenceStack({ candidates }) {
  const stats = { declared: 0, configured: 0, observed: 0, verified: 0, unknown: 0 };
  for (const c of candidates || []) {
    const key = String(c?.state_type || "observed").toLowerCase();
    if (Object.prototype.hasOwnProperty.call(stats, key)) stats[key] += 1;
    else stats.observed += 1;
  }

  return (
    <div className="evidence-stack">
      {Object.entries(stats).map(([k, v]) => (
        <DataPlate key={k} label={k.toUpperCase()} value={v} />
      ))}
    </div>
  );
}

export function AdapterTile({ adapterId, descriptor, lastResult, lastRequest }) {
  const status = lastResult?.status || lastRequest?.status || "idle";
  return (
    <div className="adapter-tile">
      <div className="tile-top">
        <strong>{adapterId}</strong>
        <span>{descriptor.name}</span>
      </div>
      <div className="tile-grid">
        <DataPlate label="STATE" value={descriptor.enabled ? "READY" : "DISABLED"} />
        <DataPlate label="RISK" value={descriptor.risk_level} />
        <DataPlate label="APPROVAL" value={descriptor.requires_approval ? "REQUIRED" : "NONE"} />
        <DataPlate label="LAST" value={String(status).toUpperCase()} />
      </div>
      <div className="tile-foot">
        <span>Duration: {lastResult?.duration_ms ? `${Number(lastResult.duration_ms).toFixed(1)} ms` : "--"}</span>
      </div>
    </div>
  );
}

export const COGNITIVE_STAGES = [
  "RECEIVING",
  "CLASSIFYING",
  "IDENTITY",
  "MEMORY",
  "REASONING",
  "PLANNING",
  "COMPOSING",
  "TRANSMITTING",
];

export function CognitiveBus({ items, pulseIndex, cognitiveStage, silenceMode }) {
  const stageIndex = Math.max(0, COGNITIVE_STAGES.indexOf(cognitiveStage));
  return (
    <section className={`cognitive-bus ${silenceMode ? "is-silence" : ""}`}>
      <div className="cognitive-pipeline">
        {COGNITIVE_STAGES.map((stage, index) => (
          <span key={stage} className={`pipeline-stage ${index < stageIndex ? "is-complete" : ""} ${index === stageIndex ? "is-active" : ""}`}>
            {stage}
          </span>
        ))}
      </div>
      <div className="cognitive-bus-track">
        {items.map((item, index) => (
          <div key={item.key} className={`bus-node tone-${item.tone} trait-${item.trait} ${index === pulseIndex ? "is-pulse" : ""}`}>
            <StatusLamp status={item.status} pulse={item.pulse || index === pulseIndex} />
            <strong>{item.label}</strong>
            <div className="bus-meter" aria-hidden="true">
              <span style={{ width: `${Math.max(4, Math.min(100, item.value || 0))}%` }} />
            </div>
            <span>LAST {fmtTime(item.lastActivity)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ChroniclePlate({ lastResult }) {
  const [arrivalPhase, setArrivalPhase] = useState("locked");

  useEffect(() => {
    if (!lastResult) return;
    setArrivalPhase("arriving");
    const typingTimer = setTimeout(() => setArrivalPhase("typing"), 220);
    const lockTimer = setTimeout(() => setArrivalPhase("locked"), 980);
    return () => {
      clearTimeout(typingTimer);
      clearTimeout(lockTimer);
    };
  }, [lastResult?.completed_at, lastResult?.started_at, lastResult?.tool_name]);

  return (
    <div className={`chronicle-plate chronicle-${arrivalPhase}`}>
      <div>SYSTEM CHRONICLE</div>
      <div>Epoch IX-A</div>
      <div>First Trusted Runtime Observation</div>
      <div>Verified: Backend Health</div>
      <div>Method: Approved Local Adapter</div>
      <div>Result: {lastResult?.output?.status_code ? `HTTP ${lastResult.output.status_code}` : "--"}</div>
      <div>Duration: {lastResult?.duration_ms ? `${Number(lastResult.duration_ms).toFixed(3)} ms` : "--"}</div>
    </div>
  );
}

export const SURFACE_MODES = [
  { id: "steady", label: "STEADY" },
  { id: "surge", label: "SURGE" },
  { id: "lock", label: "LOCK" },
];

export function HardwareControlDeck({
  surfaceMode,
  locked,
  scanBurst,
  gain,
  audioEnabled,
  onModeChange,
  onLockToggle,
  onScanBurst,
  onGainChange,
  onAudioToggle,
}) {
  return (
    <div className="hardware-controls">
      <div className="hardware-controls-head">
        <small>PHYSICAL CONTROL BAY</small>
        <strong>{surfaceMode.toUpperCase()}</strong>
      </div>
      <div className="mode-bank" role="group" aria-label="Surface mode">
        {SURFACE_MODES.map((mode) => (
          <button
            key={mode.id}
            type="button"
            className={`rocker-switch ${surfaceMode === mode.id ? "is-active" : ""}`}
            onClick={() => onModeChange(mode.id)}
            disabled={locked}
          >
            <span className="rocker-cap" />
            <span>{mode.label}</span>
          </button>
        ))}
      </div>
      <div className="hardware-dial-row">
        <button
          type="button"
          className={`hardware-dial ${scanBurst ? "is-pulsing" : ""}`}
          onClick={onScanBurst}
          aria-label="Trigger scan burst"
        >
          <span className="dial-ring" />
          <span className="dial-pointer" style={{ transform: `rotate(${gain * 2.7}deg)` }} />
        </button>
        <div className="gain-block">
          <label htmlFor="gain-slider">GAIN</label>
          <input id="gain-slider" className="gain-slider" type="range" min="0" max="100" value={gain} onChange={(e) => onGainChange(Number(e.target.value))} />
          <div className="gain-readout">{gain}%</div>
        </div>
      </div>
      <div className="hardware-footer">
        <button type="button" className={`lock-toggle ${locked ? "is-active" : ""}`} onClick={onLockToggle}>
          {locked ? "UNLOCK SHELL" : "LOCK SHELL"}
        </button>
        <button type="button" className={`audio-toggle ${audioEnabled ? "is-active" : ""}`} onClick={onAudioToggle}>
          AUDIO {audioEnabled ? "ON" : "OFF"}
        </button>
        <div className="hardware-legend">LOW-PLAYBACK // PHYSICAL FEEDBACK ENABLED</div>
      </div>
    </div>
  );
}

export function ActivityRibbon({
  surfaceMode,
  isStreaming,
  scanBurst,
  gain,
  liveMemoryHits,
  webHits,
  endpointUp,
  endpointTotal,
  phase,
  powerState,
  alarmLevel,
  telemetryBand,
  selfCheckPulse,
}) {
  const modeTone = surfaceMode === "surge" ? "amber" : surfaceMode === "lock" ? "violet" : "green";
  const phaseTone = phase === "none" ? "steel" : phase === "silence" ? "green" : "cyan";
  const syncTone = endpointUp < endpointTotal ? (endpointUp <= Math.max(1, endpointTotal - 2) ? "red" : "amber") : "green";
  const ribbonItems = [
    { label: "MODE", value: surfaceMode.toUpperCase(), tone: modeTone, blink: surfaceMode !== "steady" },
    { label: "PHASE", value: phaseLabel(phase), tone: phaseTone, blink: phase !== "none" },
    { label: "STREAM", value: isStreaming ? "ACTIVE" : "IDLE", tone: isStreaming ? "cyan" : "green", blink: isStreaming },
    { label: "SCAN", value: scanBurst ? "BURST" : "STABLE", tone: scanBurst ? "amber" : "steel", blink: scanBurst },
    { label: "MEM", value: liveMemoryHits.length, tone: liveMemoryHits.length > 0 ? "violet" : "steel", blink: liveMemoryHits.length > 0 },
    { label: "WEB", value: webHits.length, tone: webHits.length > 0 ? "orange" : "steel", blink: webHits.length > 0 },
    { label: "SYNC", value: selfCheckPulse ? "SYNC OK" : `${endpointUp}/${endpointTotal}`, tone: syncTone, blink: syncTone !== "green" || selfCheckPulse },
    { label: "PWR", value: powerState, tone: alarmLevel === "red" ? "red" : alarmLevel === "amber" ? "amber" : "cyan", blink: telemetryBand === "overdrive" },
  ];

  const ribbonIntensity = scanBurst ? 1 : isStreaming ? 0.82 : 0.56;

  return (
    <div
      className={`activity-ribbon ${isStreaming ? "is-hot" : ""} ${scanBurst ? "is-surging" : ""} band-${telemetryBand}`}
      style={{ "--ribbon-intensity": String(ribbonIntensity) }}
    >
      <div className="activity-ribbon-track" aria-hidden="true">
        {Array.from({ length: 16 }, (_, i) => (
          <span key={i} style={{ animationDelay: `${i * 0.18}s`, transform: `scaleY(${0.45 + (gain / 100) * 0.75})` }} />
        ))}
      </div>
      <div className="activity-ribbon-content">
        {ribbonItems.map((item) => (
          <div key={item.label} className={`activity-chip tone-${item.tone} ${item.blink ? "is-alert" : ""}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export function IndicatorLamp({ label, value, blink = false, tone = "green" }) {
  return (
    <div className={`indicator-lamp tone-${tone} ${blink ? "is-blinking" : ""}`}>
      <span className="indicator-led" />
      <div className="indicator-copy">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

export function SparkGraph({ label, values = [], tone = "cyan" }) {
  const safeValues = values.length ? values : [0];
  const tallest = Math.max(...safeValues, 1);
  return (
    <div className={`spark-graph tone-${tone}`}>
      <div className="spark-bars" aria-hidden="true">
        {safeValues.map((value, index) => (
          <span
            key={`${label}-${index}`}
            style={{ height: `${Math.max(8, (value / tallest) * 100)}%`, animationDelay: `${index * 90}ms` }}
          />
        ))}
      </div>
      <small>{label}</small>
    </div>
  );
}

export function SignalArray({
  surfaceMode,
  isStreaming,
  scanBurst,
  gain,
  panelLocked,
  coreRuntimeState,
  liveMemoryHits,
  webHits,
  runtime,
  planningProgressPct,
  evidenceVerifiedPct,
  approvedPending,
  telemetryBand,
}) {
  const pulseSeed = scanBurst ? 8 : isStreaming ? 5 : 2;
  const telemetryGraph = Array.from({ length: 18 }, (_, i) => {
    const phase = i / 3.2;
    const base = 18 + Math.sin(phase + pulseSeed) * 8;
    const telemetryLift = Number(runtime.telemetry.poll_ms || 0) / 3;
    const modeLift = surfaceMode === "surge" ? 10 : surfaceMode === "lock" ? -4 : 0;
    return Math.max(6, Math.min(100, base + telemetryLift + modeLift + (gain / 12)));
  });
  const stateGraph = [
    planningProgressPct,
    evidenceVerifiedPct,
    approvedPending * 25,
    liveMemoryHits.length * 20,
    webHits.length * 20,
    surfaceMode === "surge" ? 88 : surfaceMode === "lock" ? 24 : 56,
    isStreaming ? 82 : 20,
    scanBurst ? 96 : 18,
  ];
  const activityGraph = Array.from({ length: 12 }, (_, i) => {
    const memoryLift = liveMemoryHits.length * 9;
    const webLift = webHits.length * 7;
    const lockPenalty = panelLocked ? -10 : 0;
    return Math.max(5, Math.min(100, 28 + Math.sin(i * 0.7 + pulseSeed) * 18 + memoryLift + webLift + lockPenalty));
  });

  return (
    <section className={`signal-array band-${telemetryBand} mode-${surfaceMode} ${scanBurst ? "is-surging" : ""}`}>
      <div className="signal-array-head">
        <div>
          <small>SYSTEM LIGHTS // INDICATORS // WAVEFORMS</small>
          <strong>{coreRuntimeState}</strong>
        </div>
        <div className="signal-array-ticker" aria-hidden="true">
          <span className={isStreaming ? "is-hot" : ""} />
          <span className={scanBurst ? "is-hot" : ""} />
          <span className={panelLocked ? "is-hot" : ""} />
          <span />
          <span />
          <span />
        </div>
      </div>
      <div className="indicator-grid">
        <IndicatorLamp label="LINK" value={coreRuntimeState} blink={coreRuntimeState !== "OPERATIONAL"} tone={coreRuntimeState === "OPERATIONAL" ? "green" : "amber"} />
        <IndicatorLamp label="STREAM" value={isStreaming ? "ACTIVE" : "IDLE"} blink={isStreaming} tone={isStreaming ? "cyan" : "green"} />
        <IndicatorLamp label="SCAN" value={scanBurst ? "BURST" : "ARMED"} blink={scanBurst} tone={scanBurst ? "amber" : "green"} />
        <IndicatorLamp label="LOCK" value={panelLocked ? "ENGAGED" : "OPEN"} blink={panelLocked} tone={panelLocked ? "red" : "green"} />
        <IndicatorLamp label="MEM" value={liveMemoryHits.length} blink={liveMemoryHits.length > 0} tone="violet" />
        <IndicatorLamp label="WEB" value={webHits.length} blink={webHits.length > 0} tone="orange" />
      </div>
      <div className="graph-grid">
        <SparkGraph label="Telemetry Drift" tone="green" values={telemetryGraph} />
        <SparkGraph label="State Pressure" tone="amber" values={stateGraph} />
        <SparkGraph label="Activity Envelope" tone="cyan" values={activityGraph} />
      </div>
    </section>
  );
}

export function AnnunciatorStack({ alarms, onAcknowledge, onAcknowledgeAll }) {
  return (
    <section className="annunciator-stack">
      <div className="annunciator-head">
        <div>
          <small>ANNUNCIATOR BANK</small>
          <strong>{alarms.length ? `${alarms.length} ACTIVE` : "ALL SYSTEMS NOMINAL"}</strong>
        </div>
        <button type="button" onClick={onAcknowledgeAll} disabled={!alarms.length}>
          ACK ALL
        </button>
      </div>
      <div className="annunciator-grid">
        {alarms.length ? (
          alarms.map((alarm) => (
            <div key={alarm.id} className={`annunciator tone-${alarm.level} ${alarm.latched ? "is-latched" : ""}`}>
              <div className="annunciator-led" />
              <div className="annunciator-copy">
                <strong>{alarm.label}</strong>
                <span>{alarm.detail}</span>
              </div>
              <button type="button" onClick={() => onAcknowledge(alarm.id)}>ACK</button>
            </div>
          ))
        ) : (
          <div className="annunciator annunciator-clear tone-green">
            <div className="annunciator-led" />
            <div className="annunciator-copy">
              <strong>NO ACTIVE ALERTS</strong>
              <span>All panels within operational bands</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
