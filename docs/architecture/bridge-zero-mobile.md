# Bridge Zero Mobile — Epoch IX

**Release line:** Version 0.2.x (current 0.2.0)

Bridge Zero Mobile is an operator console for the existing Core Runtime. Desktop Bridge Zero remains Mission Control. Mobile clients do not own inference, select substitute models, rewrite responses, or manufacture runtime activity.

## Runtime boundary

The additive `/api/mobile/v1` router projects existing state and delegates conversation streaming to the established `/chat/stream` implementation. This preserves the selected model, Model Lock, cognition pipeline, persistence, and SSE behavior.

Authentication is fail-closed. Set `MOBILE_AUTH_TOKEN` to a long random secret before mobile access is enabled. Tokens are accepted only as bearer headers and are never included in errors or logs.

## Repository layout

- `backend/routes/mobile.py` — authenticated transport adapter
- `bridge/bridge-zero-ios` — SwiftUI operator console
- `bridge/bridge-zero-android` — Jetpack Compose operator console
- `bridge/shared/mobile` — API contract and Chronicle data

## Epoch IX-A

The native clients provide connection/login, version gating, live status, synchronized conversation history, SSE responses, read-only diagnostics, settings, logs, and Chronicle. UI state is derived from runtime responses. There is no simulated typing or fabricated telemetry.

## Network and security

Production deployments should terminate HTTPS at the Core Runtime or a trusted reverse proxy. Platform TLS validation remains enabled. The iOS app uses Keychain; Android uses EncryptedSharedPreferences backed by Android Keystore. Cleartext traffic is not globally enabled.

## Compatibility

Clients support mobile API major `1` and app version `0.2.0`. A different API major or a `required_mobile_version` newer than the installed application presents **Update Required** and disables runtime features.

## Synchronization

`GET /conversations/active` returns the most recently updated Core Runtime session, which lets mobile resume a conversation started on desktop. All streamed messages are persisted by the existing chat path.

## Epoch IX-B — Runtime Operations

IX-B is active. The shared RuntimeStore now consumes measured CPU, RAM, connected-client, queue, session, latency, streaming, and Chronicle telemetry. Typed SSE events and native event buses provide the foundation for live runtime updates, while the Operations Dashboard exposes only authoritative values.

## Future phases

IX-C will add registered push devices and short-lived approval challenges with biometric confirmation. IX-D will evolve the authoritative signals into the full command console. Both remain documented future work only.
