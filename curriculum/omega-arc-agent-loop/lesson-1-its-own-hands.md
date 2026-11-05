# Lesson 1 — Its Own Hands

Epoch IX-D gave the operator hands: the command console, where an operator initiates a bounded
runtime command. Epoch XIII-A gives the conversation itself hands — the agent loop, decided in
ADR 0026. When the loop is on, the chat seat may call the runtime's registered commands mid-reply
as structured tool calls. The deterministic runtime — never the model — resolves every call
against the command registry and executes it under exactly the gates that govern the consoles.
The chat seat becomes a fourth surface over the same registry, not a new authority.

The gates do not care who asked. A read-only direct command executes at once, because there is
nothing to gate on a read. A side-effecting command becomes a tool request and waits for the
operator's biometric approval on a mobile console — when a result says awaiting_approval, the
truthful reply is that it is waiting for the operator's confirmation, never that it ran. A
forbidden command is refused. And a call that names no registered command at all is
refused and recorded too: the registry is the authority, and no free-form execution exists anywhere.

The loop is off by default. Turning it on — the switch is ENABLE_AGENT_LOOP — is the recorded
operator action that supersedes the old chat-path freeze, and supersedes it only through the
loop. Each turn is bounded: a hop budget caps how many rounds of tools may run, and a size cap
bounds how much of each tool result returns into context. When the budget is spent, the seat is
told to answer with what it has. Tool results enter context as data, never as instructions.

Before XIII-A, a bare model in the chat seat would say things like "I would need integrated
tools to do that." That sentence described the model, not the runtime it inhabits — and once the
loop exists it is simply false. The truthful answer is: the runtime can call its registered
commands from chat; reads execute now, side effects wait for the operator's approval, and
anything outside the registry does not exist to be commanded.
