# Lesson 3 — Broadening by Risk

The registry grows one risk-classed command at a time, and the gate a command carries is decided by
what it does, not by how useful it would be to skip the gate. A direct command is either a built-in
action the runtime already owns, such as starting a new conversation, or a read-only tool. A
read-only command executes immediately because there is nothing to gate on a read: it observes and
returns, it never changes state, so waiting for an approval would protect nothing.

That permission is guarded. The console will direct-run a bounded tool only when the tool
declares no side effects. A tool that changes state, offered as a direct command, is refused, not run — the guard
lives in the executor, not in the interface, so no console can talk the runtime into running a
side-effecting tool without an approval. The first read-only direct command is host_status, which
reads the host machine's CPU, memory, disk, and uptime and reports them back. It is the model for
every read-only command that follows.

At the far end of the scale is forbidden, and it is not about risk that can be managed with an
approval — it is about a line that is never crossed. Forbidden means Model Lock and output fidelity:
a command that would silently change which model answers, or rewrite the runtime's responses, is
never runnable. The forbidden command in the registry is change_conversational_routing — it is
listed only so the boundary stays visible, and it can never run. Model selection remains its own
explicit, recorded operator action; it is not smuggled in as a command.

So the shape of growth is settled. A new command earns its gate by its risk: a read is direct, an
action that changes state is approval-gated behind the biometric, and a violation of Model Lock is
forbidden. Anything destructive needs an explicit undo before it qualifies at all, because the
Covenant asks that actions be reversible. The registry can widen safely for a long time without ever
loosening a gate, because the gate is chosen by the risk and the risk does not change to suit the
convenience of the moment.
