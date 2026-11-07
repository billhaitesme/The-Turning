# 0028 — Browser Hands: acting in the operator's own tabs (Epoch XIII-F)

**Status:** Accepted; built 2026-11-06
**Operator direction (2026-11-06):** OMEGA should work *"within browser tabs I might've
already had open, whether it's Chrome, Mozilla, Edge, etc."*, and separately have a browser of
its own to browse or pull things up.
**Builds on:** ADR [`0026`](0026-the-agent-loop.md) (breaker pattern, bounded tools),
ADR [`0014`](0014-operator-approvals.md) (biometric approvals), ADR [`0008`](0008-bounded-tools-and-verified-execution.md).

## Context

Chrome 136+ and Edge ignore remote-debugging on the everyday profile; Firefox never exposed
one. Nothing on the PC can attach to the tabs the operator actually uses. The only path is an
extension, which is how Claude in Chrome does it. Playwright and the like can only give OMEGA a
separate browser of its own, which the operator also wants, for a different purpose.

## Decision

1. **The extension** (`extension/`, MV3, one codebase for Chrome, Edge and Firefox) long-polls
   the local backend for jobs and posts results. It opens no ports and talks only to the
   configured backend URL. It is loaded unpacked by the operator; nothing is downloaded.
2. **The bridge** (`services/browser_bridge.py`, `routes/browser.py`): a pairing token
   generated once and typed into the extension; a standing **BROWSER HANDS** switch on the
   console, OFF by default, flipped only by recorded operator action, like the network
   breaker; a job log the console shows.
3. **The hands** (`services/adapters/browser_hands.py`), registered as bounded tools and
   commands:
   - read-class, under the switch: `browser_tabs`, `browser_read`, `browser_screenshot`,
     `browser_open` (opening a URL is treated as read-class because the operator asked for
     "pull up things to show me" without a fingerprint each time; http(s) only);
   - act-class, under the switch **and** the biometric: `browser_click`, `browser_type`.
   Page text is untrusted data. Screenshots land in the image store for `look_at_image`.
4. **OMEGA's own browser** is a separate concern: Playwright in the backend venv (installed by
   the operator), to be proposed through the Workbench as its own adapter.

## Consequences

- OMEGA can read what the operator is looking at and open pages for them without a
  fingerprint; it cannot click or type in their sessions without one, and cannot do anything
  while the switch is off.
- The extension must be re-loaded in Firefox after a restart until it is signed.
