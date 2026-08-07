# Bridge Zero

Bridge Zero is the engineering command bridge for OMEGA-ARC.

## Purpose

Bridge Zero visualizes subsystem cognition in real time:
- Identity
- Evidence
- Reasoning
- Planning
- Deliberation
- Tools

Conversation is present as one instrument, not the entire interface.

## Run

1. Copy `bridge.config.example` to `.env` in this directory and adjust values.
2. Install dependencies:
   - `npm install`
3. Start development mode:
   - `npm run dev`
4. Build for production:
   - `npm run build`

Default bridge URL: `http://127.0.0.1:5181`

## Version Plate

The version plate is driven by release metadata environment values:
- `VITE_ARCH_VERSION`
- `VITE_BUILD_NUMBER`
- `VITE_BACKEND_TEST_COUNT`

This allows Bridge Zero visuals to track backend release metadata automatically.
