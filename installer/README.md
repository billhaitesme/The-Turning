# OMEGA-ARC Windows installer

Builds a single `OMEGA-ARC-Setup-<version>.exe` (Inno Setup 6) that installs everything a user
needs to run OMEGA-ARC locally — no admin rights, no system Python, no manual setup.

## What the installer contains / does

- **Embedded Python** (python.org embeddable CPython) with all backend dependencies preinstalled —
  the user needs no Python of their own.
- **Core Runtime** (`backend/` tracked sources + clean data fixtures; tests/benchmarks excluded).
- **Built web UIs** — Command Deck (`frontend/dist`) and desktop Bridge Zero (`bridge-zero/dist`).
- **Launcher** (`app/OMEGA-ARC.cmd` → PowerShell): starts Ollama, the Core Runtime (8001), and the
  Command Deck (5173), waits for readiness, and opens the browser. Start-menu + optional desktop
  shortcut with the 0M3-G4 icon.
- **Ollama dependency**: if not detected, Setup downloads the official `OllamaSetup.exe` at install
  time and runs it silently (checkbox task — the user can skip and install later).
- **Models are NOT bundled** (~6 GB): the launcher's first run detects missing required models
  (active chat model + embedder from `.env`) and pulls them via Ollama after explicit consent.
- `.env` is created from `.env.example` on first launch; user data (`.env`, `backend/data`,
  `omega_arc.db`) survives uninstall by design.

## Build

Requirements: Windows, git, Inno Setup 6 (`winget install JRSoftware.InnoSetup`), network (first
build downloads the embeddable Python + pip), and both Vite dists built.

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
```

Output: `installer\Output\OMEGA-ARC-Setup-<version>.exe` (~24 MB). The build smoke-tests the staged
backend against the embedded runtime before compiling; bump the version in `OMEGA-ARC.iss`
(`#define AppVersion`) when the release advances.

Validated flow (0.3.2): silent install → installed embedded Python imports the installed backend →
installed backend serves HTTP 200 → silent uninstall removes cleanly.

## Honest caveats

- **Unsigned executable** — Windows SmartScreen will warn on first run ("More info → Run anyway").
  Code-signing requires a paid certificate; document or budget for it before wide distribution.
- **Windows x64 only.** macOS/Linux users run from source.
- First launch needs network + disk for the model pulls; the chat model runs best with a capable
  CPU/GPU (see the project README).
- The default `.env` is a local single-operator configuration (loopback bind, dev token). LAN and
  mobile-console use still require the documented opt-ins.
