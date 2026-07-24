# Versioning authority

This document is the single source of truth for OMEGA-ARC release identity.

## Current identity

| Field | Value |
|---|---|
| Epoch | Epoch IX |
| Release | 0.2.0 |
| Active series | 0.2.x |
| Active milestone | Epoch IX-B |
| Mobile API major | 1 |
| Planned checkpoint tag | `epoch-ix-a` (pending clean checkpoint commit) |

The Epoch communicates architectural continuity. Semantic versioning communicates compatibility and delivery. They are related but independent: Epoch IX can contain multiple compatible Version 0.2.x releases.

## Component sources

Every active component must report Epoch IX / 0.2.0 until the release version is advanced here.

| Component | Authoritative field |
|---|---|
| Backend | FastAPI application version and `RUNTIME_VERSION` default |
| Desktop Bridge Zero | `package.json` and `app/releaseMetadata.js` |
| Frontend | `package.json` and command-deck build fallback |
| iOS | Xcode marketing version and `MobileVersion.current` |
| Android | Gradle `versionName` and `MobileVersion.CURRENT` |
| Shared contract | OpenAPI `info.version` |
| Documentation | root `README.md`, `CHANGELOG.md`, and `ROADMAP.md` |

The mobile protocol remains API major `1`. A protocol major is not the product version and must not be rewritten to `0.2.0`.

## Compatibility rules

1. A client may connect only when its supported API major matches the backend API major.
2. A client version lower than `required_mobile_version` must show **Update Required** and disable runtime operations.
3. Patch and minor releases within 0.2.x must preserve the deterministic runtime boundary and Model Lock behavior.
4. Release metadata must never claim functionality that is not backed by an authoritative runtime signal.

## Tags

Milestone tags use `epoch-<roman>-<milestone>`, in lowercase. Epoch IX-A uses `epoch-ix-a`.

A Git tag identifies a commit, never a dirty working tree. Before creating a milestone tag, verify the intended release changes are committed and tested, then create an annotated tag. Do not move an existing milestone tag.

## Historical references

Documents describing completed Epoch I–VIII architecture keep their historical epoch names. They do not conflict with the current standard when written in historical context.

Active UI labels, build metadata, compatibility defaults, setup instructions, and current-roadmap statements must use Epoch IX / Version 0.2.x. A historical document must not describe an earlier epoch or version as the current release.

## Release advancement

When advancing the release, update this document first, then update all component sources in the table above, add a changelog entry, and run the repository version consistency check.
