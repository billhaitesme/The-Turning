# OMEGA-ARC Engineering Guide

This guide defines the working conventions for human contributors, IDE assistants, and Codex sessions. It is an internal governance document; the Covenant, Constitution, and accepted architecture decisions remain authoritative.

## Before changing the repository

Read, in order:

1. [`COVENANT.md`](../../COVENANT.md)
2. [`CONSTITUTION.md`](../../CONSTITUTION.md)
3. [`ARCHITECTURE.md`](../../ARCHITECTURE.md)
4. [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)
5. [`ROADMAP.md`](../../ROADMAP.md)
6. [`ARCHITECTURE_DECISIONS.md`](../../ARCHITECTURE_DECISIONS.md)
7. [`docs/architecture/versioning.md`](../architecture/versioning.md)

Preserve user work. Never discard a dirty tree, rewrite history, or combine unrelated changes merely to make a checkpoint look clean.

## Branch naming

Use lowercase names with hyphenated descriptions:

| Purpose | Pattern | Example |
|---|---|---|
| Epoch feature | `feature/epoch-<roman>-<scope>` | `feature/epoch-ix-c-approvals` |
| Bug fix | `fix/<scope>` | `fix/mobile-stream-reconnect` |
| Documentation | `docs/<scope>` | `docs/ix-b-validation` |
| Release preparation | `release/epoch-<roman>-<version>` | `release/epoch-ix-0.2.0` |
| Codex-owned task | `codex/<scope>` | `codex/ix-b-checkpoint-audit` |

Create release branches only from a reviewed, reproducible baseline. Do not begin IX-C from a dirty IX-B working tree.

## Commit messages

Use Conventional Commits:

```text
<type>(<scope>): <imperative summary>
```

Common types are `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`, `perf`, and `revert`.

Examples:

```text
feat(runtime): publish typed stream lifecycle events
fix(ios): restore runtime connection after foregrounding
docs(governance): record IX-B validation gate
chore(release): checkpoint Epoch IX 0.2.0
```

Each commit should represent one reviewable concern. Keep generated runtime state, caches, logs, databases, secrets, and build outputs out of commits.

## Epoch and version policy

[`docs/architecture/versioning.md`](../architecture/versioning.md) is the release-identity authority.

- Epoch names describe architectural continuity.
- Semantic versions describe compatibility and delivery.
- Every active component must report the same current product version.
- The mobile API major is independent from the product version.
- Historical documents retain historical epoch names when clearly presented as history.
- Version changes require synchronized manifests, compatibility defaults, documentation, tests, and release metadata.

Never advance the epoch or version merely to mark unfinished work. Update [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) when phase or validation state changes.

## Architecture Decision Records

Use [`ARCHITECTURE_DECISIONS.md`](../../ARCHITECTURE_DECISIONS.md) for the concise governing index and `docs/decisions/` for detailed records.

A proposal should state:

1. Context and the concrete problem
2. Decision
3. Reason and rejected alternatives
4. Consequences and compatibility impact
5. Migration or rollback path
6. Status: Proposed, Accepted, Superseded, or Rejected

Do not rewrite an accepted ADR to hide a changed decision. Add a superseding ADR and link both records.

## Definition of Done for an epoch or phase

A phase is complete only when:

- its roadmap objectives are implemented without undeclared future-scope behavior;
- runtime authority and deterministic boundaries remain intact;
- automated unit, integration, contract, and production-build checks pass;
- required native clients build and run on physical hardware;
- background, foreground, offline, reconnect, accessibility, and security paths are validated where applicable;
- active documentation, manifests, compatibility gates, and release metadata agree;
- genuine technical debt and accepted limitations are recorded;
- generated artifacts and private runtime data are excluded;
- the working tree is intentionally scoped and reviewed;
- a reproducible checkpoint commit and documented tag exist.

Passing automated tests alone does not complete a phase that has a physical-device validation gate.

## Release and checkpoint process

1. Freeze feature scope.
2. Read `PROJECT_STATUS.md` and the current validation report.
3. Inventory tracked modifications, untracked files, ignored artifacts, and runtime data.
4. Preserve unrelated work before separating commits; do not delete it.
5. Remove generated state from the proposed commit without erasing the operator’s retained data.
6. Build and test every component supported by the current host.
7. Complete platform-specific physical-device checklists.
8. Re-run version, contract, link, and `git diff --check` audits.
9. Review the exact staged diff.
10. Create the checkpoint commit.
11. Create the documented annotated tag on that exact commit.
12. Verify a clean clone can reproduce the build and tests.
13. Update `PROJECT_STATUS.md` and `CHANGELOG.md` with the completed checkpoint.

For Epoch IX / Version 0.2.0, the planned tag is `epoch-ix-a`.

## Testing expectations

Tests must be hermetic. They must not mutate tracked runtime stores or depend on an operator’s private database. Use temporary directories and explicit store paths.

Before committing:

- run the complete backend suite;
- build both web applications;
- run iOS unit/UI tests on macOS with the generated Xcode project;
- run Android unit/instrumentation tests with the committed Gradle wrapper;
- parse the shared OpenAPI and design-token files;
- run `git diff --check`;
- confirm the test run did not dirty tracked files.

## Security and data handling

- Never commit bearer tokens, signing credentials, certificates, private keys, model weights, databases, or device-specific secrets.
- Mobile authentication must fail closed.
- LAN binding must be an explicit validation/deployment choice, not an unnoticed default.
- Release clients require trusted HTTPS unless an explicitly documented local-development exception applies.
- Preserve platform certificate validation and secure credential storage.

## Continuity test

Before requesting review, answer:

1. Can OMEGA-ARC explain why this change happened?
2. Can it be reversed?
3. Does it preserve history?
4. Will a future steward understand it?
5. Does it improve coherence rather than merely add capability?
