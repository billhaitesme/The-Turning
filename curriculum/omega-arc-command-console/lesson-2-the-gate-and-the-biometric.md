# Lesson 2 — The Gate and the Biometric

An approval-gated command does not run when it is initiated. Instead it becomes a bounded tool
request in the existing approval pipeline, and it executes only after an operator approval confirmed
by a device biometric — a fingerprint or a face on the operator's phone. The command waits in an
awaiting-approval state until that confirmation lands. If the approval expires first, the command
expires with it; nothing runs on a stale approval.

The biometric is not decoration; it is the gate. Only the mobile approve route records that an
approval was confirmed by a biometric, and only that recorded confirmation releases a command to
execute. An approval recorded by any other channel is stored but does not release the command — the
command stays awaiting approval, with a note saying so. This is why the desktop cannot self-approve a
sensitive action: a desktop console may initiate an approval-gated command, but the confirmation must
come from the phone. The surface that asks is not allowed to also be the surface that consents.

Two switches govern execution and must not be confused. COMMAND_EXECUTION is on by default, because
every execution on the console path has already passed a device biometric — there is nothing left to
gate. ENABLE_TOOL_EXECUTION stays off by default and governs a different path entirely: the
model-initiated chat tool path, where a request comes from a model turn rather than from the
operator's hand. The operator-initiated path is trusted because it is biometric-confirmed; the
model-initiated path stays closed until it earns the same trust.

Nothing on this surface is silent. Every command is written to the command log with its requester,
its channel, its linked request and approval, its outcome, and its timestamps — including the ones
that did not succeed: forbidden, denied, expired, and failed. A refusal is a recorded event, not a
dropped one. The Covenant test applies to each command: explain why, reverse where possible, and
preserve the history.
