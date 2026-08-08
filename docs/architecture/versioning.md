# Versioning authority

This document is the single source of truth for OMEGA-ARC release identity.

## Current identity

| Field | Value |
|---|---|
| Epoch | Epoch X — Memory |
| Release | 0.3.1 |
| Active series | 0.3.x |
| Active milestone | Epoch X-B — Rooms and Revision (released as 0.3.1; tag `epoch-x-b`) |
| Mobile API major | 1 |
| Prior milestone tags | `epoch-ix-a` (IX-B, 0.2.0) · `epoch-ix-c` (IX-C, 0.2.1) · `epoch-x-a` (X-A, 0.3.0) |

The Epoch communicates architectural continuity. Semantic versioning communicates compatibility and delivery. They are related but independent: an epoch can contain multiple compatible releases in its series (Epoch IX spanned 0.2.0–0.2.1; Epoch X begins the 0.3.x series per the milestone-versioning rule below).

## Component sources

Every active component must report Epoch X / 0.3.1 until the release version is advanced here.

| Component | Authoritative field |
|---|---|
| Backend | FastAPI application version and `RUNTIME_VERSION` default |
| Desktop Bridge Zero | `package.json` and `app/releaseMetadata.js` |
| Frontend | `package.json` and command-deck build fallback |
| iOS | Xcode marketing version and `MobileVersion.current` |
| Android | Gradle `versionName` and `MobileVersion.CURRENT` |
| Shared contract | OpenAPI `info.version` |
| Documentation | root `README.md`, `CHANGELOG.md`, and `ROADMAP.md` |

The mobile protocol remains API major `1`. A protocol major is not the product version and must not be rewritten to `0.3.1`.

## Compatibility rules

1. A client may connect only when its supported API major matches the backend API major.
2. A client version lower than `required_mobile_version` must show **Update Required** and disable runtime operations.
3. Patch and minor releases within the active series must preserve the deterministic runtime boundary and Model Lock behavior.
4. Release metadata must never claim functionality that is not backed by an authoritative runtime signal.

## Milestone versioning

Within an epoch, each shippable milestone increments the **patch** — Epoch IX-C releases as `0.2.1`,
IX-D as `0.2.2`. Crossing into a new epoch increments the **minor** — Epoch X begins at `0.3.0`. The
major stays `0` for the pre-1.0 line.

Product compatibility is governed by the **mobile API major** and the runtime compatibility gate, not
by the patch number. A breaking change is signaled by an API-major bump (and trips the gate); it is
never hidden inside a milestone patch — which is precisely why additive, API-compatible milestones may
advance only the patch.

A milestone version advances only when the milestone is committed from a clean tree, has passed its
validation gate, and is tagged (`epoch-<roman>-<milestone>`). Advance in this order: update this
document, then the component sources in the table above, then the changelog, then run the version
consistency check (`scripts/check_versions.py`).

## Tags

Milestone tags use `epoch-<roman>-<milestone>`, in lowercase. Epoch IX-A uses `epoch-ix-a`.

A Git tag identifies a commit, never a dirty working tree. Before creating a milestone tag, verify the intended release changes are committed and tested, then create an annotated tag. Do not move an existing milestone tag.

## Historical references

Documents describing completed Epoch I–VIII architecture keep their historical epoch names. They do not conflict with the current standard when written in historical context.

Active UI labels, build metadata, compatibility defaults, setup instructions, and current-roadmap statements must use Epoch IX / Version 0.2.x. A historical document must not describe an earlier epoch or version as the current release.

## Release advancement

When advancing the release, update this document first, then update all component sources in the table above, add a changelog entry, and run the version consistency check: `python scripts/check_versions.py`. The check reads the declared `Release` value here and fails if any component source disagrees.
