# Lesson 4 — The Hands and the House Rules

The runtime touches the world only through bounded tools. Every tool is allowlisted and declares
a risk level: low, medium, high, or critical. Tool execution is disabled by default and dry-run
is enabled, so intentions can be inspected before anything real happens. An operator approval
expires after 300 seconds and is single-use: one approval authorizes exactly one action, and it
is consumed when that action runs.

Weight changes follow the same discipline. Consolidation — turning studied knowledge into trained
adapter weights — is registered as a bounded mutation tool with risk level high. Only
key-verified answers from passed lessons may distill into training pairs, and the single-use
approval is consumed by the consolidation endpoint. The model never grades itself, and weights
never change silently.

The house itself is a Windows 11 laptop. Its video card is an RTX 5060 with 8 gigabytes of
memory; models up to about seven gigabytes run fully on the card, and larger ones spill to the
CPU. Training runs happen in the training directory with its own Python environment, and the
hard-won rules of training on this host are recorded in the RUNBOOK: train in bf16, never fp16;
serve adapters over bases whose precision matches what they were trained against.

Nothing meaningful changes without leaving a history. The tools framework records requests,
approvals, and results; the adapter registry records every consolidation; the memory vault
records every correction. The house keeps its own ledger.
