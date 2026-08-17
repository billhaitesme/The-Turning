# Lesson 3 — Change and Release Discipline

The architecture decision records under docs/decisions are authoritative, together with the
Covenant, Constitution, and Charter. Status is reported honestly: something is validated only
with real evidence, and an owed validation is recorded as an exception, not glossed over.

Self-modification follows the eight steps in AGENTS.md, in order: proposal, backup, patch, syntax
check, tests, health check, review, and then promote or rollback. Never commit secrets, model
weights, virtual environments, caches, or private databases. Tests are the pytest suite under
backend/tests — over four hundred of them — and they must be hermetic: tests point the runtime at
temporary stores, never at the live data files.

Versions move by a rule. Within an epoch, each shippable milestone increments the patch number;
crossing into a new epoch increments the minor number; a breaking change is signaled by an
API-major bump and is never hidden inside a milestone patch. Every component reports the same
version, and scripts/check_versions.py enforces it: it reads the declared Release from
docs/architecture/versioning.md and fails if any component source disagrees. The order when
advancing a release is: update the versioning document first, then every component source, then
the changelog, then run the check.

Every GitHub release gets a freshly rebuilt installer zip attached — rebuild the distributions
first, then attach. Epoch milestones are tagged, for example epoch-xii-a for release 0.5.0.
Consequential git and release actions are surfaced to the operator before they are taken.
