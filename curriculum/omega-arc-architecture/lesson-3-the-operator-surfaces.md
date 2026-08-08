# Lesson 3 — The Operator Surfaces

The Command Deck is the web interface where conversation happens. Its panels display the runtime's
real state: identity, evidence, reasoning, planning, deliberation, and trusted adapters. Every
displayed signal traces to an authoritative source in the deterministic runtime; panels that show
nothing are showing an honestly empty store.

The desktop Bridge Zero is Mission Control: a read-only operations console with no chat by design.
It observes the runtime but never commands it. The native operator consoles on iOS and Android are
synchronized to the same runtime and add operator actions: selecting the active model from an
allowlist, starting a new conversation, and deciding approvals.

Operator approvals are the runtime's action gate. When the runtime wants to act, the request waits
for the operator, and approving or denying on a mobile console requires biometric confirmation:
Face ID on iOS and BiometricPrompt on Android. No action bypasses the gate.

The consoles are protected by a compatibility gate. A console whose version is lower than the
required mobile version shows Update Required and disables runtime operations, so an outdated
surface can never misrepresent the runtime.

Anyone can install OMEGA-ARC on Windows with a single installer. It bundles an embedded Python
runtime, the Core Runtime, and both web interfaces, and it installs Ollama when missing. On first
launch the models are downloaded once, with consent, and the browser opens the Command Deck.
