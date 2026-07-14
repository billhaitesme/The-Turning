# OMEGA-ARC Architecture

```text
User
  |
  v
Intent Router
  +--> Identity Engine
  +--> Personality Engine
  +--> Memory Retrieval
  +--> Network Search
  +--> Vision Router
  |
  v
Prompt Composer
  |
  v
Model Router
  +--> llama2-uncensored:7b
  +--> llama3.1:8b
  +--> llava:7b
  +--> gemma3:1b
  +--> embeddinggemma:latest
  |
  v
Response Validator
  |
  v
Memory / Journal / Academy / Proposals
```

Important state is human-readable, versioned, and reversible. Runtime models are replaceable.
