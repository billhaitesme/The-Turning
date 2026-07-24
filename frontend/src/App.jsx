import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8001";
const ASSISTANT_NAME = "0M3-G4-ARC";
const DIRECT_MODEL = "dolphin-mixtral:8x7b";
const ACTIVE_ADAPTERS = {
  backend_health_check: "A-001",
  git_status: "A-002",
  filesystem_inspection: "A-003",
  local_model_status: "A-004",
  test_runner: "A-005",
};

const BOOT_SEQUENCE = [
  { label: "CORE IGNITION", delay: 420 },
  { label: "SENSOR CALIBRATION", delay: 520 },
  { label: "BUS LINK", delay: 540 },
  { label: "READY", delay: 480 },
];

const COGNITIVE_STAGES = [
  "RECEIVING",
  "CLASSIFYING",
  "IDENTITY",
  "MEMORY",
  "REASONING",
  "PLANNING",
  "COMPOSING",
  "TRANSMITTING",
];

function fmtTime(value) {
  if (!value) return "--";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "--";
  return d.toLocaleTimeString();
}

function phaseLabel(name) {
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

function statusFromError(error) {
  return error ? "ERROR" : "READY";
}

function panelPattern({ error = false, waiting = false, input = false, output = false }) {
  if (error) return "error";
  if (waiting) return "wait";
  if (output) return "output";
  if (input) return "input";
  return "idle";
}

function cadenceBand(load) {
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

function tunedCadence(band, pattern) {
  const raw = cadenceFromBand(band) * patternCadenceBoost(pattern);
  return Math.max(0.65, Math.min(2.35, raw));
}

function pushHistory(history, value) {
  const bounded = Math.max(0, Math.min(100, Number(value) || 0));
  const next = [...history, bounded];
  return next.length > 24 ? next.slice(next.length - 24) : next;
}

function playTone(context, {
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

function PanelFrame({
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
      className={`panel-frame panel-${accent} panel-${size} ${live ? "is-live" : ""} ${blink ? "is-blink" : ""} pattern-${pattern} band-${band} warm-stage-${warmStage} ${warmStage < 4 ? "is-warming" : ""}`}
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
                {subtitle ? <p>{subtitle}</p> : null}
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
                </div>
              </div>
            </div>
            <div className="panel-display">{children}</div>
          </div>
        </div>
      </div>
    </section>
  );
}

function StatusLamp({ status, pulse }) {
  const normalized = String(status || "OFFLINE").toLowerCase();
  return (
    <div className={`status-lamp lamp-${normalized} ${pulse ? "lamp-pulse" : ""}`}>
      <span className="dot" />
      <span>{String(status || "OFFLINE").toUpperCase()}</span>
    </div>
  );
}

function SystemBadge({ label, value }) {
  return (
    <div className="system-badge">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}

function DataPlate({ label, value }) {
  return (
    <div className="data-plate">
      <span>{label}</span>
      <strong>{value ?? "--"}</strong>
    </div>
  );
}

function SignalBar({ value = 0 }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="signal-bar">
      <div className="signal-fill" style={{ width: `${bounded}%` }} />
    </div>
  );
}

function SegmentMeter({ segments = 5, active = 0 }) {
  const items = Array.from({ length: segments }, (_, i) => i < active);
  return (
    <div className="segment-meter">
      {items.map((on, i) => (
        <span key={i} className={on ? "on" : "off"} />
      ))}
    </div>
  );
}

function CircularGauge({ label, value = 0 }) {
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

function ratioPct(part, total) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.max(0, Math.min(100, (part / total) * 100));
}

function RadarDisplay({ value = 0 }) {
  return (
    <div className="radar-display">
      <div className="sweep" style={{ transform: `rotate(${value * 3.6}deg)` }} />
    </div>
  );
}

function ScopeTrace({ value = 0 }) {
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

function MeterStack({ values = [] }) {
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

function toAurebeshGlyphText(text) {
  return String(text || "").toUpperCase().trim();
}

function EvidenceStack({ results }) {
  const stats = { declared: 0, configured: 0, observed: 0, verified: 0, unknown: 0 };
  for (const result of results || []) {
    for (const c of result?.evidence_candidates || []) {
      const key = String(c?.state_type || "observed").toLowerCase();
      if (Object.prototype.hasOwnProperty.call(stats, key)) stats[key] += 1;
      else stats.observed += 1;
    }
  }

  return (
    <div className="evidence-stack">
      {Object.entries(stats).map(([k, v]) => (
        <DataPlate key={k} label={k.toUpperCase()} value={v} />
      ))}
    </div>
  );
}

function AdapterTile({ descriptor, lastResult, lastRequest }) {
  const adapterId = ACTIVE_ADAPTERS[descriptor.name] || "A-???";
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

function CognitiveBus({ items, pulseIndex, cognitiveStage, silenceMode }) {
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

function ChroniclePlate({ lastResult }) {
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
      <div>Epoch IX-A</div>      <div>First Trusted Runtime Observation</div>
      <div>Verified: Backend Health</div>
      <div>Method: Approved Local Adapter</div>
      <div>Result: {lastResult?.output?.status_code ? `HTTP ${lastResult.output.status_code}` : "--"}</div>
      <div>Duration: {lastResult?.duration_ms ? `${Number(lastResult.duration_ms).toFixed(3)} ms` : "--"}</div>
    </div>
  );
}

const SURFACE_MODES = [
  { id: "steady", label: "STEADY" },
  { id: "surge", label: "SURGE" },
  { id: "lock", label: "LOCK" },
];

function HardwareControlDeck({
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

function ActivityRibbon({
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

function IndicatorLamp({ label, value, blink = false, tone = "green" }) {
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

function SparkGraph({ label, values = [], tone = "cyan" }) {
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

function SignalArray({
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

function AnnunciatorStack({ alarms, onAcknowledge, onAcknowledgeAll }) {
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

export default function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState("");
  const [conversationMode, setConversationMode] = useState("runtime");
  const [status, setStatus] = useState("STANDBY");
  const [learning, setLearning] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryResults, setMemoryResults] = useState([]);
  const [liveMemoryHits, setLiveMemoryHits] = useState([]);
  const [webHits, setWebHits] = useState([]);
  const [currentPhase, setCurrentPhase] = useState("none");
  const [isStreaming, setIsStreaming] = useState(false);
  const [translatorOpen, setTranslatorOpen] = useState(false);
  const [translatorInput, setTranslatorInput] = useState("STANDBY NO ACTIVE PHASE BRIDGE");
  const [surfaceMode, setSurfaceMode] = useState("steady");
  const [panelLocked, setPanelLocked] = useState(false);
  const [scanBurst, setScanBurst] = useState(false);
  const [gain, setGain] = useState(62);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [audioPrimed, setAudioPrimed] = useState(false);
  const [busPulseIndex, setBusPulseIndex] = useState(-1);
  const [cognitiveStage, setCognitiveStage] = useState("RECEIVING");
  const [selfCheckPulse, setSelfCheckPulse] = useState(false);
  const [lastCognitiveActivityAt, setLastCognitiveActivityAt] = useState(Date.now());
  const [activityTick, setActivityTick] = useState(Date.now());
  const [bootStage, setBootStage] = useState(0);
  const [bootReady, setBootReady] = useState(false);
  const [recoveryPulse, setRecoveryPulse] = useState(false);
  const [ackedAlarms, setAckedAlarms] = useState({});
  const [panelHistory, setPanelHistory] = useState(() => ({
    identity: Array(14).fill(14),
    evidence: Array(14).fill(10),
    reasoning: Array(14).fill(12),
    command: Array(14).fill(18),
    planning: Array(14).fill(9),
    deliberation: Array(14).fill(8),
    adapters: Array(14).fill(16),
    operations: Array(14).fill(20),
  }));
  const scanBurstTimer = useRef(null);
  const recoveryTimer = useRef(null);
  const lastEndpointUp = useRef(null);
  const audioContextRef = useRef(null);
  const busPulseTimerRef = useRef(null);
  const lastAlarmIdsRef = useRef([]);
  const lastBootStageRef = useRef(0);
  const lastToolResultCountRef = useRef(0);

  function startBusPulseSequence() {
    const path = [0, 1, 2, 3, 4, 5];
    if (busPulseTimerRef.current) {
      clearInterval(busPulseTimerRef.current);
    }
    let cursor = 0;
    setBusPulseIndex(path[cursor]);
    busPulseTimerRef.current = setInterval(() => {
      cursor += 1;
      if (cursor >= path.length) {
        clearInterval(busPulseTimerRef.current);
        busPulseTimerRef.current = null;
        setBusPulseIndex(-1);
        return;
      }
      setBusPulseIndex(path[cursor]);
    }, 72);
  }

  function getAudioContext() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioCtx();
    }
    return audioContextRef.current;
  }

  async function primeAudio() {
    const ctx = getAudioContext();
    if (!ctx) return false;
    if (ctx.state === "suspended") {
      try {
        await ctx.resume();
      } catch {
        return false;
      }
    }
    return ctx.state === "running";
  }

  async function playAudioCue(kind) {
    if (!audioEnabled) return;
    const ready = await primeAudio();
    if (!ready) return;
    setAudioPrimed(true);
    const ctx = audioContextRef.current;
    if (!ctx) return;

    if (kind === "boot") {
      playTone(ctx, { frequency: 240, duration: 0.07, type: "triangle", gain: 0.018, offset: 0 });
      playTone(ctx, { frequency: 320, duration: 0.07, type: "triangle", gain: 0.018, offset: 0.08 });
      return;
    }
    if (kind === "recovery") {
      playTone(ctx, { frequency: 180, duration: 0.12, type: "sawtooth", gain: 0.02, offset: 0 });
      playTone(ctx, { frequency: 270, duration: 0.1, type: "triangle", gain: 0.018, offset: 0.13 });
      return;
    }
    if (kind === "alarm-red") {
      playTone(ctx, { frequency: 210, duration: 0.12, type: "square", gain: 0.023, offset: 0 });
      playTone(ctx, { frequency: 170, duration: 0.12, type: "square", gain: 0.023, offset: 0.16 });
      return;
    }
    if (kind === "alarm-amber") {
      playTone(ctx, { frequency: 250, duration: 0.09, type: "square", gain: 0.018, offset: 0 });
      playTone(ctx, { frequency: 300, duration: 0.08, type: "triangle", gain: 0.016, offset: 0.11 });
      return;
    }
    if (kind === "scan") {
      playTone(ctx, { frequency: 380, duration: 0.06, type: "sine", gain: 0.014, offset: 0 });
      return;
    }
    if (kind === "navigation") {
      playTone(ctx, { frequency: 290, duration: 0.04, type: "square", gain: 0.012, offset: 0 });
      return;
    }
    if (kind === "ack") {
      playTone(ctx, { frequency: 230, duration: 0.035, type: "triangle", gain: 0.011, offset: 0 });
      return;
    }
    if (kind === "verified") {
      playTone(ctx, { frequency: 360, duration: 0.05, type: "sine", gain: 0.012, offset: 0 });
      playTone(ctx, { frequency: 430, duration: 0.05, type: "sine", gain: 0.012, offset: 0.06 });
      return;
    }
    if (kind === "completion") {
      playTone(ctx, { frequency: 280, duration: 0.06, type: "triangle", gain: 0.013, offset: 0 });
      playTone(ctx, { frequency: 340, duration: 0.06, type: "triangle", gain: 0.013, offset: 0.08 });
      playTone(ctx, { frequency: 420, duration: 0.06, type: "triangle", gain: 0.013, offset: 0.16 });
      return;
    }
    if (kind === "chronicle") {
      playTone(ctx, { frequency: 330, duration: 0.08, type: "sine", gain: 0.01, offset: 0 });
      return;
    }
  }

  const [runtime, setRuntime] = useState({
    systemStatus: null,
    tools: [],
    plans: [],
    decisions: [],
    reasoning: null,
    toolRequests: [],
    toolResults: [],
    errors: {},
    busPulse: {},
    lastSeen: {},
    telemetry: {
      poll_ms: 0,
      endpoint_up: 0,
      endpoint_total: 7,
      last_poll_at: null,
    },
  });

  const hashes = useRef({});

  useEffect(() => {
    const onPrime = () => {
      primeAudio().then((ready) => {
        if (ready) setAudioPrimed(true);
      });
    };
    window.addEventListener("pointerdown", onPrime, { once: true });

    return () => {
      if (scanBurstTimer.current) {
        clearTimeout(scanBurstTimer.current);
      }
      if (recoveryTimer.current) {
        clearTimeout(recoveryTimer.current);
      }
      if (busPulseTimerRef.current) {
        clearInterval(busPulseTimerRef.current);
      }
      window.removeEventListener("pointerdown", onPrime);
    };
  }, []);

  useEffect(() => {
    const tickTimer = setInterval(() => setActivityTick(Date.now()), 1000);
    const selfCheckTimer = setInterval(() => {
      setSelfCheckPulse(true);
      setTimeout(() => setSelfCheckPulse(false), 700);
    }, 180000);

    return () => {
      clearInterval(tickTimer);
      clearInterval(selfCheckTimer);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer = null;
    let index = 0;

    const advance = () => {
      if (cancelled) return;
      if (index >= BOOT_SEQUENCE.length - 1) {
        setBootStage(BOOT_SEQUENCE.length - 1);
        setBootReady(true);
        return;
      }
      index += 1;
      setBootStage(index);
      timer = setTimeout(advance, BOOT_SEQUENCE[index].delay);
    };

    timer = setTimeout(advance, BOOT_SEQUENCE[0].delay);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (bootStage > lastBootStageRef.current) {
      lastBootStageRef.current = bootStage;
      playAudioCue("boot");
    }
  }, [bootStage]);

  useEffect(() => {
    let alive = true;
    let timeoutId = null;

    const poll = async () => {
      const pollStartedAt = performance.now();
      const endpoints = [
        ["systemStatus", `${API_BASE}/system/status`],
        ["tools", `${API_BASE}/system/tools`],
        ["plans", `${API_BASE}/system/plans`],
        ["decisions", `${API_BASE}/system/decisions`],
        ["reasoning", `${API_BASE}/system/reasoning`],
        ["toolRequests", `${API_BASE}/system/tool-requests?limit=50`],
        ["toolResults", `${API_BASE}/system/tool-results?limit=50`],
      ];

      const nextErrors = {};
      const nextData = {};
      const pulse = {};
      const now = new Date().toISOString();

      await Promise.all(
        endpoints.map(async ([key, url]) => {
          try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            nextData[key] = data;
            const serialized = JSON.stringify(data);
            if (hashes.current[key] && hashes.current[key] !== serialized) {
              pulse[key] = true;
            }
            hashes.current[key] = serialized;
          } catch (err) {
            nextErrors[key] = String(err?.message || err);
          }
        })
      );

      if (!alive) return;
      setRuntime((prev) => ({
        ...prev,
        systemStatus: nextData.systemStatus || prev.systemStatus,
        tools: nextData.tools?.tools || prev.tools,
        plans: nextData.plans?.plans || prev.plans,
        decisions: nextData.decisions?.decisions || prev.decisions,
        reasoning: nextData.reasoning?.reasoning || nextData.reasoning || prev.reasoning,
        toolRequests: nextData.toolRequests?.requests || nextData.toolRequests || prev.toolRequests,
        toolResults: nextData.toolResults?.results || nextData.toolResults || prev.toolResults,
        errors: nextErrors,
        busPulse: pulse,
        lastSeen: {
          ...prev.lastSeen,
          ...Object.fromEntries(Object.keys(nextData).map((k) => [k, now])),
        },
        telemetry: {
          poll_ms: Math.round((performance.now() - pollStartedAt) * 10) / 10,
          endpoint_up: Object.keys(nextData).length,
          endpoint_total: endpoints.length,
          last_poll_at: now,
        },
      }));

      if (Object.keys(pulse).length > 0) {
        startBusPulseSequence();
      }

      timeoutId = setTimeout(poll, 4000);
    };

    poll();
    return () => {
      alive = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  async function createConversation() {
    try {
      setStatus("INITIALIZING SESSION");
      const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "demo", title: "session" }),
      });

      if (!res.ok) {
        throw new Error(`Create conversation failed: ${res.status}`);
      }

      const data = await res.json();
      setConversationId(data.conversation_id);
      setStatus("CHANNEL OPEN");
      setMessages([]);
      setLearning(null);
      setConfidence(null);
      setMemoryResults([]);
      setLiveMemoryHits([]);
      setWebHits([]);
      setCurrentPhase("none");
      setTranslatorInput("CHANNEL OPEN BRIDGE ZERO");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  async function sendMessage() {
    if (!message.trim()) {
      setStatus("WARNING: ENTER INPUT");
      return;
    }

    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }

    const userMsg = message;
    setMessages((prev) => [...prev, { role: "USER", content: userMsg }]);
    setMessage("");
    setStatus(conversationMode === "direct" ? "DIRECT MODEL" : "CHANNEL OPEN");
    if (conversationMode === "direct") {
      setCurrentPhase("none");
    } else {
      setCurrentPhase("guide");
      setCognitiveStage("RECEIVING");
      setLastCognitiveActivityAt(Date.now());
      startBusPulseSequence();
    }

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: "demo",
          message: userMsg,
          mode: conversationMode,
        }),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: conversationMode === "direct" ? DIRECT_MODEL : ASSISTANT_NAME, content: data.reply }]);
      setLearning(data.learning || null);
      setStatus(conversationMode === "direct" ? "DIRECT COMPLETE" : "LINK ESTABLISHED");
      setCurrentPhase(conversationMode === "direct" ? "none" : "silence");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setCurrentPhase("none");
    }
  }

  async function streamMessage() {
    if (!message.trim()) {
      setStatus("WARNING: ENTER INPUT");
      return;
    }

    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }

    const userMsg = message;
    setMessages((prev) => [...prev, { role: "USER", content: userMsg }]);
    setMessage("");
    setStatus(conversationMode === "direct" ? "DIRECT MODEL" : "CHANNEL OPEN");
    setIsStreaming(true);
    if (conversationMode === "direct") {
      setCurrentPhase("none");
    } else {
      setCurrentPhase("whisper");
      setCognitiveStage("RECEIVING");
      setLastCognitiveActivityAt(Date.now());
      startBusPulseSequence();
    }
    setLiveMemoryHits([]);
    setWebHits([]);

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: "demo",
          message: userMsg,
          mode: conversationMode,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(await res.text());
      }

      let assistantText = "";
      let streamEnded = false;
      const responseRole = conversationMode === "direct" ? DIRECT_MODEL : ASSISTANT_NAME;
      setMessages((prev) => [...prev, { role: responseRole, content: "" }]);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!streamEnded) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          if (!event.startsWith("data: ")) continue;

          const payload = JSON.parse(event.slice(6));
          if (payload.type === "phase") {
            setCurrentPhase(payload.name);
          } else if (payload.type === "memory") {
            setLiveMemoryHits(payload.items || []);
          } else if (payload.type === "web") {
            setWebHits(payload.items || []);
          } else if (payload.type === "delta") {
            assistantText += payload.text || "";
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { role: responseRole, content: assistantText };
              return next;
            });
          } else if (payload.type === "learning") {
            setLearning(payload.data);
          } else if (payload.type === "confidence") {
            setConfidence(payload.data);
          } else if (payload.type === "done") {
            setStatus(conversationMode === "direct" ? "DIRECT COMPLETE" : "STREAM COMPLETE");
            setCurrentPhase(conversationMode === "direct" ? "none" : "silence");
            playAudioCue("completion");
          } else if (payload.type === "mode" && payload.name === "direct") {
            setStatus(`DIRECT // ${payload.model || DIRECT_MODEL}`);
          } else if (payload.type === "end") {
            streamEnded = true;
          } else if (payload.type === "error") {
            throw new Error(payload.error);
          }
        }
      }
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setCurrentPhase("none");
    } finally {
      setIsStreaming(false);
    }
  }

  async function searchMemory() {
    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }
    if (!memoryQuery.trim()) {
      setStatus("WARNING: ENTER MEMORY QUERY");
      return;
    }

    try {
      setStatus("SCANNING MEMORY INDEX");
      const res = await fetch(`${API_BASE}/conversations/${conversationId}/memories?q=${encodeURIComponent(memoryQuery)}`);
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = await res.json();
      setMemoryResults(data.memories || []);
      setStatus("MEMORY SCAN COMPLETE");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  function captureLiveTranslator() {
    setTranslatorInput(`${status} ${phaseLabel(currentPhase)} ${runtime.systemStatus?.branch || "BRIDGE"}`.toUpperCase());
  }

  function triggerHardwareScan() {
    setScanBurst(true);
    playAudioCue("scan");
    setLastCognitiveActivityAt(Date.now());
    if (scanBurstTimer.current) clearTimeout(scanBurstTimer.current);
    scanBurstTimer.current = setTimeout(() => setScanBurst(false), 1100);
  }

  function handleModeChange(mode) {
    if (panelLocked) return;
    setSurfaceMode(mode);
    playAudioCue("navigation");
  }

  const lastToolResult = runtime.toolResults?.[runtime.toolResults.length - 1] || null;
  const lastToolRequest = runtime.toolRequests?.[runtime.toolRequests.length - 1] || null;
  const activePlan = runtime.plans?.find?.((p) => p?.status === "active") || runtime.plans?.[0] || null;
  const evidenceCandidates = runtime.toolResults.flatMap((r) => r?.evidence_candidates || []);
  const verifiedEvidence = evidenceCandidates.filter((c) => String(c?.state_type || "").toLowerCase() === "verified").length;

  const coreRuntimeState = useMemo(() => {
    const systemStatusError = Boolean(runtime.errors.systemStatus);
    const otherSignals = runtime.tools.length || runtime.toolResults.length || runtime.plans.length || runtime.decisions.length;
    if (!systemStatusError) return "OPERATIONAL";
    if (otherSignals) return "NO TELEMETRY";
    return "UNAVAILABLE";
  }, [runtime]);

  const planningProgressPct = useMemo(() => {
    const segments = Number(activePlan?.progress_segments || 0);
    return Math.max(0, Math.min(100, segments * 20));
  }, [activePlan]);

  const adapterReadyPct = useMemo(() => {
    const total = runtime.tools.length;
    const ready = runtime.tools.filter((t) => t?.enabled).length;
    return ratioPct(ready, total || 1);
  }, [runtime.tools]);

  const evidenceVerifiedPct = useMemo(() => ratioPct(verifiedEvidence, evidenceCandidates.length || 1), [verifiedEvidence, evidenceCandidates.length]);

  const busItems = useMemo(
    () => [
      {
        key: "identity",
        label: "IDENTITY",
        status: learning ? "READY" : "BUSY",
        pulse: !!runtime.busPulse.reasoning,
        tone: "cyan",
        trait: "stable",
        value: Math.max(8, Math.min(100, (Number(learning?.reflection_score || 0) * 100) + (conversationId ? 20 : 0))),
        lastActivity: runtime.lastSeen.reasoning || runtime.lastSeen.systemStatus,
      },
      {
        key: "evidence",
        label: "EVIDENCE",
        status: runtime.toolResults.length ? "READY" : "BUSY",
        pulse: !!runtime.busPulse.toolResults,
        tone: "amber",
        trait: "flash",
        value: Math.max(6, Math.min(100, evidenceCandidates.length * 11)),
        lastActivity: runtime.lastSeen.toolResults || runtime.lastSeen.systemStatus,
      },
      {
        key: "reasoning",
        label: "REASONING",
        status: statusFromError(runtime.errors.reasoning),
        pulse: !!runtime.busPulse.reasoning,
        tone: "orange",
        trait: "oscillate",
        value: Math.max(8, Math.min(100, Number(confidence?.reflection_score || 0) * 100)),
        lastActivity: runtime.lastSeen.reasoning || runtime.lastSeen.systemStatus,
      },
      {
        key: "planning",
        label: "PLANNING",
        status: statusFromError(runtime.errors.plans),
        pulse: !!runtime.busPulse.plans,
        tone: "green",
        trait: "progress",
        value: Math.max(5, Math.min(100, Number(activePlan?.progress_segments || 0) * 20)),
        lastActivity: runtime.lastSeen.plans || runtime.lastSeen.systemStatus,
      },
      {
        key: "tools",
        label: "TOOLS",
        status: statusFromError(runtime.errors.tools),
        pulse: !!runtime.busPulse.tools || !!runtime.busPulse.toolResults,
        tone: "white",
        trait: "discrete",
        value: Math.max(5, Math.min(100, runtime.toolResults.length * 14)),
        lastActivity: runtime.lastSeen.tools || runtime.lastSeen.systemStatus,
      },
      {
        key: "deliberation",
        label: "DELIBERATION",
        status: statusFromError(runtime.errors.decisions),
        pulse: !!runtime.busPulse.decisions,
        tone: "violet",
        trait: "breathe",
        value: Math.max(5, Math.min(100, runtime.toolRequests.filter((r) => r?.status === "awaiting_approval").length * 26 + (runtime.decisions?.length || 0) * 12)),
        lastActivity: runtime.lastSeen.decisions || runtime.lastSeen.systemStatus,
      },
    ],
    [learning, runtime, conversationId, evidenceCandidates.length, confidence?.reflection_score, activePlan?.progress_segments]
  );

  const approvedPending = runtime.toolRequests.filter((r) => r?.status === "awaiting_approval").length;
  const translatorSource = translatorInput || `${status} ${phaseLabel(currentPhase)} ${runtime.systemStatus?.branch || "BRIDGE"}`;
  const translatorOutput = toAurebeshGlyphText(translatorSource).slice(0, 260);
  const motionClass = scanBurst ? "scan-burst" : "";
  const consoleLive = isStreaming || scanBurst || runtime.toolResults.length > 0 || runtime.tools.length > 0;
  const telemetryHealthPct = ratioPct(runtime.telemetry.endpoint_up, runtime.telemetry.endpoint_total || 1);
  const identitySignalPct = Math.max(Number(learning?.reflection_score || 0) * 100, conversationId ? 35 : 8);
  const identityFlowPct = Math.max(0, Math.min(100, messages.length * 6 + (isStreaming ? 26 : 0) + (liveMemoryHits.length + webHits.length) * 10));
  const evidenceFlowPct = Math.max(0, Math.min(100, evidenceCandidates.length * 14 + (runtime.busPulse.toolResults ? 18 : 0)));
  const reasoningConfidencePct = Math.min(100, Number(confidence?.reflection_score || 0) * 100);
  const reasoningFlowPct = Math.max(0, Math.min(100, Number(runtime.reasoning?.uncertainty_count || 0) * 18 + Number(runtime.reasoning?.conflict_count || 0) * 14));
  const commandThroughputPct = Math.max(0, Math.min(100, messages.length * 5 + (isStreaming ? 36 : 10)));
  const planningFlowPct = Math.max(0, Math.min(100, Number(activePlan?.blockers?.length || 0) * 22 + (runtime.busPulse.plans ? 18 : 0)));
  const deliberationPressurePct = Math.max(0, Math.min(100, approvedPending * 25 + (runtime.decisions?.length || 0) * 14));
  const adapterFlowPct = Math.max(0, Math.min(100, runtime.toolResults.length * 12 + (runtime.busPulse.tools ? 20 : 0)));
  const operationsFlowPct = Math.max(0, Math.min(100, runtime.toolResults.length * 11 + approvedPending * 20 + (scanBurst ? 18 : 0)));
  const lastMessage = messages[messages.length - 1] || null;
  const hasRecentUserInput = lastMessage?.role === "USER";
  const hasRecentAssistantOutput = lastMessage?.role === ASSISTANT_NAME;
  const statusWarning = String(status || "").toUpperCase().startsWith("WARNING");
  const silenceMode = !isStreaming && !scanBurst && activityTick - lastCognitiveActivityAt > 18000;

  const identityPanelPattern = panelPattern({
    error: coreRuntimeState === "UNAVAILABLE",
    waiting: !conversationId,
    input: hasRecentUserInput || currentPhase === "guide" || currentPhase === "whisper",
    output: hasRecentAssistantOutput || currentPhase === "bridge" || currentPhase === "mirror" || Boolean(learning),
  });
  const evidencePanelPattern = panelPattern({
    error: Boolean(runtime.errors.toolResults),
    waiting: runtime.toolRequests.length > 0 && runtime.toolResults.length === 0,
    input: Boolean(runtime.busPulse.toolRequests),
    output: Boolean(runtime.busPulse.toolResults),
  });
  const reasoningPanelPattern = panelPattern({
    error: Boolean(runtime.errors.reasoning),
    waiting: currentPhase === "bridge" || currentPhase === "whisper",
    input: hasRecentUserInput,
    output: Boolean(runtime.busPulse.reasoning || hasRecentAssistantOutput),
  });
  const commandPanelPattern = panelPattern({
    error: statusWarning || coreRuntimeState === "UNAVAILABLE",
    waiting: !conversationId || approvedPending > 0,
    input: hasRecentUserInput || currentPhase === "guide" || currentPhase === "whisper",
    output: isStreaming || hasRecentAssistantOutput,
  });
  const planningPanelPattern = panelPattern({
    error: Boolean(runtime.errors.plans),
    waiting: Boolean(activePlan?.blockers?.length),
    input: Boolean(runtime.busPulse.reasoning),
    output: Boolean(runtime.busPulse.plans),
  });
  const deliberationPanelPattern = panelPattern({
    error: Boolean(runtime.errors.decisions),
    waiting: approvedPending > 0,
    input: Boolean(runtime.busPulse.plans || runtime.busPulse.reasoning),
    output: Boolean(runtime.busPulse.decisions),
  });
  const adaptersPanelPattern = panelPattern({
    error: Boolean(runtime.errors.tools),
    waiting: approvedPending > 0,
    input: Boolean(runtime.busPulse.toolRequests),
    output: Boolean(runtime.busPulse.tools || runtime.busPulse.toolResults),
  });
  const opsPanelPattern = panelPattern({
    error: coreRuntimeState === "UNAVAILABLE",
    waiting: approvedPending > 0,
    input: scanBurst || Boolean(runtime.busPulse.toolRequests),
    output: Boolean(runtime.busPulse.toolResults || runtime.busPulse.decisions),
  });

  const identityLoad = Math.max(identitySignalPct, identityFlowPct);
  const evidenceLoad = Math.max(evidenceVerifiedPct, evidenceFlowPct);
  const reasoningLoad = Math.max(reasoningConfidencePct, reasoningFlowPct);
  const commandLoad = Math.max(commandThroughputPct, telemetryHealthPct);
  const planningLoad = Math.max(planningProgressPct, planningFlowPct);
  const deliberationLoad = Math.max(deliberationPressurePct, ratioPct(runtime.decisions?.length || 0, 6));
  const adaptersLoad = Math.max(adapterReadyPct, adapterFlowPct);
  const operationsLoad = Math.max(telemetryHealthPct, operationsFlowPct);

  const identityBand = cadenceBand(identityLoad);
  const evidenceBand = cadenceBand(evidenceLoad);
  const reasoningBand = cadenceBand(reasoningLoad);
  const commandBand = cadenceBand(commandLoad);
  const planningBand = cadenceBand(planningLoad);
  const deliberationBand = cadenceBand(deliberationLoad);
  const adaptersBand = cadenceBand(adaptersLoad);
  const operationsBand = cadenceBand(operationsLoad);

  const identityCadence = tunedCadence(identityBand, identityPanelPattern);
  const evidenceCadence = tunedCadence(evidenceBand, evidencePanelPattern);
  const reasoningCadence = tunedCadence(reasoningBand, reasoningPanelPattern);
  const commandCadence = tunedCadence(commandBand, commandPanelPattern);
  const planningCadence = tunedCadence(planningBand, planningPanelPattern);
  const deliberationCadence = tunedCadence(deliberationBand, deliberationPanelPattern);
  const adaptersCadence = tunedCadence(adaptersBand, adaptersPanelPattern);
  const operationsCadence = tunedCadence(operationsBand, opsPanelPattern);
  const telemetryBand = cadenceBand(telemetryHealthPct);
  const bootLabel = BOOT_SEQUENCE[Math.min(bootStage, BOOT_SEQUENCE.length - 1)]?.label || "CORE IGNITION";

  const powerState = !bootReady ? `BOOT // ${bootLabel}` : recoveryPulse ? "RECOVERING LINK" : "ONLINE";

  useEffect(() => {
    const current = runtime.telemetry.endpoint_up;
    if (!bootReady) {
      lastEndpointUp.current = current;
      return;
    }
    if (lastEndpointUp.current != null && current < lastEndpointUp.current) {
      setRecoveryPulse(true);
      playAudioCue("recovery");
      if (recoveryTimer.current) clearTimeout(recoveryTimer.current);
      recoveryTimer.current = setTimeout(() => setRecoveryPulse(false), 1800);
    }
    lastEndpointUp.current = current;
  }, [runtime.telemetry.endpoint_up, bootReady]);

  useEffect(() => {
    setPanelHistory((prev) => ({
      identity: pushHistory(prev.identity, Math.max(identitySignalPct, identityFlowPct)),
      evidence: pushHistory(prev.evidence, Math.max(evidenceVerifiedPct, evidenceFlowPct)),
      reasoning: pushHistory(prev.reasoning, Math.max(reasoningConfidencePct, reasoningFlowPct)),
      command: pushHistory(prev.command, Math.max(commandThroughputPct, telemetryHealthPct)),
      planning: pushHistory(prev.planning, Math.max(planningProgressPct, planningFlowPct)),
      deliberation: pushHistory(prev.deliberation, Math.max(deliberationPressurePct, ratioPct(runtime.decisions?.length || 0, 6))),
      adapters: pushHistory(prev.adapters, Math.max(adapterReadyPct, adapterFlowPct)),
      operations: pushHistory(prev.operations, Math.max(telemetryHealthPct, operationsFlowPct)),
    }));
  }, [
    identitySignalPct,
    identityFlowPct,
    evidenceVerifiedPct,
    evidenceFlowPct,
    reasoningConfidencePct,
    reasoningFlowPct,
    commandThroughputPct,
    telemetryHealthPct,
    planningProgressPct,
    planningFlowPct,
    deliberationPressurePct,
    runtime.decisions?.length,
    adapterReadyPct,
    adapterFlowPct,
    operationsFlowPct,
  ]);

  const rawAlarms = useMemo(() => {
    const alarms = [];
    if (!bootReady) {
      alarms.push({ id: "boot", level: "info", label: "BOOT SEQUENCE", detail: bootLabel, latched: true });
    }
    if (recoveryPulse) {
      alarms.push({ id: "recover", level: "amber", label: "LINK RECOVERY", detail: "Endpoint continuity dropped", latched: true });
    }
    if (runtime.telemetry.endpoint_up < runtime.telemetry.endpoint_total) {
      alarms.push({ id: "sync", level: "amber", label: "SYNC DEGRADED", detail: `${runtime.telemetry.endpoint_up}/${runtime.telemetry.endpoint_total} endpoints online`, latched: true });
    }
    if (approvedPending > 0) {
      alarms.push({ id: "approval", level: "violet", label: "APPROVAL QUEUE", detail: `${approvedPending} request(s) awaiting`, latched: false });
    }
    const errorCount = Object.keys(runtime.errors || {}).length;
    if (errorCount > 0) {
      alarms.push({ id: "errors", level: "red", label: "RUNTIME ERRORS", detail: `${errorCount} subsystem error(s)`, latched: true });
    }
    if (scanBurst) {
      alarms.push({ id: "scan", level: "cyan", label: "SCAN BURST", detail: "Manual scan burst active", latched: false });
    }
    return alarms;
  }, [bootReady, bootLabel, recoveryPulse, runtime.telemetry.endpoint_up, runtime.telemetry.endpoint_total, approvedPending, runtime.errors, scanBurst]);

  useEffect(() => {
    const active = new Set(rawAlarms.map((alarm) => alarm.id));
    setAckedAlarms((prev) => {
      const next = {};
      Object.keys(prev).forEach((key) => {
        if (active.has(key)) next[key] = prev[key];
      });
      return next;
    });
  }, [rawAlarms]);

  const alarms = rawAlarms.filter((alarm) => !ackedAlarms[alarm.id]);
  const alarmLevel = alarms.some((alarm) => alarm.level === "red")
    ? "red"
    : alarms.some((alarm) => alarm.level === "amber")
      ? "amber"
      : "green";

  useEffect(() => {
    const currentIds = alarms.map((alarm) => alarm.id);
    const hasNew = currentIds.some((id) => !lastAlarmIdsRef.current.includes(id));
    if (hasNew) {
      const hasRed = alarms.some((alarm) => alarm.level === "red");
      const hasAmber = alarms.some((alarm) => alarm.level === "amber");
      playAudioCue(hasRed ? "alarm-red" : hasAmber ? "alarm-amber" : "scan");
    }
    lastAlarmIdsRef.current = currentIds;
  }, [alarms]);

  useEffect(() => {
    if (isStreaming || scanBurst || hasRecentAssistantOutput || hasRecentUserInput || Object.keys(runtime.busPulse || {}).length > 0) {
      setLastCognitiveActivityAt(Date.now());
    }
  }, [isStreaming, scanBurst, hasRecentAssistantOutput, hasRecentUserInput, runtime.busPulse]);

  useEffect(() => {
    let nextStage = "RECEIVING";
    if (silenceMode) {
      nextStage = "RECEIVING";
    } else if (isStreaming) {
      if (currentPhase === "whisper") nextStage = "CLASSIFYING";
      else if (currentPhase === "guide") nextStage = "IDENTITY";
      else if (currentPhase === "bridge") nextStage = "REASONING";
      else if (currentPhase === "mirror") nextStage = "PLANNING";
      else nextStage = "COMPOSING";
    } else if (hasRecentAssistantOutput) {
      nextStage = "TRANSMITTING";
    } else if (hasRecentUserInput) {
      nextStage = "MEMORY";
    }
    setCognitiveStage(nextStage);
  }, [silenceMode, isStreaming, currentPhase, hasRecentAssistantOutput, hasRecentUserInput]);

  useEffect(() => {
    const count = runtime.toolResults.length;
    if (count > lastToolResultCountRef.current) {
      const newest = runtime.toolResults[count - 1];
      const hasVerified = (newest?.evidence_candidates || []).some((item) => String(item?.state_type || "").toLowerCase() === "verified");
      playAudioCue(hasVerified ? "verified" : "chronicle");
      startBusPulseSequence();
    }
    lastToolResultCountRef.current = count;
  }, [runtime.toolResults]);

  return (
    <div
      className={`bridge-app mode-${surfaceMode} ${panelLocked ? "panel-locked" : ""} ${motionClass} ${silenceMode ? "is-silence" : ""}`}
      style={{ "--gain-level": String(Math.max(0, Math.min(100, gain)) / 100) }}
    >
      <header className="command-header">
        <div className="identity-plate">
          <h1>OMEGA-ARC</h1>
          <h2>BRIDGE ZERO</h2>
          <div className="epoch-line">EPOCH IX // COMMAND DECK</div>          <StatusLamp status={bootReady ? (coreRuntimeState === "OPERATIONAL" ? "OPERATIONAL" : "WARNING") : "BOOTING"} pulse={!!runtime.busPulse.systemStatus || scanBurst || !bootReady} />
        </div>
        <div className="build-plate">
          <SystemBadge label="Core Runtime" value={coreRuntimeState} />
          <SystemBadge label="Power State" value={powerState} />
          <SystemBadge label="Phase" value={phaseLabel(currentPhase)} />
          <SystemBadge label="Build" value={runtime.systemStatus?.version || "v0.2.0"} />          <SystemBadge label="Branch" value={runtime.systemStatus?.branch || "feature/epoch8-tools"} />
          <SystemBadge label="Tag" value={runtime.systemStatus?.tag || "epoch-8a-trusted-diagnostics"} />
          <SystemBadge label="Tests" value={runtime.systemStatus?.tests_run || "310"} />
          <SystemBadge label="Active Adapters" value={runtime.tools.length} />
          <SystemBadge label="Poll" value={`${runtime.telemetry.poll_ms} ms`} />
          <SystemBadge label="Sync" value={`${runtime.telemetry.endpoint_up}/${runtime.telemetry.endpoint_total}`} />
          <SystemBadge label="Last Poll" value={fmtTime(runtime.telemetry.last_poll_at)} />
        </div>
        <HardwareControlDeck
          surfaceMode={surfaceMode}
          locked={panelLocked}
          scanBurst={scanBurst}
          gain={gain}
          audioEnabled={audioEnabled && audioPrimed}
          onModeChange={handleModeChange}
          onLockToggle={() => {
            setPanelLocked((value) => !value);
            playAudioCue("navigation");
          }}
          onScanBurst={triggerHardwareScan}
          onGainChange={setGain}
          onAudioToggle={() => {
            const next = !audioEnabled;
            setAudioEnabled(next);
            if (next) {
              playAudioCue("scan");
            }
          }}
        />
      </header>

      <ActivityRibbon
        surfaceMode={surfaceMode}
        isStreaming={isStreaming}
        scanBurst={scanBurst}
        gain={gain}
        liveMemoryHits={liveMemoryHits}
        webHits={webHits}
        endpointUp={runtime.telemetry.endpoint_up}
        endpointTotal={runtime.telemetry.endpoint_total}
        phase={currentPhase}
        powerState={powerState}
        alarmLevel={alarmLevel}
        telemetryBand={telemetryBand}
        selfCheckPulse={selfCheckPulse}
      />

      <AnnunciatorStack
        alarms={alarms}
        onAcknowledge={(id) => {
          setAckedAlarms((prev) => ({ ...prev, [id]: true }));
          playAudioCue("ack");
        }}
        onAcknowledgeAll={() => {
          const next = {};
          alarms.forEach((alarm) => {
            next[alarm.id] = true;
          });
          setAckedAlarms((prev) => ({ ...prev, ...next }));
          playAudioCue("ack");
        }}
      />

      <SignalArray
        surfaceMode={surfaceMode}
        isStreaming={isStreaming}
        scanBurst={scanBurst}
        gain={gain}
        panelLocked={panelLocked}
        coreRuntimeState={coreRuntimeState}
        liveMemoryHits={liveMemoryHits}
        webHits={webHits}
        runtime={runtime}
        planningProgressPct={planningProgressPct}
        evidenceVerifiedPct={evidenceVerifiedPct}
        approvedPending={approvedPending}
        telemetryBand={telemetryBand}
      />

      <CognitiveBus items={busItems} pulseIndex={busPulseIndex} cognitiveStage={cognitiveStage} silenceMode={silenceMode} />

      <div className="bus-backbone" aria-hidden="true">
        <span>IDENTITY</span>
        <span>EVIDENCE</span>
        <span>REASONING</span>
        <span>PLANNING</span>
        <span>DELIBERATION</span>
        <span>TOOLS</span>
      </div>

      <main className="bridge-grid">
        <aside className="left-bank">
          <PanelFrame
            title="Identity"
            accent="cyan"
            subtitle="Fact count, confidence, active project"
            serial="BZ-001 // ID"
            live={Boolean(conversationId || learning)}
            blink={Boolean(runtime.busPulse.reasoning || currentPhase !== "none")}
            throughput={identitySignalPct}
            flow={identityFlowPct}
            signalTone="cyan"
            pattern={identityPanelPattern}
            cadence={identityCadence}
            band={identityBand}
            sparkValues={panelHistory.identity}
          >
            <div className="plate-row">
              <CircularGauge label="Identity Confidence" value={Number(learning?.reflection_score || 0) * 100} />
              <div className="list-stack">
                <DataPlate label="Style" value={learning?.style || "--"} />
                <DataPlate label="Strategy" value={learning?.strategy || "--"} />
                <DataPlate label="Project" value={conversationId ? "ACTIVE" : "IDLE"} />
                <DataPlate label="CAL" value="07-2026" />
              </div>
            </div>
          </PanelFrame>

          <PanelFrame
            title="Evidence"
            accent="amber"
            size="major"
            subtitle="Declared, configured, observed, verified, unknown"
            serial="BZ-002 // EV"
            live={runtime.toolResults.length > 0}
            blink={Boolean(runtime.busPulse.toolResults)}
            throughput={evidenceVerifiedPct}
            flow={evidenceFlowPct}
            signalTone="amber"
            pattern={evidencePanelPattern}
            cadence={evidenceCadence}
            band={evidenceBand}
            sparkValues={panelHistory.evidence}
          >
            <EvidenceStack results={runtime.toolResults} />
            <MeterStack
              values={[
                { label: "VER", value: evidenceVerifiedPct },
                { label: "OBS", value: ratioPct(evidenceCandidates.length - verifiedEvidence, evidenceCandidates.length || 1) },
                { label: "CFG", value: ratioPct(runtime.tools.length, 5) },
              ]}
            />
            <div className="plate-row compact">
              <CircularGauge label="Verification Ratio" value={evidenceVerifiedPct} />
              <div className="list-stack">
                <DataPlate label="Verified" value={verifiedEvidence} />
                <DataPlate label="Total Evidence" value={evidenceCandidates.length} />
                <DataPlate label="Freshness" value={fmtTime(lastToolResult?.completed_at)} />
              </div>
            </div>
            <div className="provenance-line">Latest provenance: {lastToolResult?.tool_name || "--"}</div>
          </PanelFrame>

          <PanelFrame
            title="Reasoning"
            accent="orange"
            subtitle="Conflict and uncertainty monitor"
            serial="BZ-003 // RSN"
            live={Boolean(runtime.reasoning || confidence)}
            blink={Boolean(runtime.busPulse.reasoning)}
            throughput={reasoningConfidencePct}
            flow={reasoningFlowPct}
            signalTone="orange"
            pattern={reasoningPanelPattern}
            cadence={reasoningCadence}
            band={reasoningBand}
            sparkValues={panelHistory.reasoning}
          >
            <div className="plate-row">
              <RadarDisplay value={Math.min(100, Number(confidence?.reflection_score || 0) * 100)} />
              <div className="list-stack">
                <DataPlate label="Uncertainty" value={runtime.reasoning?.uncertainty_count || 0} />
                <DataPlate label="Conflicts" value={runtime.reasoning?.conflict_count || 0} />
                <DataPlate label="Confidence" value={confidence?.reflection_score ?? "--"} />
              </div>
            </div>
            <ScopeTrace value={Math.min(100, Number(confidence?.reflection_score || 0) * 100)} />
          </PanelFrame>
        </aside>

        <section className="conversation-console">
          <PanelFrame
            title="Command Channel"
            accent="steel"
            size="major"
            subtitle="Primary communications channel"
            serial="BZ-COMM // MK-II"
            live={consoleLive}
            blink={Boolean(isStreaming || scanBurst)}
            throughput={commandThroughputPct}
            flow={telemetryHealthPct}
            signalTone="green"
            pattern={commandPanelPattern}
            cadence={commandCadence}
            band={commandBand}
            sparkValues={panelHistory.command}
          >
            <div className="console-status">
              <SystemBadge label="Status" value={status} />
              <SystemBadge label="Session" value={conversationId || "NONE"} />
              <SystemBadge label="Streaming" value={isStreaming ? "ACTIVE" : "IDLE"} />
            </div>
            <div className={`comm-plates ${consoleLive ? "is-live" : ""}`}>
              <small>COMM CHANNEL // BZ-COMM-01</small>
              <small>SYNC {runtime.telemetry.endpoint_up}/{runtime.telemetry.endpoint_total} // LAT {runtime.telemetry.poll_ms}ms // CRC OK</small>
            </div>
            <div className={`conversation-mode ${conversationMode === "direct" ? "is-direct" : ""}`}>
              <div className="conversation-mode-buttons" role="group" aria-label="Conversation mode">
                <button
                  className={conversationMode === "runtime" ? "is-active" : ""}
                  onClick={() => setConversationMode("runtime")}
                  disabled={isStreaming}
                >
                  Runtime
                </button>
                <button
                  className={conversationMode === "direct" ? "is-active" : ""}
                  onClick={() => setConversationMode("direct")}
                  disabled={isStreaming}
                >
                  Direct Model
                </button>
              </div>
              <small>
                {conversationMode === "direct"
                  ? `PINNED ${DIRECT_MODEL} // RAW HISTORY + INPUT // NO PROMPT, MEMORY, WEB, COGNITION, REASONING, PLANNING, OR LEARNING`
                  : "OMEGA-ARC RUNTIME // DETERMINISTIC SUBSYSTEMS ACTIVE"}
              </small>
            </div>
            <div className="console-buttons console-buttons-live">
              <button onClick={createConversation}>Create Conversation</button>
            </div>
            <div className={`chat-window ${isStreaming ? "is-streaming" : ""}`}>
              {messages.length === 0 ? <div className="empty">NO TRANSMISSIONS YET.</div> : null}
              {messages.map((m, i) => (
                <div key={i} className={`chat-msg ${m.role === "USER" ? "user" : "assistant"}`}>
                  <div className="role">{m.role}</div>
                  <div className="content">{m.content}</div>
                </div>
              ))}
            </div>
            <div className="command-line">&gt;</div>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="ENTER TRANSMISSION..." />
            <div className="console-buttons">
              <button onClick={sendMessage} disabled={isStreaming}>Send</button>
              <button onClick={streamMessage} disabled={isStreaming}>Stream</button>
            </div>
            <div className="memory-search">
              <input value={memoryQuery} onChange={(e) => setMemoryQuery(e.target.value)} placeholder="QUERY MEMORY INDEX..." />
              <button onClick={searchMemory}>Search</button>
            </div>
            <div className="memory-results">
              {memoryResults.slice(0, 4).map((m, i) => (
                <div key={i} className="memory-item">
                  <strong>{m.kind}</strong>
                  <p>{m.summary_text}</p>
                </div>
              ))}
            </div>
          </PanelFrame>
        </section>

        <aside className="right-bank">
          <PanelFrame
            title="Planning"
            accent="green"
            size="major"
            subtitle="Current plan, active step, blockers"
            serial="BZ-004 // PLN"
            live={Boolean(activePlan)}
            blink={Boolean(runtime.busPulse.plans)}
            throughput={planningProgressPct}
            flow={planningFlowPct}
            signalTone="green"
            pattern={planningPanelPattern}
            cadence={planningCadence}
            band={planningBand}
            sparkValues={panelHistory.planning}
          >
            <div className="plate-row compact">
              <CircularGauge label="Completion" value={planningProgressPct} />
              <div className="list-stack">
                <DataPlate label="Current Plan" value={activePlan?.title || activePlan?.plan_id || "--"} />
                <DataPlate label="Next Action" value={runtime.reasoning?.next_action || "--"} />
                <DataPlate label="Blockers" value={activePlan?.blockers?.length || 0} />
              </div>
            </div>
            <SegmentMeter segments={5} active={Math.min(5, Math.max(0, activePlan?.progress_segments || 1))} />
            <div className="engrave">ACCESS PANEL // DO NOT REMOVE // REV MK-II</div>
          </PanelFrame>

          <PanelFrame
            title="Deliberation"
            accent="violet"
            subtitle="Recommendation, alternatives, approval state"
            serial="BZ-005 // DLB"
            live={Boolean(runtime.decisions?.length || approvedPending)}
            blink={Boolean(runtime.busPulse.decisions || approvedPending > 0)}
            throughput={deliberationPressurePct}
            flow={ratioPct(runtime.decisions?.length || 0, 6)}
            signalTone="violet"
            pattern={deliberationPanelPattern}
            cadence={deliberationCadence}
            band={deliberationBand}
            sparkValues={panelHistory.deliberation}
          >
            <DataPlate label="Recommendation" value={runtime.decisions?.[0]?.decision || "--"} />
            <DataPlate label="Alternatives" value={runtime.decisions?.length || 0} />
            <DataPlate label="Approval Queue" value={approvedPending} />
            <SignalBar value={Math.min(100, approvedPending * 25)} />
          </PanelFrame>

          <PanelFrame
            title="Trusted Adapters"
            accent="white"
            subtitle="ID, status, approval, duration, evidence"
            serial="BZ-006 // ADP"
            live={runtime.tools.length > 0}
            blink={Boolean(runtime.busPulse.tools || runtime.busPulse.toolResults)}
            throughput={adapterReadyPct}
            flow={adapterFlowPct}
            signalTone="white"
            pattern={adaptersPanelPattern}
            cadence={adaptersCadence}
            band={adaptersBand}
            sparkValues={panelHistory.adapters}
          >
            <div className="plate-row compact">
              <CircularGauge label="Utilization" value={adapterReadyPct} />
              <div className="list-stack">
                <DataPlate label="Enabled" value={runtime.tools.filter((t) => t?.enabled).length} />
                <DataPlate label="Registered" value={runtime.tools.length} />
                <DataPlate label="Last Run" value={fmtTime(lastToolResult?.completed_at)} />
              </div>
            </div>
            <div className="adapter-list">
              {runtime.tools.map((tool) => (
                <AdapterTile
                  key={tool.name}
                  descriptor={tool}
                  lastRequest={[...runtime.toolRequests].reverse().find((r) => r.tool_name === tool.name)}
                  lastResult={[...runtime.toolResults].reverse().find((r) => r.tool_name === tool.name)}
                />
              ))}
              {!runtime.tools.length ? <div className="empty">NO ADAPTER DATA.</div> : null}
            </div>
            <div className="engrave">SERIAL 1143-22 // CAL OK</div>
          </PanelFrame>
        </aside>
      </main>

      <section className="lower-strip">
        <PanelFrame
          title="Operations Strip"
          accent="steel"
          size="major"
          subtitle="Current plan, approvals, verified evidence, execution timeline"
          serial="BZ-OPS // LIVE"
          live={consoleLive}
          blink={Boolean(scanBurst || runtime.busPulse.toolResults)}
          throughput={telemetryHealthPct}
          flow={operationsFlowPct}
          signalTone="cyan"
          pattern={opsPanelPattern}
          cadence={operationsCadence}
          band={operationsBand}
          sparkValues={panelHistory.operations}
        >
          <div className="ops-grid">
            <DataPlate label="Current Plan" value={activePlan?.title || "--"} />
            <DataPlate label="Next Action" value={runtime.reasoning?.next_action || "--"} />
            <DataPlate label="Approvals Pending" value={approvedPending} />
            <DataPlate label="Latest Verified" value={lastToolResult?.evidence_candidates?.[0]?.key || "--"} />
            <DataPlate label="Telemetry" value={coreRuntimeState} />
            <DataPlate label="Last Update" value={fmtTime(runtime.telemetry.last_poll_at)} />
          </div>
          <div className={`timeline ${consoleLive ? "is-live" : ""}`}>
            {[...runtime.toolResults].slice(-6).reverse().map((r, i) => (
              <div className="timeline-row" key={i}>
                <span>{fmtTime(r.completed_at || r.started_at)}</span>
                <strong>{r.tool_name}</strong>
                <span>{String(r.status || "--").toUpperCase()}</span>
                <span>{r.duration_ms ? `${Number(r.duration_ms).toFixed(1)} ms` : "--"}</span>
              </div>
            ))}
          </div>
        </PanelFrame>
        <ChroniclePlate lastResult={lastToolResult} />
      </section>

      <footer className="translator-strip">
        <span>SUBSYSTEM CODES // WHSPR-BRIDG-MIRR-GUIDE-SILNC</span>
        <span>MEMORY HITS {liveMemoryHits.length} // WEB HITS {webHits.length}</span>
      </footer>

      <section className="translator-drawer">
        <button className="translator-toggle" onClick={() => setTranslatorOpen((v) => !v)}>
          {translatorOpen ? "Hide Galactic Basic Encoder" : "Show Galactic Basic Encoder"}
        </button>
        {translatorOpen ? (
          <div className="translator-panel">
            <div className="translator-shell">
              <div className="translator-labels">
                <small>GALACTIC BASIC ENCODER // DECORATIVE SUBSYSTEM INSERT</small>
                <strong>ENGLISH REMAINS AUTHORITATIVE</strong>
              </div>
              <div className="translator-status">MODULE LOCKED TO DISPLAY ONLY</div>
              <button className="translator-live" onClick={captureLiveTranslator}>Live Bridge</button>
            </div>
            <textarea
              className="translator-input"
              value={translatorInput}
              onChange={(e) => setTranslatorInput(e.target.value.toUpperCase())}
              placeholder="TYPE BASIC HERE..."
            />
            <div className="translator-rows">
              <div>
                <span>English Source</span>
                <strong>{translatorSource}</strong>
              </div>
              <div>
                <span>Glyph Line</span>
                <strong className="aurebesh">{translatorOutput || "--"}</strong>
              </div>
            </div>
            <div className="translator-footer">NON-TRANSCRIBING VISUAL CHANNEL // NO COMMAND PRIVILEGES</div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
