# Lesson 1 — Its Hands

For most of its history the runtime could observe its operator surfaces and, later, approve or deny
an action it had itself raised. The command console changes that: it lets the operator initiate a
bounded runtime command, not only react to one. This is the runtime gaining hands — a way to be
told "do this" and to do it, safely, under supervision. It arrived in Epoch IX-D and is described in
ADR 0015.

The rule that keeps those hands safe is that the command registry is the authority. The registry is
a single list, held by the runtime, of every command that may be initiated and how each one is
gated. The consoles render it, they never define it: a phone or a desktop shows the operator the
cards it is given, but it cannot invent a command the registry does not list, and it cannot change
how a command is gated. If a capability is not in the registry, it cannot be commanded at all.

Every command carries a gate, and there are exactly three: direct, approval, and forbidden. A direct
command is low-risk and already explicit, so it executes at once. An approval command must be
confirmed by the operator with a device biometric before it runs. A forbidden command is shown so
the boundary is visible, but it can never run. These are the same gates the runtime already used for
its own action requests, which is the point — the console adds no new authority and no bypass of the
deterministic runtime. A commanded action enters the very pipeline an internally raised action would,
and is recorded the same way.
