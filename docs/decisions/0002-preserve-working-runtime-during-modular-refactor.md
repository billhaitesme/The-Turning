# ADR 0002: Preserve the Working Runtime During Modular Refactor

## Status
Accepted

## Decision
Add modular components beside the working `app.py`. Do not replace the live runtime until each subsystem has tests, an integration point, and a rollback path.

## Rollback
Delete the new modules and continue using the original `app.py`.
