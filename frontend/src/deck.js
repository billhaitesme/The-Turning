// The widget deck (XIII-A console refactor): every panel is a card the operator can reorder,
// resize, collapse, or stow. Layout is the operator's and persists locally; RESET returns the
// bridge to the default arrangement. The deck changes presentation only — never authority.

export const WIDGET_DEFS = [
  { id: "chat", title: "Command Channel", width: "half" },
  { id: "commands", title: "Command Registry", width: "third" },
  { id: "identity", title: "Identity", width: "third" },
  { id: "evidence", title: "Evidence", width: "third" },
  { id: "reasoning", title: "Reasoning", width: "third" },
  { id: "planning", title: "Planning", width: "third" },
  { id: "deliberation", title: "Deliberation", width: "third" },
  { id: "adapters", title: "Trusted Adapters", width: "third", collapsed: true },
  { id: "bus", title: "Cognitive Bus", width: "full" },
  { id: "signal", title: "Signal Array", width: "full", collapsed: true },
  { id: "operations", title: "Operations Strip", width: "full", collapsed: true },
  { id: "chronicle", title: "System Chronicle", width: "third", hidden: true },
  { id: "encoder", title: "Galactic Basic Encoder", width: "third", hidden: true },
];

export const WIDTH_CYCLE = { third: "half", half: "full", full: "third" };

const STORAGE_KEY = "omega-arc.deck.v1";

export function defaultDeck() {
  return {
    order: WIDGET_DEFS.map((w) => w.id),
    state: Object.fromEntries(
      WIDGET_DEFS.map((w) => [w.id, {
        width: w.width || "third",
        collapsed: Boolean(w.collapsed),
        hidden: Boolean(w.hidden),
      }])
    ),
  };
}

export function loadDeck() {
  const base = defaultDeck();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return base;
    const stored = JSON.parse(raw);
    const knownIds = new Set(base.order);
    const order = (Array.isArray(stored.order) ? stored.order : []).filter((id) => knownIds.has(id));
    for (const id of base.order) if (!order.includes(id)) order.push(id); // new widgets join at the end
    const state = { ...base.state };
    for (const [id, s] of Object.entries(stored.state || {})) {
      if (knownIds.has(id) && s && typeof s === "object") {
        state[id] = {
          width: ["third", "half", "full"].includes(s.width) ? s.width : state[id].width,
          collapsed: Boolean(s.collapsed),
          hidden: Boolean(s.hidden),
        };
      }
    }
    return { order, state };
  } catch {
    return base;
  }
}

export function saveDeck(deck) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(deck));
  } catch {
    /* storage unavailable — layout simply won't persist */
  }
}

export function widgetTitle(id) {
  return WIDGET_DEFS.find((w) => w.id === id)?.title || id;
}
