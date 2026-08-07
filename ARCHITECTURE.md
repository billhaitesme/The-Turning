# OMEGA-ARC Architecture

```text
User
  |
  v
Deterministic Runtime
  +--> Identity Engine
  +--> Personality Engine
  +--> Memory Retrieval
  +--> Network Search
  +--> Vision Router
  +--> Tool Approval / Trusted Adapters
  |
  v
Prompt Composer
  |
  v
Operator-Selected Chat Model (Model Lock)
  |
  v
Unmodified Model Response
  |
  v
Memory / Journal / Academy / Proposals
```

Vision, embedding, and trusted-tool adapters remain deterministic subsystem selections. They do not substitute, supervise, or rewrite the conversational model. Important state is human-readable, versioned, and reversible. Runtime models are replaceable only through explicit operator selection.
