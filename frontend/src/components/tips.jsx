// HUD tips (2026-11-06): hover any element carrying data-tip to see what it is and does.
// Switchable from the Physical Control Bay (TIPS ON/OFF), like a game's HUD hints; the choice is
// remembered in this browser. Labels that repeat across the console (badges, plates, lamps,
// ribbon chips, panel titles) get their text from TIPS by label, so every instance agrees.
import { useEffect, useState } from "react";

export const TIPS = {
  // top status strip
  "core runtime": "Is the backend answering? OPERATIONAL = the status endpoint replied on the last refresh.",
  "power state": "The console's own link state: BOOT while it starts, RECOVERING LINK after a dropped refresh, then ONLINE.",
  phase: "Where OMEGA is in the current reply (e.g. bridge, mirror, guide, silence). NONE when idle.",
  build: "OMEGA-ARC version running on the backend.",
  seat: "The chat model answering you right now (the 'seat').",
  "agent loop": "ON = OMEGA can call tools (commands) mid-reply. OFF = plain chat only.",
  senses: "Network breaker state. LIVE = OMEGA may search/fetch the web. DARK = no internet reads.",
  adapters: "Number of registered tool adapters (built-in plus Toolwright-inducted).",
  poll: "How long the last telemetry refresh took, end to end.",
  sync: "Endpoints that answered the last refresh, out of how many were asked.",
  "last poll": "When the console last refreshed its telemetry (host time, 24-hour).",
  // ribbon chips
  mode: "Console tempo from the control bay: STEADY, SURGE (live) or QUIET (low bandwidth).",
  stream: "ACTIVE while a reply is streaming in.",
  scan: "BURST for a moment after you press the dial (scan now).",
  mem: "Memories OMEGA pulled up for the current reply.",
  web: "Web results OMEGA used in the current reply.",
  pwr: "Link health: colour follows the alarm level.",
  // identity / reasoning / planning plates
  style: "How OMEGA reads your writing style this conversation.",
  strategy: "The reply strategy OMEGA picked after reflecting on its last answer.",
  project: "ACTIVE when a conversation is open.",
  uncertainty: "Open questions OMEGA has flagged as uncertain.",
  conflicts: "Pieces of evidence that disagree with each other.",
  confidence: "OMEGA's self-score of its last reply (0-1). A small model's self-score is a hint, not a fact.",
  "current plan": "The plan OMEGA is tracking (from goals you set with 'my goal is to ...').",
  "next action": "The next step the reasoning pipeline suggests.",
  blockers: "Things the current plan says are in the way.",
  recommendation: "What deliberation currently recommends.",
  alternatives: "How many other plans were weighed.",
  "approval queue": "Gated actions waiting for your fingerprint on the phone.",
  "approvals pending": "Gated actions waiting for your fingerprint on the phone.",
  enabled: "Adapters currently allowed to run.",
  registered: "All adapters the runtime knows.",
  "last run": "When an adapter last ran (host time).",
  "latest verified": "The newest fact a tool result actually verified.",
  telemetry: "Same as Core Runtime: is the backend answering.",
  "last update": "When this strip last refreshed (host time).",
  // panels
  "command channel": "Talk to OMEGA. TRANSMIT streams the reply; SEND (NO STREAM) waits for the whole reply.",
  "command registry": "Every command OMEGA (and you) can run, the network breaker, deep-thinking seat, faces and the Toolwright.",
  identity: "Who OMEGA thinks it is talking to and how: style, strategy, seat.",
  evidence: "What OMEGA knows and how sure: declared, configured, observed, verified or unknown.",
  reasoning: "Conflicts and uncertainty OMEGA is tracking.",
  planning: "Goals and plans OMEGA is tracking, and what blocks them.",
  deliberation: "Options OMEGA weighed and what it recommends.",
  "trusted adapters": "The tools the runtime can run, with their last results.",
  "operations strip": "One-line summary: plan, approvals, verified evidence, freshness.",
  "galactic basic encoder": "Decorative: shows the console's status in Aurebesh.",
};

export function tipFor(label) {
  return TIPS[String(label || "").trim().toLowerCase()];
}

const STORE_KEY = "omega.tips";

export function useTipsSetting() {
  const [on, setOn] = useState(() => {
    try { return localStorage.getItem(STORE_KEY) !== "off"; } catch { return true; }
  });
  const toggle = () => setOn((value) => {
    const next = !value;
    try { localStorage.setItem(STORE_KEY, next ? "on" : "off"); } catch { /* private mode */ }
    return next;
  });
  return [on, toggle];
}

// One floating tip for the whole page: follows the pointer over any [data-tip] element.
export function TipLayer({ enabled }) {
  const [tip, setTip] = useState(null);

  useEffect(() => {
    if (!enabled) {
      setTip(null);
      return undefined;
    }
    function onMove(event) {
      const host = event.target?.closest?.("[data-tip]");
      const text = host?.getAttribute("data-tip");
      if (!text) {
        setTip((current) => (current ? null : current));
        return;
      }
      setTip({ text, x: event.clientX, y: event.clientY });
    }
    function onLeave() { setTip(null); }
    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);
    window.addEventListener("scroll", onLeave, { passive: true });
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("scroll", onLeave);
    };
  }, [enabled]);

  if (!enabled || !tip) return null;
  const width = 280;
  const left = Math.min(tip.x + 14, window.innerWidth - width - 8);
  const top = tip.y + 18 + 80 > window.innerHeight ? tip.y - 70 : tip.y + 18;
  return (
    <div className="hud-tip" style={{ left, top, maxWidth: width }} role="tooltip">
      {tip.text}
    </div>
  );
}
