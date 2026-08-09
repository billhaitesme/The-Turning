# Lesson 2 — The Nervous System (the FastAPI runtime)

The Core Runtime is a FastAPI application that lives in the backend directory. By default it
listens on port 8000. It is the deterministic authority: the language model produces conversation,
but the runtime alone owns memory, evidence, plans, decisions, and every record that persists.

Every operator surface speaks to this same API. The Command Deck is the web interface where
conversation happens. The desktop Bridge Zero is Mission Control, a read-only operations console.
The native iOS and Android applications are synchronized operator consoles. None of them hold
state of their own; they are windows into the one runtime.

The API is organized into families. Conversation endpoints carry chat. The system status endpoint
reports the runtime's health, Model Lock state, and tool framework state. The memory endpoints
browse and correct the memory store. The tutelage endpoints run study cycles, retention reports,
and gated consolidations. The reflection endpoints run reflection cycles, whose observations only
the reflection pipeline may write.

Mobile clients are protected by a compatibility gate. The runtime reports its version, and a
client whose supported version is too old must show Update Required and disable runtime
operations rather than guess. Release metadata never claims functionality that is not backed by
an authoritative runtime signal.
