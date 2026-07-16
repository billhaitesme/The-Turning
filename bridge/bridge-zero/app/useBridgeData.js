import { useEffect, useMemo, useState } from "react";
import { chronicleTimeline, epochRecords } from "../chronicle/chronicleData";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001";
const BASE_POLL_MS = 2500;
const MAX_BACKOFF_MS = 20000;

function nowIso() {
  return new Date().toISOString();
}

function hashOf(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function inferSubsystemState(connected, stale, hasWarnings = false) {
  if (!connected) return "OFFLINE";
  if (stale) return "WARNING";
  if (hasWarnings) return "WARNING";
  return "READY";
}

export function useBridgeData() {
  const [conversation, setConversation] = useState({
    state: "INITIALIZING",
    messages: [{ role: "SYSTEM", content: "Initializing Bridge Zero polling bus." }],
  });
  const [identity, setIdentity] = useState({ state: "INITIALIZING", user: "operator", project: "unknown", session: "live", confidence: 0, activity_at: null });
  const [evidence, setEvidence] = useState({ state: "INITIALIZING", counts: { declared: 0, configured: 0, observed: 0, verified: 0, unknown: 0 }, indicators: [], activity_at: null });
  const [reasoning, setReasoning] = useState({ state: "INITIALIZING", confidence: 0, inferences: [], assumptions: [], activity_at: null });
  const [planning, setPlanning] = useState({ state: "INITIALIZING", activeGoal: "none", nextAction: "none", steps: [], activity_at: null });
  const [deliberation, setDeliberation] = useState({ state: "INITIALIZING", recommendation: "none", approvalState: "pending", alternatives: [], activity_at: null });
  const [tools, setTools] = useState({ state: "INITIALIZING", tools: [], currentActivity: "idle", executionEnabled: false, timeline: [], last_poll_at: null, activity_at: null });

  const [connection, setConnection] = useState({
    state: "INITIALIZING",
    lastSuccessfulPollAt: null,
    lastAttemptAt: null,
    stale: false,
    pollIntervalMs: BASE_POLL_MS,
    failureCount: 0,
    message: "Initializing",
  });

  const [activityMap, setActivityMap] = useState({
    identity: null,
    evidence: null,
    reasoning: null,
    planning: null,
    deliberation: null,
    tools: null,
  });

  const [busActive, setBusActive] = useState("identity");
  const [selectedChronicle, setSelectedChronicle] = useState("Tools");

  useEffect(() => {
    let disposed = false;
    let timeoutId = null;
    let failureCount = 0;
    let currentInterval = BASE_POLL_MS;
    let lastSuccessfulPollAt = null;
    const previousHashes = {
      identity: "",
      evidence: "",
      reasoning: "",
      planning: "",
      deliberation: "",
      tools: "",
    };

    const activateBus = (subsystem) => {
      setBusActive(subsystem);
      setTimeout(() => {
        if (!disposed) {
          const order = ["identity", "evidence", "reasoning", "planning", "deliberation", "tools"];
          setBusActive(order[Math.floor(Date.now() / 1500) % order.length]);
        }
      }, 500);
    };

    const markActivityIfChanged = (subsystem, payload) => {
      const hash = hashOf(payload);
      if (previousHashes[subsystem] !== hash) {
        previousHashes[subsystem] = hash;
        const stamp = nowIso();
        setActivityMap((prev) => ({ ...prev, [subsystem]: stamp }));
        activateBus(subsystem);
        return true;
      }
      return false;
    };

    const scheduleNext = () => {
      if (disposed) return;
      timeoutId = setTimeout(pollOnce, currentInterval);
    };

    const staleFrom = () => {
      if (!lastSuccessfulPollAt) return true;
      const delta = Date.now() - new Date(lastSuccessfulPollAt).getTime();
      return delta > Math.max(7000, currentInterval * 2);
    };

    const buildToolTimeline = (toolsPayload, decisionsPayload) => {
      const entries = [];
      const toolsList = toolsPayload?.tools || [];
      const activeTools = toolsList.filter((item) => item && item.enabled).length;
      entries.push(`${nowIso()} | tools polled: ${toolsList.length} registered, ${activeTools} enabled`);

      const decisions = decisionsPayload?.decisions || [];
      const toolDecisions = decisions.filter((item) => {
        const text = `${item?.title || ""} ${item?.decision_text || ""}`.toLowerCase();
        return text.includes("tool") || text.includes("adapter") || text.includes("approval");
      });
      toolDecisions.slice(0, 3).forEach((item) => {
        entries.push(`${item.updated_at || item.created_at || nowIso()} | decision: ${item.title || item.id}`);
      });

      return entries.slice(0, 8);
    };

    const pollOnce = async () => {
      const attemptAt = nowIso();
      if (!disposed) {
        setConnection((prev) => ({
          ...prev,
          state: prev.lastSuccessfulPollAt ? "POLLING" : "INITIALIZING",
          lastAttemptAt: attemptAt,
          pollIntervalMs: currentInterval,
          failureCount,
        }));
      }

      const calls = await Promise.allSettled([
        fetch(`${API_BASE}/system/status`),
        fetch(`${API_BASE}/system/tools`),
        fetch(`${API_BASE}/system/plans`),
        fetch(`${API_BASE}/system/decisions`),
        fetch(`${API_BASE}/system/reasoning`),
      ]);

      const toJson = async (settled) => {
        if (settled.status !== "fulfilled") return { ok: false, payload: null };
        if (!settled.value.ok) return { ok: false, payload: null };
        try {
          return { ok: true, payload: await settled.value.json() };
        } catch {
          return { ok: false, payload: null };
        }
      };

      const [statusRes, toolsRes, plansRes, decisionsRes, reasoningRes] = await Promise.all(calls.map(toJson));
      const coreSuccess = toolsRes.ok && plansRes.ok && decisionsRes.ok && reasoningRes.ok;

      if (!coreSuccess) {
        failureCount += 1;
        currentInterval = Math.min(MAX_BACKOFF_MS, BASE_POLL_MS * Math.pow(2, failureCount));
        const stale = staleFrom();

        if (!disposed) {
          setConnection((prev) => ({
            ...prev,
            state: prev.lastSuccessfulPollAt ? "DEGRADED" : "OFFLINE",
            stale,
            pollIntervalMs: currentInterval,
            failureCount,
            message: "Polling failed. Retrying with backoff.",
            lastAttemptAt: attemptAt,
          }));
          setConversation((prev) => ({
            ...prev,
            state: prev.messages.length > 0 ? "WARNING" : "OFFLINE",
            messages: [
              { role: "SYSTEM", content: "Live backend polling unavailable. Bridge Zero is in graceful offline mode." },
            ],
            activity_at: nowIso(),
          }));
        }

        scheduleNext();
        return;
      }

      failureCount = 0;
      currentInterval = BASE_POLL_MS;
      const now = nowIso();
      lastSuccessfulPollAt = now;
      const stale = false;

      const statusPayload = statusRes.payload || {};
      const toolsPayload = toolsRes.payload || {};
      const plansPayload = plansRes.payload || {};
      const decisionsPayload = decisionsRes.payload || {};
      const reasoningPayload = reasoningRes.payload || {};

      const plans = plansPayload.plans || [];
      const activePlan = plans.find((item) => String(item.status || "").toLowerCase() === "active") || plans[0] || null;
      const nextStep = activePlan
        ? (activePlan.steps || []).find((item) => ["active", "ready", "pending"].includes(String(item.status || "").toLowerCase()))
        : null;

      const reasoningCore = reasoningPayload.reasoning || {};
      const confidence = Math.round(Number(reasoningCore.confidence || 0) * 100);
      const inferences = Array.isArray(reasoningCore.inferences) ? reasoningCore.inferences : ["No active inference payload."];

      const decisions = decisionsPayload.decisions || [];
      const approvalDecision = decisions.find((item) => String(item.title || "").toLowerCase().includes("approved"));

      const toolTimeline = buildToolTimeline(toolsPayload, decisionsPayload);
      const connected = true;

      const identityPayload = {
        user: "operator",
        project: activePlan ? activePlan.title : "No active plan",
        session: "live",
        confidence,
      };
      const identityChanged = markActivityIfChanged("identity", identityPayload);
      setIdentity((prev) => ({
        ...prev,
        ...identityPayload,
        state: inferSubsystemState(connected, stale),
        activity_at: identityChanged ? now : prev.activity_at,
      }));

      const evidenceCounts = {
        declared: 0,
        configured: 1,
        observed: inferences.length,
        verified: statusRes.ok ? 1 : 0,
        unknown: statusRes.ok ? 0 : 1,
      };
      const evidencePayload = {
        counts: evidenceCounts,
        indicators: [
          { label: "Backend Status", state: statusRes.ok ? "observed" : "unknown" },
          { label: "Reasoning", state: inferences.length > 0 ? "observed" : "unknown" },
          { label: "Planning", state: activePlan ? "configured" : "unknown" },
        ],
      };
      const evidenceChanged = markActivityIfChanged("evidence", evidencePayload);
      setEvidence((prev) => ({
        ...prev,
        ...evidencePayload,
        state: inferSubsystemState(connected, stale, !statusRes.ok),
        activity_at: evidenceChanged ? now : prev.activity_at,
      }));

      const reasoningData = {
        confidence,
        inferences,
        assumptions: Array.isArray(reasoningCore.assumptions) ? reasoningCore.assumptions : [],
      };
      const reasoningChanged = markActivityIfChanged("reasoning", reasoningData);
      setReasoning((prev) => ({
        ...prev,
        ...reasoningData,
        state: inferSubsystemState(connected, stale),
        activity_at: reasoningChanged ? now : prev.activity_at,
      }));

      const planningData = {
        activeGoal: activePlan ? activePlan.title : "none",
        nextAction: nextStep ? nextStep.title : "none",
        steps: (activePlan?.steps || []).slice(0, 8).map((step) => ({
          id: step.id || step.title,
          title: step.title,
          status: String(step.status || "pending").toLowerCase(),
          dependsOn: (step.dependencies || [])[0] || "root",
        })),
      };
      const planningChanged = markActivityIfChanged("planning", planningData);
      setPlanning((prev) => ({
        ...prev,
        ...planningData,
        state: inferSubsystemState(connected, stale),
        activity_at: planningChanged ? now : prev.activity_at,
      }));

      const deliberationData = {
        recommendation: activePlan ? activePlan.id : "none",
        approvalState: approvalDecision ? "approved" : "pending",
        alternatives: plans.slice(1, 4).map((item) => item.id || item.title).filter(Boolean),
      };
      const deliberationChanged = markActivityIfChanged("deliberation", deliberationData);
      setDeliberation((prev) => ({
        ...prev,
        ...deliberationData,
        state: inferSubsystemState(connected, stale),
        activity_at: deliberationChanged ? now : prev.activity_at,
      }));

      const toolData = {
        tools: toolsPayload.tools || [],
        currentActivity: "polling registry",
        executionEnabled: Boolean(toolsPayload.execution_enabled),
        timeline: toolTimeline,
        last_poll_at: now,
      };
      const toolsChanged = markActivityIfChanged("tools", toolData);
      setTools((prev) => ({
        ...prev,
        ...toolData,
        state: inferSubsystemState(connected, stale),
        activity_at: toolsChanged ? now : prev.activity_at,
      }));

      setConversation({
        state: inferSubsystemState(connected, stale),
        messages: [
          { role: "SYSTEM", content: `Last poll: ${now}` },
          { role: "REASONING", content: `Inference confidence ${confidence}%.` },
          { role: "PLANNING", content: `Next action: ${planningData.nextAction}` },
        ],
        activity_at: now,
      });

      setConnection({
        state: "CONNECTED",
        lastSuccessfulPollAt,
        lastAttemptAt: attemptAt,
        stale,
        pollIntervalMs: currentInterval,
        failureCount,
        message: statusPayload?.status ? `Backend status: ${statusPayload.status}` : "Connected",
      });

      scheduleNext();
    };

    pollOnce();

    return () => {
      disposed = true;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, []);

  useEffect(() => {
    const order = ["identity", "evidence", "reasoning", "planning", "deliberation", "tools"];
    const timer = setInterval(() => {
      setBusActive((current) => {
        const idx = order.indexOf(current);
        return order[(idx + 1) % order.length];
      });
    }, 2500);
    return () => {
      clearInterval(timer);
    };
  }, []);

  const chronicleRecord = useMemo(() => {
    return epochRecords.find((item) => item.epoch.includes("VIII")) || null;
  }, []);

  return {
    conversation,
    identity,
    evidence,
    reasoning,
    planning,
    deliberation,
    tools,
    busActive,
    connection,
    activityMap,
    chronicleTimeline,
    selectedChronicle,
    setSelectedChronicle,
    chronicleRecord,
  };
}
