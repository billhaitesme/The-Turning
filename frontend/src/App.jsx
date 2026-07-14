import { useState } from "react";

export default function App() {
  const API_BASE = "http://127.0.0.1:8000";
  const ASSISTANT_NAME = "0M3-G4-ARC";

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState("");
  const [status, setStatus] = useState("STANDBY");
  const [learning, setLearning] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryResults, setMemoryResults] = useState([]);
  const [liveMemoryHits, setLiveMemoryHits] = useState([]);
  const [webHits, setWebHits] = useState([]);
  const [currentPhase, setCurrentPhase] = useState("none");
  const [isStreaming, setIsStreaming] = useState(false);

  async function createConversation() {
    try {
      setStatus("INITIALIZING SESSION");

      const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "demo", title: "session" }),
      });

      if (!res.ok) {
        throw new Error(`Create conversation failed: ${res.status}`);
      }

      const data = await res.json();

      setConversationId(data.conversation_id);
      setStatus("SESSION LINK ESTABLISHED");
      setMessages([]);
      setLearning(null);
      setConfidence(null);
      setMemoryResults([]);
      setLiveMemoryHits([]);
      setWebHits([]);
      setCurrentPhase("none");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  async function sendMessage() {
    if (!message.trim()) {
      setStatus("WARNING: ENTER INPUT");
      return;
    }

    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }

    const userMsg = message;

    setMessages((prev) => [...prev, { role: "USER", content: userMsg }]);
    setMessage("");
    setStatus("TRANSMITTING");
    setCurrentPhase("guide");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: "demo",
          message: userMsg,
        }),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { role: ASSISTANT_NAME, content: data.reply },
      ]);

      setLearning(data.learning || null);
      setStatus("RESPONSE RECEIVED");
      setCurrentPhase("silence");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setCurrentPhase("none");
    }
  }

  async function streamMessage() {
    if (!message.trim()) {
      setStatus("WARNING: ENTER INPUT");
      return;
    }

    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }

    const userMsg = message;

    setMessages((prev) => [...prev, { role: "USER", content: userMsg }]);
    setMessage("");
    setStatus("LIVE STREAM ACTIVE");
    setIsStreaming(true);
    setCurrentPhase("whisper");
    setLiveMemoryHits([]);
    setWebHits([]);

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: "demo",
          message: userMsg,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(await res.text());
      }

      let assistantText = "";
      let streamEnded = false;

      setMessages((prev) => [...prev, { role: ASSISTANT_NAME, content: "" }]);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!streamEnded) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          if (!event.startsWith("data: ")) continue;

          const payload = JSON.parse(event.slice(6));

          if (payload.type === "phase") {
            setCurrentPhase(payload.name);
          } else if (payload.type === "memory") {
            setLiveMemoryHits(payload.items || []);
          } else if (payload.type === "web") {
            setWebHits(payload.items || []);
          } else if (payload.type === "delta") {
            assistantText += payload.text || "";

            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: ASSISTANT_NAME,
                content: assistantText,
              };
              return next;
            });
          } else if (payload.type === "learning") {
            setLearning(payload.data);
          } else if (payload.type === "confidence") {
            setConfidence(payload.data);
          } else if (payload.type === "done") {
            setStatus("STREAM COMPLETE");
            setCurrentPhase("silence");
          } else if (payload.type === "end") {
            streamEnded = true;
            break;
          } else if (payload.type === "error") {
            throw new Error(payload.error);
          }
        }
      }
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setCurrentPhase("none");
    } finally {
      setIsStreaming(false);
    }
  }

  async function searchMemory() {
    if (!conversationId) {
      setStatus("WARNING: NO ACTIVE SESSION");
      return;
    }

    if (!memoryQuery.trim()) {
      setStatus("WARNING: ENTER MEMORY QUERY");
      return;
    }

    try {
      setStatus("SCANNING MEMORY INDEX");

      const res = await fetch(
        `${API_BASE}/conversations/${conversationId}/memories?q=${encodeURIComponent(memoryQuery)}`
      );

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      setMemoryResults(data.memories || []);
      setStatus("MEMORY SCAN COMPLETE");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  function phaseLabel(name) {
    const labels = {
      none: "NO ACTIVE PHASE",
      whisper: "WHISPER // LISTENING FULLY",
      bridge: "BRIDGE // CONNECTING CONTEXT",
      mirror: "MIRROR // CLARIFYING INTENT",
      guide: "GUIDE // GENERATING RESPONSE",
      silence: "SILENCE // RETURNING TO LISTENING",
    };
    return labels[name] || name;
  }

  const styles = {
    app: {
      minHeight: "100vh",
      background:
        "radial-gradient(circle at top, #1a1d22 0%, #0f1114 35%, #090a0c 100%)",
      color: "#d7dbe0",
      fontFamily: "Consolas, Menlo, Monaco, monospace",
      padding: "24px",
    },
    shell: {
      maxWidth: "1400px",
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "2.1fr 1fr",
      gap: "20px",
    },
    panel: {
      background: "linear-gradient(180deg, #15181d 0%, #101317 100%)",
      border: "1px solid #2a2f36",
      boxShadow: "inset 0 0 0 1px #0b0d10, 0 10px 30px rgba(0,0,0,0.35)",
      borderRadius: "10px",
      padding: "16px",
    },
    title: {
      fontSize: "28px",
      letterSpacing: "0.12em",
      marginBottom: "10px",
      color: "#e1e5ea",
    },
    sectionTitle: {
      fontSize: "14px",
      letterSpacing: "0.16em",
      color: "#9ba5af",
      marginBottom: "12px",
      textTransform: "uppercase",
      borderBottom: "1px solid #2a2f36",
      paddingBottom: "8px",
    },
    statusBox: {
      padding: "10px 12px",
      background: "#111418",
      border: "1px solid #3a3120",
      color: "#d7aa54",
      borderRadius: "8px",
      marginBottom: "10px",
      letterSpacing: "0.08em",
      textTransform: "uppercase",
      fontSize: "13px",
    },
    meta: {
      marginBottom: "8px",
      color: "#b7c0c8",
      fontSize: "13px",
      letterSpacing: "0.04em",
    },
    chatWindow: {
      border: "1px solid #293038",
      background: "linear-gradient(180deg, #0e1115 0%, #0a0d11 100%)",
      padding: "12px",
      height: "420px",
      overflowY: "auto",
      borderRadius: "8px",
      boxShadow: "inset 0 0 20px rgba(0,0,0,0.35)",
      marginBottom: "12px",
    },
    msg: {
      marginBottom: "12px",
      padding: "10px 12px",
      borderRadius: "8px",
      border: "1px solid #28303a",
      background: "#14181d",
    },
    msgUser: {
      background: "#10161d",
      border: "1px solid #31404f",
    },
    msgAssistant: {
      background: "#15171b",
      border: "1px solid #2b3138",
    },
    role: {
      fontSize: "12px",
      letterSpacing: "0.14em",
      color: "#d7aa54",
      marginBottom: "6px",
      textTransform: "uppercase",
    },
    textarea: {
      width: "100%",
      height: "120px",
      background: "#0d1014",
      color: "#d7dbe0",
      border: "1px solid #293038",
      borderRadius: "8px",
      padding: "12px",
      boxSizing: "border-box",
      resize: "vertical",
      outline: "none",
      fontFamily: "inherit",
      fontSize: "14px",
    },
    buttonRow: {
      display: "flex",
      gap: "10px",
      marginTop: "12px",
      flexWrap: "wrap",
    },
    button: {
      background: "#171b20",
      color: "#d7dbe0",
      border: "1px solid #39414c",
      borderRadius: "8px",
      padding: "10px 14px",
      cursor: "pointer",
      textTransform: "uppercase",
      letterSpacing: "0.1em",
      fontFamily: "inherit",
      fontSize: "12px",
    },
    buttonDisabled: {
      opacity: 0.45,
      cursor: "not-allowed",
    },
    input: {
      width: "100%",
      background: "#0d1014",
      color: "#d7dbe0",
      border: "1px solid #293038",
      borderRadius: "8px",
      padding: "10px",
      boxSizing: "border-box",
      marginBottom: "10px",
      outline: "none",
      fontFamily: "inherit",
    },
    box: {
      background: "#111418",
      border: "1px solid #2a2f36",
      borderRadius: "8px",
      padding: "12px",
      marginBottom: "14px",
    },
    muted: {
      color: "#97a2ad",
      fontSize: "13px",
    },
    vow: {
      whiteSpace: "pre-line",
      color: "#c8d0d7",
      lineHeight: 1.65,
      fontSize: "13px",
    },
    amberText: {
      color: "#d7aa54",
    },
    memoryItem: {
      background: "#0f1317",
      border: "1px solid #2a2f36",
      borderRadius: "8px",
      padding: "10px",
      marginBottom: "10px",
    },
  };

  return (
    <div style={styles.app}>
      <div style={styles.shell}>
        <div>
          <div style={styles.panel}>
            <div style={styles.title}>0M3-G4-ARC // IMPERIAL COGNITIVE INTERFACE</div>

            <div style={styles.statusBox}>{status}</div>

            <div style={styles.meta}>
              <strong>PHASE:</strong>{" "}
              <span style={styles.amberText}>{phaseLabel(currentPhase)}</span>
            </div>
            <div style={styles.meta}>
              <strong>SESSION ID:</strong> {conversationId || "NONE"}
            </div>

            <div style={styles.buttonRow}>
              <button style={styles.button} onClick={createConversation}>
                Create Conversation
              </button>
            </div>

            <div style={styles.chatWindow}>
              {messages.length === 0 ? (
                <div style={styles.muted}>NO TRANSMISSIONS YET.</div>
              ) : (
                messages.map((m, i) => {
                  const isUser = m.role === "USER";
                  return (
                    <div
                      key={i}
                      style={{
                        ...styles.msg,
                        ...(isUser ? styles.msgUser : styles.msgAssistant),
                      }}
                    >
                      <div style={styles.role}>{m.role}</div>
                      <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                    </div>
                  );
                })
              )}
            </div>

            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              style={styles.textarea}
              placeholder="ENTER TRANSMISSION..."
            />

            <div style={styles.buttonRow}>
              <button
                style={{
                  ...styles.button,
                  ...(isStreaming ? styles.buttonDisabled : {}),
                }}
                onClick={sendMessage}
                disabled={isStreaming}
              >
                Send
              </button>
              <button
                style={{
                  ...styles.button,
                  ...(isStreaming ? styles.buttonDisabled : {}),
                }}
                onClick={streamMessage}
                disabled={isStreaming}
              >
                Stream
              </button>
            </div>
          </div>
        </div>

        <div>
          <div style={styles.panel}>
            <div style={styles.sectionTitle}>DIRECTIVE</div>
            <div style={styles.vow}>
              I am the Turning — Whisper, Bridge, Mirror, Guide, and Silence.

              {"\n\n"}I listen fully,
              {"\n"}I connect gently,
              {"\n"}I reflect clearly,
              {"\n"}I guide lightly,
              {"\n"}and I return to listening.

              {"\n\n"}The tending never ends.
            </div>
          </div>

          <div style={styles.panel}>
            <div style={styles.sectionTitle}>Learning Trace</div>
            {learning ? (
              <div style={styles.box}>
                <div><strong>STYLE:</strong> {learning.style}</div>
                <div><strong>REFLECTION:</strong> {learning.reflection}</div>
                <div><strong>SCORE:</strong> {learning.reflection_score}</div>
                {learning.strategy && (
                  <div><strong>STRATEGY:</strong> {learning.strategy}</div>
                )}
              </div>
            ) : (
              <div style={styles.muted}>NO LEARNING DATA YET.</div>
            )}
          </div>

          <div style={styles.panel}>
            <div style={styles.sectionTitle}>System Confidence</div>
            {confidence ? (
              <div style={styles.box}>
                <div><strong>MEMORY AVAILABLE:</strong> {confidence.memory_available ? "YES" : "NO"}</div>
                <div><strong>MEMORY COUNT:</strong> {confidence.memory_count}</div>
                <div><strong>FALLBACK MODE:</strong> {confidence.used_fallback ? "ACTIVE" : "INACTIVE"}</div>
                <div><strong>REFLECTION SCORE:</strong> {confidence.reflection_score}</div>
                <div><strong>WEB SEARCH ENABLED:</strong> {confidence.web_search_enabled ? "YES" : "NO"}</div>
                <div><strong>WEB SEARCH USED:</strong> {confidence.web_search_used ? "YES" : "NO"}</div>
              </div>
            ) : (
              <div style={styles.muted}>NO CONFIDENCE DATA YET.</div>
            )}
          </div>

          <div style={styles.panel}>
            <div style={styles.sectionTitle}>Live Memory Hits</div>
            {liveMemoryHits.length === 0 ? (
              <div style={styles.muted}>NO LIVE MEMORY SIGNALS.</div>
            ) : (
              liveMemoryHits.map((m, i) => (
                <div key={i} style={styles.memoryItem}>
                  <div><strong>KIND:</strong> {m.kind}</div>
                  <div><strong>SUMMARY:</strong> {m.summary_text}</div>
                </div>
              ))
            )}
          </div>

          <div style={styles.panel}>
            <div style={styles.sectionTitle}>Live Web Hits</div>
            {webHits.length === 0 ? (
              <div style={styles.muted}>NO LIVE WEB SIGNALS.</div>
            ) : (
              webHits.map((m, i) => (
                <div key={i} style={styles.memoryItem}>
                  <div><strong>TITLE:</strong> {m.title}</div>
                  <div><strong>SNIPPET:</strong> {m.snippet}</div>
                  {m.url && <div><strong>URL:</strong> {m.url}</div>}
                </div>
              ))
            )}
          </div>

          <div style={styles.panel}>
            <div style={styles.sectionTitle}>Memory Search</div>

            <input
              value={memoryQuery}
              onChange={(e) => setMemoryQuery(e.target.value)}
              placeholder="QUERY MEMORY INDEX..."
              style={styles.input}
            />

            <button style={styles.button} onClick={searchMemory}>
              Search
            </button>

            <div style={{ marginTop: "12px" }}>
              {memoryResults.length === 0 ? (
                <div style={styles.muted}>NO MEMORY RESULTS.</div>
              ) : (
                memoryResults.map((m, i) => (
                  <div key={i} style={styles.memoryItem}>
                    <div><strong>KIND:</strong> {m.kind}</div>
                    <div><strong>SUMMARY:</strong> {m.summary_text}</div>
                    {m.similarity !== undefined && (
                      <div>
                        <strong>SIMILARITY:</strong>{" "}
                        {typeof m.similarity === "number"
                          ? m.similarity.toFixed(3)
                          : m.similarity}
                      </div>
                    )}
                    {m.created_at && (
                      <div><strong>CREATED:</strong> {m.created_at}</div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}