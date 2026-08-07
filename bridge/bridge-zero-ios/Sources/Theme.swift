import SwiftUI

extension Color {
    /// Exact sRGB value from a shared design-token hex string such as "#071016".
    /// Keeps the SwiftUI palette bit-for-bit aligned with
    /// `bridge/shared/mobile/design-tokens.json` instead of hand-tuned fractions.
    init(bridgeHex hex: String) {
        let raw = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        let value = UInt64(raw, radix: 16) ?? 0
        let red = Double((value >> 16) & 0xFF) / 255.0
        let green = Double((value >> 8) & 0xFF) / 255.0
        let blue = Double(value & 0xFF) / 255.0
        self.init(.sRGB, red: red, green: green, blue: blue, opacity: 1)
    }
}

/// Colors mirror `bridge/shared/mobile/design-tokens.json` exactly.
enum BridgeTheme {
    static let void = Color(bridgeHex: "#071016")
    static let panel = Color(bridgeHex: "#0E171D")
    static let raised = Color(bridgeHex: "#15232B")
    /// Shared token name is `separator`; exposed as `line` for existing call sites.
    static let line = Color(bridgeHex: "#24333C")
    static let signal = Color(bridgeHex: "#38D1E8")
    static let nominal = Color(bridgeHex: "#57D492")
    static let warning = Color(bridgeHex: "#F2AD40")
    static let failure = Color(bridgeHex: "#F05252")
    /// Platform-specific: the shared token set has no `muted` color. iOS defers to the
    /// system secondary label so muted text tracks Dark Mode/contrast settings. Android
    /// makes the same choice with its screen-level muted gray. Documented intentional difference.
    static let muted = Color.secondary
}

enum BridgeSpacing {
    static let xs: CGFloat = 4
    static let sm: CGFloat = 8
    static let md: CGFloat = 12
    static let lg: CGFloat = 16
    static let xl: CGFloat = 24
}

enum BridgeRadius {
    static let badge: CGFloat = 6
    static let control: CGFloat = 8
    static let card: CGFloat = 12
}

/// Typography tokens mirroring the shared `typography` map. SwiftUI applies letter
/// spacing (`tracking`) as a view modifier rather than on `Font`, so each token exposes
/// both its `Font` and its tracking value.
enum BridgeTypography {
    static let display = Font.system(size: 34, weight: .bold)
    static let title = Font.system(size: 22, weight: .bold)
    static let body = Font.system(size: 16, weight: .regular)
    static let label = Font.system(size: 12, weight: .semibold)
    static let metric = Font.system(size: 16, weight: .regular, design: .monospaced)

    static let displayTracking: CGFloat = 2
    static let titleTracking: CGFloat = 1.5
    static let bodyTracking: CGFloat = 0
    static let labelTracking: CGFloat = 1.4
    static let metricTracking: CGFloat = 0
}

struct InstrumentPanel<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    init(title: String, @ViewBuilder content: @escaping () -> Content) {
        self.title = title
        self.content = content
    }

    var body: some View {
        VStack(alignment: .leading, spacing: BridgeSpacing.md) {
            Text(title.uppercased())
                .font(BridgeTypography.label)
                .tracking(BridgeTypography.labelTracking)
                .foregroundStyle(BridgeTheme.signal)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(BridgeSpacing.lg)
        .background(BridgeTheme.panel, in: RoundedRectangle(cornerRadius: BridgeRadius.card))
        .overlay(RoundedRectangle(cornerRadius: BridgeRadius.card).stroke(BridgeTheme.line))
    }
}

struct StatusLamp: View {
    let color: Color
    let label: String

    var body: some View {
        HStack(spacing: BridgeSpacing.sm) {
            Circle().fill(color).frame(width: 8, height: 8)
                .shadow(color: color.opacity(0.6), radius: 5)
            Text(label.uppercased())
                .font(.caption.monospaced().weight(.semibold))
        }
    }
}

struct StatusBadge: View {
    let label: String
    let color: Color

    var body: some View {
        Text(label.uppercased())
            .font(.caption2.monospaced().weight(.bold))
            .foregroundStyle(color)
            .padding(.horizontal, BridgeSpacing.sm)
            .padding(.vertical, BridgeSpacing.xs)
            .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: BridgeRadius.badge))
            .overlay(RoundedRectangle(cornerRadius: BridgeRadius.badge).stroke(color.opacity(0.35)))
    }
}

struct MetricRow: View {
    let label: String
    let value: String
    var accent: Color = .primary

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label).foregroundStyle(.secondary)
            Spacer(minLength: BridgeSpacing.md)
            Text(value)
                .foregroundStyle(accent)
                .font(BridgeTypography.metric)
                .multilineTextAlignment(.trailing)
        }
        .accessibilityElement(children: .combine)
    }
}
