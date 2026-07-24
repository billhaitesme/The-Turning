# Direct Model Mode

Direct Model mode is an explicit operator-selected conversation mode. It pins the conversational model to `DIRECT_CHAT_MODEL` (default: `dolphin-mixtral:8x7b`) and sends only the stored user/assistant transcript plus the new user message to that model.

## Request path

```text
Operator selects Direct Model
  -> Runtime pins and verifies DIRECT_CHAT_MODEL
  -> Raw user/assistant history + new input
  -> Ollama chat endpoint
  -> Unmodified model response
  -> Transcript + model telemetry
```

Direct mode does not call:

- system-prompt or personality composition;
- identity augmentation;
- memory retrieval or persistence;
- web search;
- declarative acknowledgements or intent detection;
- cognition, reasoning, planning, or deliberation pipelines;
- tool-request interpretation or tool execution;
- post-turn learning or response rewriting.

The deterministic runtime still verifies the actual provider model, rejects provider substitution, records model telemetry, and stores the transcript. Direct mode never falls back to another conversational model, even if fallback is enabled for normal runtime mode. These responsibilities do not alter conversational language.

## API

Both `POST /chat` and `POST /chat/stream` accept:

```json
{
  "message": "Exact operator input",
  "conversation_id": "...",
  "mode": "direct"
}
```

`mode` defaults to `runtime` for backwards compatibility. A direct request that names a different `model` is rejected instead of silently substituting it.

## Tradeoffs

Direct mode intentionally removes OMEGA-ARC identity and personality prompting. The selected model may therefore identify or behave according to its base training. It also will not remember facts through OMEGA-ARC memory, interpret tool requests, update evidence, create plans, or learn from the completed turn. Switching modes does not erase transcript history.
