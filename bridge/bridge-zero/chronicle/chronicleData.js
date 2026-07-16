export const chronicleTimeline = [
  "Genesis",
  "Continuity",
  "Identity",
  "Cognition",
  "Evidence",
  "Reasoning",
  "Planning",
  "Deliberation",
  "Tools",
];

export const epochRecords = [
  {
    epoch: "Epoch VIII",
    title: "Trusted Tools and Verified Execution",
    adrs: ["0008-bounded-tools-and-verified-execution"],
    acceptance: ["024", "025", "026", "027", "028", "029", "030", "031", "032", "033"],
    milestones: [
      "Tool contracts and result envelopes",
      "Deterministic registry and request-bound approvals",
      "Non-general executor foundation",
      "Read-only system inspection endpoints",
    ],
    backendTests: 289,
    architectureChanges: [
      "Bounded adapter protocol",
      "Approval scope hash validation",
      "Structured result envelope and evidence bridge",
    ],
  },
];
