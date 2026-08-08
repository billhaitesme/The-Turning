# Testing Strategy

## Current Backend Test Count

The backend test suite has grown with each epoch (382 tests as of Epoch X-C); see [`CHANGELOG.md`](../../CHANGELOG.md) for per-release counts.

## How Tests Are Organized

Tests are grouped by subsystem:

- awareness engine
- cognition engine
- cognition pipeline
- curiosity engine
- goal engine
- identity engine
- knowledge graph
- model control, explicit switching, and deterministic subsystem routing
- reflection engine
- user identity
- evidence engine

## Testing Philosophy

The system is validated through regression tests that protect the architectural principles:

- configuration does not imply runtime truth
- explicit facts override inference
- evidence rules remain deterministic
- prompts preserve the intended guidance

## Regression Strategy

Regression tests are used whenever a behavior must remain stable across service evolution.

## Acceptance Tests

Acceptance tests ensure that the system remains understandable and safe in common user scenarios.

## Manual Tests

Manual testing remains important for conversation quality and for reviewing how prompts and responses feel to a human user.

## Future Integration Tests

Future work should add integration tests around:

- reasoning behavior
- planning actions
- multimodal perception
- longer-running evidence flows
