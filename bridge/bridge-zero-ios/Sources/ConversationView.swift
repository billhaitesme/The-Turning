import SwiftUI

struct ConversationView: View {
    @EnvironmentObject private var state: OperatorConsoleState

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(state.conversation?.messages ?? []) { message in
                            MessagePlate(role: message.role, content: message.content)
                                .id(message.id)
                        }
                        if !state.streamingText.isEmpty || state.runtimePhase != nil {
                            MessagePlate(
                                role: .runtime,
                                content: state.streamingText,
                                phase: state.runtimePhase
                            ).id("stream")
                        }
                    }.padding(16)
                }
                .onChange(of: state.conversation?.messages.count) { _, _ in
                    if let id = state.conversation?.messages.last?.id { proxy.scrollTo(id, anchor: .bottom) }
                }
                .onChange(of: state.streamingText) { _, _ in proxy.scrollTo("stream", anchor: .bottom) }
            }

            Divider()
            HStack(alignment: .bottom, spacing: 10) {
                TextField("Operator command", text: $state.composerText, axis: .vertical)
                    .lineLimit(1...6)
                    .padding(11)
                    .background(BridgeTheme.raised, in: RoundedRectangle(cornerRadius: 10))
                    .accessibilityLabel("Operator message")
                Button(action: state.sendMessage) {
                    Image(systemName: "arrow.up.circle.fill").font(.system(size: 32))
                }
                .disabled(state.composerText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || state.isStreaming || !state.isConnected)
                .accessibilityLabel("Transmit")
            }.padding(12)
        }
        .background(BridgeTheme.void)
        .navigationTitle("Conversation")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                if state.isStreaming { ProgressView().accessibilityLabel("Runtime streaming") }
            }
        }
    }
}

struct MessagePlate: View {
    let role: RuntimeMessage.Role
    let content: String
    var phase: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(roleLabel).font(.caption.monospaced().weight(.bold)).foregroundStyle(roleColor)
                Spacer()
                if let phase {
                    Label(phase.uppercased(), systemImage: "waveform")
                        .font(.caption2.monospaced()).foregroundStyle(BridgeTheme.warning)
                }
            }
            if content.isEmpty {
                Text("Runtime phase reported; awaiting response data.")
                    .font(.footnote).foregroundStyle(.secondary)
            } else {
                MarkdownContent(content: content)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(role == .operator ? BridgeTheme.raised : BridgeTheme.panel, in: RoundedRectangle(cornerRadius: 10))
        .overlay(alignment: .leading) { Rectangle().fill(roleColor).frame(width: 2).padding(.vertical, 8) }
    }

    private var roleLabel: String {
        switch role { case .operator: "OPERATOR"; case .runtime: "CORE RUNTIME"; case .system: "SYSTEM" }
    }
    private var roleColor: Color {
        switch role { case .operator: BridgeTheme.signal; case .runtime: BridgeTheme.nominal; case .system: BridgeTheme.warning }
    }
}

struct MarkdownContent: View {
    let content: String

    var body: some View {
        let blocks = content.components(separatedBy: "```")
        VStack(alignment: .leading, spacing: 8) {
            ForEach(blocks.indices, id: \.self) { index in
                let block = blocks[index]
                if index.isMultiple(of: 2) {
                    if let attributed = try? AttributedString(markdown: block) {
                        Text(attributed).textSelection(.enabled)
                    } else { Text(block).textSelection(.enabled) }
                } else {
                    ScrollView(.horizontal) {
                        Text(block.trimmingCharacters(in: .newlines))
                            .font(.system(.callout, design: .monospaced)).textSelection(.enabled)
                            .padding(10)
                    }
                    .background(Color.black.opacity(0.35), in: RoundedRectangle(cornerRadius: 7))
                }
            }
        }
    }
}
