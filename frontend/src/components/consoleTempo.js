// The Physical Control Bay's mode bank sets the console's TEMPO (2026-11-06). Before this the
// three rockers only changed animation speed, which was barely visible and did nothing. Now each
// mode is a real refresh rate, so how lively the console looks is how lively it is:
//   STEADY - the original cadence
//   SURGE  - live: telemetry every second, the Command Deck every 2 s (most traffic)
//   QUIET  - low-bandwidth: for a phone hotspot / PairVPN / Tailscale on mobile data
// (QUIET was "LOCK"; renamed so it is not confused with LOCK SHELL beside it. The id stays
// "lock" so saved preferences and the CSS hooks keep working.)
export const TEMPO = {
  steady: { label: "STEADY", pollMs: 4000, deckMs: 8000, motion: 1 },
  surge: { label: "SURGE", pollMs: 1000, deckMs: 2000, motion: 2.2 },
  lock: { label: "QUIET", pollMs: 20000, deckMs: 30000, motion: 0.25 },
};

export function tempoFor(mode) {
  return TEMPO[mode] || TEMPO.steady;
}

export function secondsLabel(ms) {
  return ms >= 1000 ? `${ms / 1000} s` : `${ms} ms`;
}
