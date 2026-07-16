import { useEffect, useMemo, useState } from "react";
import { chronicleTimeline, epochRecords } from "../chronicle/chronicleData";

const statuses = ["OFFLINE", "INITIALIZING", "READY", "BUSY", "WARNING", "ERROR"];

export function useBridgeData() {
  const [conversation] = useState({
    state: "READY",
    messages: [{ role: "SYSTEM", content: "Bridge Zero foundation initialized." }],
  });
  const [identity] = useState({
    state: "READY",
    user: "operator",
    project: "Bridge Zero Foundation",
    session: "bootstrap",
    confidence: 76,
  });
  const [evidence] = useState({
    state: "READY",
    counts: { declared: 2, configured: 2, observed: 1, verified: 1, unknown: 1 },
    indicators: [
      { label: "Backend", state: "configured" },
      { label: "Planning", state: "observed" },
      { label: "Tools", state: "unknown" },
    ],
  });
  const [reasoning] = useState({
    state: "READY",
    confidence: 68,
    inferences: [
      "Interface shell is aligned to subsystem topology.",
      "Instrumentation is reusable across panels.",
    ],
    assumptions: ["Backend reachable", "Operator context stable"],
  });
  const [planning] = useState({
    state: "READY",
    activeGoal: "Bridge Zero Milestone 1",
    nextAction: "Integrate launcher workflow",
    steps: [
      { id: "step-1", title: "Shell layout", status: "completed", dependsOn: "root" },
      { id: "step-2", title: "Instrument library", status: "completed", dependsOn: "step-1" },
      { id: "step-3", title: "Status lamp system", status: "active", dependsOn: "step-2" },
      { id: "step-4", title: "Live polling", status: "pending", dependsOn: "step-3" },
    ],
  });
  const [deliberation] = useState({
    state: "READY",
    recommendation: "milestone-1-foundation",
    approvalState: "pending",
    alternatives: ["fast-ui-shell", "minimal-control-deck"],
  });
  const [tools] = useState({
    state: "READY",
    tools: [
      {
        name: "backend_health_check",
        enabled: true,
        risk_level: "low",
        requires_approval: true,
      },
    ],
  });
  const [busActive, setBusActive] = useState("identity");
  const [selectedChronicle, setSelectedChronicle] = useState("Tools");

  useEffect(() => {
    const order = ["identity", "evidence", "reasoning", "planning", "deliberation", "tools"];
    const timer = setInterval(() => {
      setBusActive(order[Math.floor(Date.now() / 1500) % order.length]);
    }, 1500);
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
    chronicleTimeline,
    selectedChronicle,
    setSelectedChronicle,
    chronicleRecord,
  };
}
