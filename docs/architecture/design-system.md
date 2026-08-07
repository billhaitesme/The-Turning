# Bridge Zero Design System — Cross-Platform Parity

**Status:** Foundation aligned; adoption in progress. Pending native-build validation.

The single source of truth is [`bridge/shared/mobile/design-tokens.json`](../../bridge/shared/mobile/design-tokens.json).
Each native platform mirrors those values; no platform may invent a divergent value for a token
that the shared file defines. This document records the mapping and the small set of
**intentional** platform-specific differences.

## Token sources

| Token family | Shared JSON | iOS | Android |
|---|---|---|---|
| Colors | `colors` | `BridgeTheme` ([Theme.swift](../../bridge/bridge-zero-ios/Sources/Theme.swift)) | `BridgeDesign.Colors` ([DesignSystem.kt](../../bridge/bridge-zero-android/app/src/main/java/arc/omega/bridgezero/DesignSystem.kt)) |
| Spacing | `spacing` | `BridgeSpacing` | `BridgeDesign.Spacing` |
| Radii | `radii` | `BridgeRadius` | `BridgeDesign.Radius` |
| Typography | `typography` | `BridgeTypography` | `BridgeDesign.Type` |
| Status map | `status` | `StatusBadge` + semantic colors | `BridgeDesign.statusColor` + `StatusBadge` |

## Aligned in this pass

- **iOS surface colors** (`void`, `panel`, `raised`) now derive from the shared hex via a
  `Color(bridgeHex:)` initializer instead of hand-tuned fractional RGB, so they match the shared
  values bit-for-bit. `signal`/`nominal`/`warning`/`failure` use the same initializer.
- **Separator**: iOS previously used `Color.white.opacity(0.12)`; it now uses the shared
  `separator` (`#24333C`), matching Android. The Android `InstrumentPanel` border previously used
  `Color.White.copy(alpha = .1f)` and now uses `BridgeDesign.Colors.Separator`.
- **Typography tokens** (`display`, `title`, `body`, `label`, `metric`) now exist on **both**
  platforms; they did not previously exist as a named set on either.
- **Android status badge**: a shared `StatusBadge` composable and a `statusColor` semantic map
  now exist, closing the gap where Android had no badge component.
- **Shared components** (`InstrumentPanel`, `StatusBadge`, `MetricRow`, plus login/dashboard
  surfaces) now reference the spacing/radius/typography tokens instead of literals **wherever the
  literal exactly equals a token value** (4/8/12/16/24 spacing; 6/8/12 radii). This rule
  guarantees no visual change from tokenization.

## Intentional platform-specific differences

These are deliberate and must not be "fixed" into false uniformity:

1. **`muted` text color** has no shared token. iOS uses `Color.secondary` and Android uses a
   screen-level gray so muted text tracks each OS's Dark Mode / contrast behavior.
2. **Letter spacing units**: the shared `tracking` values are point-based. iOS applies them as
   point `tracking`; Android applies the same numbers as `sp` letter spacing (the natural Compose
   unit). Same numbers, platform-appropriate unit.
3. **Login title** (`BRIDGE ZERO`) on iOS keeps `design: .rounded` as a branding treatment rather
   than the plain `display` token. Content, size, weight, and tracking otherwise match.

## Remaining follow-up (low-risk, mechanical)

- Non-token literals still present by design decision, not defect: values like `10`, `14`, `9`,
  `18`, `28`, `6`-spacing that are **not** in the shared scale were left unchanged rather than
  snapped to the nearest token (that would be an aesthetic redesign, which is out of scope).
- Per-screen token adoption in the remaining iOS views (`ConversationView`, `DiagnosticsView`,
  `DashboardView`, `SettingsView`) and the analogous Android screens is a mechanical follow-up.
  The tokens now exist and are equivalent; adopting them at every remaining call site does not
  change the parity contract.

## Validation gate

Every change above is source-level only. **None has been validated by a native build.** The
design-token parity gate in [`RELEASE_CANDIDATE.md`](../governance/RELEASE_CANDIDATE.md) must not
be marked passed until an iOS and an Android build compile these files and a visual check (or a
generated token-comparison test) confirms equivalence on device.
