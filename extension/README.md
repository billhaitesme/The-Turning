# OMEGA-ARC Browser Hands (extension)

Lets the local OMEGA-ARC runtime see and act in the browser tabs you already have open, in
Chrome, Edge or Firefox, the way Claude in Chrome works for Claude. One codebase, no build step.

What it can do, and what gates it (ADR 0028):

| action | what | gate |
|---|---|---|
| list tabs, read a tab's text, screenshot a tab, open a URL | looking | the console's BROWSER HANDS switch |
| click, type | acting in your logged-in sessions | the switch **and** your fingerprint |

Everything is logged on the console. Page text reaches OMEGA as untrusted data.

## Load it

**Chrome / Edge:** open `chrome://extensions` (Edge: `edge://extensions`), turn on *Developer
mode*, press *Load unpacked*, choose this `extension/` folder.

**Firefox:** open `about:debugging#/runtime/this-firefox`, press *Load Temporary Add-on…*,
choose `extension/manifest.json`. (A temporary add-on is gone after a restart; a permanent
install needs the add-on signed, a later step.)

## Pair it

1. On the desktop console, under **THE BROWSER HANDS**, copy the pairing token.
2. Open the extension's options page (right-click its icon → Options, or from the extensions
   page) and paste the token. Backend URL stays `http://127.0.0.1:8001` on this PC.
3. Press **SAVE & TEST**: it should say PAIRED.
4. Flip the console's **BROWSER HANDS** switch ON when you want OMEGA to use the browser.

The extension's badge shows ON / OFF (the switch), `!` (token rejected), `x` (backend
unreachable). It only ever talks to the backend URL you configured; it opens no ports.
