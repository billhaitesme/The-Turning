// OMEGA-ARC Bridge Zero — the web console, rebuilt as a widget deck (XIII-A).
// Every panel is a card: drag to reorder (grip), collapse, resize, or stow to the dock. The
// layout is the operator's and persists locally; authority stays with the runtime. The chat
// pops out into a companion window (?companion=1) sharing the same conversation.
import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import {
  ActivityRibbon, AdapterTile, AnnunciatorStack, ChroniclePlate, CircularGauge, CognitiveBus,
  DataPlate, EvidenceStack, HardwareControlDeck, MeterStack, PanelFrame, RadarDisplay, ScopeTrace,
  SegmentMeter, SignalArray, SignalBar, StatusLamp, SystemBadge, cadenceBand, fmtTime, setHostClock,
  panelPattern, phaseLabel, playTone, pushHistory, ratioPct, statusFromError,
  toAurebeshGlyphText, tunedCadence,
} from "./components/displays.jsx";
import { ChatConsoleView, useChatChannel, ASSISTANT_NAME, API_BASE } from "./components/ChatConsole.jsx";
import CommandDeck from "./components/CommandDeck.jsx";
import { WIDGET_DEFS, WIDTH_CYCLE, loadDeck, saveDeck, widgetTitle } from "./deck.js";

const BOOT_SEQUENCE = [
  { label: "CORE IGNITION", delay: 420 },
  { label: "SENSOR CALIBRATION", delay: 520 },
  { label: "BUS LINK", delay: 540 },
  { label: "READY", delay: 480 },
];

const IS_COMPANION = new URLSearchParams(window.location.search).has("companion");

export default function App() {
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
  const [translatorOpen, setTranslatorOpen] = useState(true);
  const [translatorInput, setTranslatorInput] = useState("STANDBY NO ACTIVE PHASE BRIDGE");
  const [deck, setDeck] = useState(() => loadDeck());
  const [dragArmed, setDragArmed] = useState("");
  const [dragOver, setDragOver] = useState("");
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

  const chat = useChatChannel({
    playCue: playAudioCue,
    onPhase: () => setLastCognitiveActivityAt(Date.now()),
  });
  const {
    messages, conversationId, learning, confidence, liveMemoryHits, webHits,
    currentPhase, isStreaming, status,
  } = chat;

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
      endpoint_total: 8,
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
    if (IS_COMPANION) return undefined; // the companion leaves telemetry polling to the bridge
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
        ["deliberation", `${API_BASE}/system/deliberation`],
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
      setHostClock(nextData.systemStatus?.host_clock);
      setRuntime((prev) => ({
        ...prev,
        systemStatus: nextData.systemStatus || prev.systemStatus,
        tools: nextData.tools?.tools || prev.tools,
        plans: nextData.plans?.plans || prev.plans,
        decisions: nextData.decisions?.decisions || prev.decisions,
        reasoning: nextData.reasoning?.reasoning || nextData.reasoning || prev.reasoning,
        deliberation: nextData.deliberation?.deliberation || prev.deliberation,
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

  function captureLiveTranslator() {
    setTranslatorInput(`${status} ${phaseLabel(currentPhase)} ${runtime.systemStatus?.version || "BRIDGE"}`.toUpperCase());
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

  // ------------------------------------------------------------------ deck actions
  function updateDeck(mutator) {
    setDeck((prev) => {
      const next = mutator(structuredClone(prev));
      saveDeck(next);
      return next;
    });
  }

  function setWidgetState(id, patch) {
    updateDeck((d) => {
      d.state[id] = { ...d.state[id], ...patch };
      return d;
    });
  }

  function moveWidget(sourceId, targetId) {
    if (!sourceId || sourceId === targetId) return;
    updateDeck((d) => {
      const order = d.order.filter((x) => x !== sourceId);
      const at = order.indexOf(targetId);
      order.splice(at < 0 ? order.length : at, 0, sourceId);
      d.order = order;
      return d;
    });
  }

  function resetDeck() {
    updateDeck(() => {
      const base = loadDeck();
      window.localStorage.removeItem("omega-arc.deck.v1");
      return (function fresh() {
        const d = { order: WIDGET_DEFS.map((w) => w.id), state: {} };
        for (const w of WIDGET_DEFS) {
          d.state[w.id] = { width: w.width || "third", collapsed: Boolean(w.collapsed), hidden: Boolean(w.hidden) };
        }
        return d;
      })() || base;
    });
    playAudioCue("navigation");
  }

  function openCompanion() {
    playAudioCue("navigation");
    window.open(
      `${window.location.pathname}?companion=1`,
      "omega-arc-companion",
      "width=520,height=760,menubar=no,toolbar=no,location=no,status=no"
    );
  }

  const lastToolResult = runtime.toolResults?.[runtime.toolResults.length - 1] || null;
  const activePlan = runtime.plans?.find?.((p) => p?.status === "active") || runtime.plans?.[0] || null;
  const deliberationRecords = runtime.deliberation?.records || [];
  const latestDeliberation = deliberationRecords[deliberationRecords.length - 1];
  const evidenceBeliefs = runtime.reasoning?.resolved_beliefs || [];
  const evidenceCandidates = evidenceBeliefs.length
    ? evidenceBeliefs
    : runtime.toolResults.flatMap((r) => r?.evidence_candidates || []);
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
  const translatorSource = translatorInput || `${status} ${phaseLabel(currentPhase)} BRIDGE`;
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
  const activeSeat = runtime.systemStatus?.model_control?.active_model || "--";
  const agentLoopOn = Boolean(runtime.systemStatus?.agent_loop_enabled);

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

  // ------------------------------------------------------------------ companion window
  if (IS_COMPANION) {
    return (
      <div className="bridge-app companion-app">
        <header className="companion-header">
          <div>
            <h1>OMEGA-ARC</h1>
            <small>COMPANION CHANNEL // SHARED SESSION</small>
          </div>
          <StatusLamp status={isStreaming ? "STREAMING" : conversationId ? "LINKED" : "STANDBY"} pulse={isStreaming} />
        </header>
        <PanelFrame
          title="Command Channel"
          accent="steel"
          size="major"
          serial="BZ-COMM // CMP"
          live={Boolean(conversationId)}
          blink={isStreaming}
          throughput={commandThroughputPct}
          flow={identityFlowPct}
          signalTone="green"
          pattern={commandPanelPattern}
          cadence={commandCadence}
          band={commandBand}
        >
          <ChatConsoleView chat={chat} compact />
        </PanelFrame>
      </div>
    );
  }

  // ------------------------------------------------------------------ widget renderers
  const deckControlsFor = (id) => {
    const s = deck.state[id] || {};
    return (
      <div className="deck-controls" onMouseDown={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="deck-grip"
          title="Drag to reorder"
          onMouseDown={() => setDragArmed(id)}
        >
          ⠿
        </button>
        <button type="button" title="Cycle width" onClick={() => setWidgetState(id, { width: WIDTH_CYCLE[s.width] || "third" })}>⇔</button>
        <button type="button" title={s.collapsed ? "Expand" : "Collapse"} onClick={() => setWidgetState(id, { collapsed: !s.collapsed })}>{s.collapsed ? "▸" : "▾"}</button>
        {id === "chat" ? (
          <button type="button" title="Open companion window" onClick={openCompanion}>⧉</button>
        ) : null}
        <button type="button" title="Stow to dock" onClick={() => setWidgetState(id, { hidden: true })}>✕</button>
      </div>
    );
  };

  const widgetRender = {
    chat: (s) => (
      <PanelFrame
        title="Command Channel" accent="steel" size="major" subtitle="Primary communications channel"
        serial="BZ-COMM // MK-II" live={consoleLive} blink={Boolean(isStreaming || scanBurst)}
        throughput={commandThroughputPct} flow={telemetryHealthPct} signalTone="green"
        pattern={commandPanelPattern} cadence={commandCadence} band={commandBand}
        sparkValues={panelHistory.command} collapsed={s.collapsed} deckControls={deckControlsFor("chat")}
      >
        <ChatConsoleView chat={chat} telemetry={runtime.telemetry} onPopout={openCompanion} />
      </PanelFrame>
    ),
    commands: (s) => (
      <PanelFrame
        title="Command Registry" accent="white" subtitle="Quick requests, gated commands, history"
        serial="BZ-CMD // REG" live blink={approvedPending > 0}
        throughput={ratioPct(runtime.tools.filter((t) => t?.enabled).length, runtime.tools.length || 1)}
        flow={Math.min(100, approvedPending * 25)} signalTone="white"
        pattern={approvedPending > 0 ? "wait" : "idle"} cadence={deliberationCadence} band={deliberationBand}
        sparkValues={panelHistory.adapters} collapsed={s.collapsed} deckControls={deckControlsFor("commands")}
      >
        <CommandDeck playCue={playAudioCue} />
      </PanelFrame>
    ),
    identity: (s) => (
      <PanelFrame
        title="Identity" accent="cyan" subtitle="Fact count, confidence, active project" serial="BZ-001 // ID"
        live={Boolean(conversationId || learning)} blink={Boolean(runtime.busPulse.reasoning || currentPhase !== "none")}
        throughput={identitySignalPct} flow={identityFlowPct} signalTone="cyan"
        pattern={identityPanelPattern} cadence={identityCadence} band={identityBand}
        sparkValues={panelHistory.identity} collapsed={s.collapsed} deckControls={deckControlsFor("identity")}
      >
        <div className="plate-row">
          <CircularGauge label="Identity Confidence" value={Number(learning?.reflection_score || 0) * 100} />
          <div className="list-stack">
            <DataPlate label="Style" value={learning?.style || "--"} />
            <DataPlate label="Strategy" value={learning?.strategy || "--"} />
            <DataPlate label="Project" value={conversationId ? "ACTIVE" : "IDLE"} />
            <DataPlate label="Seat" value={activeSeat} />
          </div>
        </div>
      </PanelFrame>
    ),
    evidence: (s) => (
      <PanelFrame
        title="Evidence" accent="amber" subtitle="Declared, configured, observed, verified, unknown"
        serial="BZ-002 // EV" live={runtime.toolResults.length > 0} blink={Boolean(runtime.busPulse.toolResults)}
        throughput={evidenceVerifiedPct} flow={evidenceFlowPct} signalTone="amber"
        pattern={evidencePanelPattern} cadence={evidenceCadence} band={evidenceBand}
        sparkValues={panelHistory.evidence} collapsed={s.collapsed} deckControls={deckControlsFor("evidence")}
      >
        <EvidenceStack candidates={evidenceCandidates} />
        <MeterStack
          values={[
            { label: "VER", value: evidenceVerifiedPct },
            { label: "OBS", value: ratioPct(evidenceCandidates.length - verifiedEvidence, evidenceCandidates.length || 1) },
            { label: "CFG", value: ratioPct(runtime.tools.length, 6) },
          ]}
        />
        <div className="provenance-line">Latest provenance: {lastToolResult?.tool_name || "--"}</div>
      </PanelFrame>
    ),
    reasoning: (s) => (
      <PanelFrame
        title="Reasoning" accent="orange" subtitle="Conflict and uncertainty monitor" serial="BZ-003 // RSN"
        live={Boolean(runtime.reasoning || confidence)} blink={Boolean(runtime.busPulse.reasoning)}
        throughput={reasoningConfidencePct} flow={reasoningFlowPct} signalTone="orange"
        pattern={reasoningPanelPattern} cadence={reasoningCadence} band={reasoningBand}
        sparkValues={panelHistory.reasoning} collapsed={s.collapsed} deckControls={deckControlsFor("reasoning")}
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
    ),
    planning: (s) => (
      <PanelFrame
        title="Planning" accent="green" subtitle="Current plan, active step, blockers" serial="BZ-004 // PLN"
        live={Boolean(activePlan)} blink={Boolean(runtime.busPulse.plans)}
        throughput={planningProgressPct} flow={planningFlowPct} signalTone="green"
        pattern={planningPanelPattern} cadence={planningCadence} band={planningBand}
        sparkValues={panelHistory.planning} collapsed={s.collapsed} deckControls={deckControlsFor("planning")}
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
      </PanelFrame>
    ),
    deliberation: (s) => (
      <PanelFrame
        title="Deliberation" accent="violet" subtitle="Recommendation, alternatives, approval state" serial="BZ-005 // DLB"
        live={Boolean(runtime.decisions?.length || approvedPending)} blink={Boolean(runtime.busPulse.decisions || approvedPending > 0)}
        throughput={deliberationPressurePct} flow={ratioPct(runtime.decisions?.length || 0, 6)} signalTone="violet"
        pattern={deliberationPanelPattern} cadence={deliberationCadence} band={deliberationBand}
        sparkValues={panelHistory.deliberation} collapsed={s.collapsed} deckControls={deckControlsFor("deliberation")}
      >
        <DataPlate label="Recommendation" value={runtime.decisions?.[0]?.decision || latestDeliberation?.recommendation?.plan_id || "--"} />
        <DataPlate label="Alternatives" value={latestDeliberation?.candidate_plans?.length || runtime.decisions?.length || 0} />
        <DataPlate label="Approval Queue" value={approvedPending} />
        <SignalBar value={Math.min(100, approvedPending * 25)} />
      </PanelFrame>
    ),
    adapters: (s) => (
      <PanelFrame
        title="Trusted Adapters" accent="white" subtitle="ID, status, approval, duration, evidence" serial="BZ-006 // ADP"
        live={runtime.tools.length > 0} blink={Boolean(runtime.busPulse.tools || runtime.busPulse.toolResults)}
        throughput={adapterReadyPct} flow={adapterFlowPct} signalTone="white"
        pattern={adaptersPanelPattern} cadence={adaptersCadence} band={adaptersBand}
        sparkValues={panelHistory.adapters} collapsed={s.collapsed} deckControls={deckControlsFor("adapters")}
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
          {runtime.tools.map((tool, index) => (
            <AdapterTile
              key={tool.name}
              adapterId={`A-${String(index + 1).padStart(3, "0")}`}
              descriptor={tool}
              lastRequest={[...runtime.toolRequests].reverse().find((r) => r.tool_name === tool.name)}
              lastResult={[...runtime.toolResults].reverse().find((r) => r.tool_name === tool.name)}
            />
          ))}
          {!runtime.tools.length ? <div className="empty">NO ADAPTER DATA.</div> : null}
        </div>
      </PanelFrame>
    ),
    bus: () => (
      <CognitiveBus items={busItems} pulseIndex={busPulseIndex} cognitiveStage={cognitiveStage} silenceMode={silenceMode} />
    ),
    signal: () => (
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
    ),
    operations: (s) => (
      <PanelFrame
        title="Operations Strip" accent="steel" size="major" subtitle="Plan, approvals, verified evidence, execution timeline"
        serial="BZ-OPS // LIVE" live={consoleLive} blink={Boolean(scanBurst || runtime.busPulse.toolResults)}
        throughput={telemetryHealthPct} flow={operationsFlowPct} signalTone="cyan"
        pattern={opsPanelPattern} cadence={operationsCadence} band={operationsBand}
        sparkValues={panelHistory.operations} collapsed={s.collapsed} deckControls={deckControlsFor("operations")}
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
    ),
    chronicle: () => <ChroniclePlate lastResult={lastToolResult} />,
    encoder: (s) => (
      <PanelFrame
        title="Galactic Basic Encoder" accent="steel" subtitle="Decorative subsystem insert" serial="BZ-ENC // GB"
        live={false} collapsed={s.collapsed} deckControls={deckControlsFor("encoder")}
      >
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
      </PanelFrame>
    ),
  };

  const visibleWidgets = deck.order.filter((id) => widgetRender[id] && !deck.state[id]?.hidden);
  const stowedWidgets = deck.order.filter((id) => widgetRender[id] && deck.state[id]?.hidden);

  return (
    <div
      className={`bridge-app mode-${surfaceMode} ${panelLocked ? "panel-locked" : ""} ${motionClass} ${silenceMode ? "is-silence" : ""}`}
      style={{ "--gain-level": String(Math.max(0, Math.min(100, gain)) / 100) }}
    >
      <header className="command-header">
        <div className="identity-plate">
          <h1>OMEGA-ARC</h1>
          <h2>BRIDGE ZERO</h2>
          <div className="epoch-line">EPOCH XIII // AGENCY DECK</div>
          <StatusLamp status={bootReady ? (coreRuntimeState === "OPERATIONAL" ? "OPERATIONAL" : "WARNING") : "BOOTING"} pulse={!!runtime.busPulse.systemStatus || scanBurst || !bootReady} />
        </div>
        <div className="build-plate">
          <SystemBadge label="Core Runtime" value={coreRuntimeState} />
          <SystemBadge label="Power State" value={powerState} />
          <SystemBadge label="Phase" value={phaseLabel(currentPhase)} />
          <SystemBadge label="Build" value={runtime.systemStatus?.version || "--"} />
          <SystemBadge label="Seat" value={activeSeat} />
          <SystemBadge label="Agent Loop" value={agentLoopOn ? "ON" : "OFF"} />
          <SystemBadge label="Senses" value={runtime.systemStatus?.network_breaker_on ? "LIVE" : "DARK"} />
          <SystemBadge label="Adapters" value={runtime.tools.length} />
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

      <div className="deck-dock">
        <small>DECK CONFIG // DRAG ⠿ TO REORDER // LAYOUT IS YOURS</small>
        <div className="deck-dock-items">
          {stowedWidgets.map((id) => (
            <button key={id} type="button" className="dock-chip" onClick={() => setWidgetState(id, { hidden: false })}>
              + {widgetTitle(id).toUpperCase()}
            </button>
          ))}
          {!stowedWidgets.length ? <span className="dock-empty">ALL PANELS DEPLOYED</span> : null}
          <button type="button" className="dock-reset" onClick={resetDeck}>RESET LAYOUT</button>
        </div>
      </div>

      <main className="widget-deck">
        {visibleWidgets.map((id) => {
          const s = deck.state[id] || { width: "third" };
          return (
            <div
              key={id}
              className={`deck-cell w-${s.width} ${dragOver === id ? "drag-over" : ""} ${dragArmed === id ? "drag-armed" : ""}`}
              draggable={dragArmed === id}
              onDragStart={(e) => {
                e.dataTransfer.setData("text/widget", id);
                e.dataTransfer.effectAllowed = "move";
              }}
              onDragEnd={() => {
                setDragArmed("");
                setDragOver("");
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(id);
              }}
              onDragLeave={() => setDragOver((prev) => (prev === id ? "" : prev))}
              onDrop={(e) => {
                e.preventDefault();
                const sourceId = e.dataTransfer.getData("text/widget");
                moveWidget(sourceId, id);
                setDragArmed("");
                setDragOver("");
                playAudioCue("navigation");
              }}
            >
              {widgetRender[id](s)}
            </div>
          );
        })}
      </main>

      <footer className="translator-strip">
        <span>SUBSYSTEM CODES // WHSPR-BRIDG-MIRR-GUIDE-SILNC</span>
        <span>MEMORY HITS {liveMemoryHits.length} // WEB HITS {webHits.length}</span>
      </footer>
    </div>
  );
}
