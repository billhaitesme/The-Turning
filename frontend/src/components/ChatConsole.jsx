// The Command Channel (chat) — hook + view, shared by the main bridge and the pop-out companion.
// XIII-A: the stream now carries tool_call / tool_result events (the agent loop's hops); they
// render live on an LED trace strip and persist as chips on the message they belong to.
import { useEffect, useRef, useState } from "react";
import { SystemBadge, fmtDateTime, phaseLabel } from "./displays.jsx";

export const API_BASE = "http://127.0.0.1:8001";
export const ASSISTANT_NAME = "0M3-G4-ARC";
const CONVERSATION_KEY = "omega-arc.conversation.v1";

export function useChatChannel({ playCue = () => {}, onPhase = () => {} } = {}) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState("");
  const [conversationMode, setConversationMode] = useState("runtime");
  const [status, setStatus] = useState("STANDBY");
  const [learning, setLearning] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryResults, setMemoryResults] = useState([]);
  const [liveMemoryHits, setLiveMemoryHits] = useState([]);
  const [webHits, setWebHits] = useState([]);
  const [currentPhase, setCurrentPhase] = useState("none");
  const [isStreaming, setIsStreaming] = useState(false);
  const [loopTrace, setLoopTrace] = useState([]);
  const [directModel, setDirectModel] = useState("");
  const [recents, setRecents] = useState([]);
  const [pendingImages, setPendingImages] = useState([]);
  const [voiceOut, setVoiceOut] = useState(false);
  const [recording, setRecording] = useState(false);
  const adoptedRef = useRef(false);
  const voiceOutRef = useRef(false);
  const recorderRef = useRef(null);

  function toggleVoiceOut() {
    setVoiceOut((prev) => {
      voiceOutRef.current = !prev;
      return !prev;
    });
  }

  async function speakReply(text) {
    if (!voiceOutRef.current || !text) return;
    try {
      const res = await fetch(`${API_BASE}/voice/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.slice(0, 1200) }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const audio = new Audio(URL.createObjectURL(blob));
      audio.play().catch(() => {});
    } catch { /* the mouth failing is never fatal */ }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        if (blob.size < 1000) return; // a tap, not speech
        setStatus("TRANSCRIBING…");
        try {
          const res = await fetch(`${API_BASE}/voice/transcribe`, { method: "POST", body: blob });
          const data = await res.json();
          if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
          if (data.text) {
            setMessage(data.text);
            setStatus("HEARD — TRANSMIT TO SEND");
          } else {
            setStatus("HEARD NOTHING");
          }
        } catch (err) {
          setStatus(`WARNING: ${err.message}`);
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      setStatus("LISTENING…");
    } catch (err) {
      setStatus(`WARNING: microphone — ${err.message}`);
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
    }
  }

  function attachImages(fileList) {
    const files = Array.from(fileList || []).slice(0, 4 - pendingImages.length);
    files.forEach((file) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = () => {
        setPendingImages((prev) => prev.length < 4 ? [...prev, { dataUrl: reader.result, name: file.name }] : prev);
      };
      reader.readAsDataURL(file);
    });
  }

  async function loadRecents() {
    try {
      const res = await fetch(`${API_BASE}/conversations?limit=12`);
      if (!res.ok) return;
      const data = await res.json();
      setRecents(data.conversations || []);
    } catch { /* recents are a convenience, never an error state */ }
  }

  const setPhase = (name) => {
    setCurrentPhase(name);
    onPhase(name);
  };

  async function adoptConversation(cid) {
    try {
      const res = await fetch(`${API_BASE}/conversations/${cid}`);
      if (!res.ok) return false;
      const data = await res.json();
      setConversationId(cid);
      setMessages(
        (data.messages || []).map((m) => ({
          role: String(m.role).toLowerCase() === "user" ? "USER" : ASSISTANT_NAME,
          content: m.content,
        }))
      );
      setStatus("CHANNEL ADOPTED");
      return true;
    } catch {
      return false;
    }
  }

  useEffect(() => {
    // Direct-mode label is read from the runtime, never hardcoded (the old constant drifted).
    fetch(`${API_BASE}/system/config`)
      .then((r) => (r.ok ? r.json() : null))
      .then((cfg) => setDirectModel(cfg?.direct_chat_model || ""))
      .catch(() => {});

    if (!adoptedRef.current) {
      adoptedRef.current = true;
      const stored = window.localStorage.getItem(CONVERSATION_KEY);
      if (stored) adoptConversation(stored);
      loadRecents();
    }

    // The companion and the main bridge share one session: when either creates a conversation,
    // the other adopts it on the storage event.
    const onStorage = (event) => {
      if (event.key === CONVERSATION_KEY && event.newValue) {
        adoptConversation(event.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  async function createConversation() {
    try {
      setStatus("INITIALIZING SESSION");
      const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "demo", title: "session" }),
      });
      if (!res.ok) throw new Error(`Create conversation failed: ${res.status}`);
      const data = await res.json();
      setConversationId(data.conversation_id);
      try {
        window.localStorage.setItem(CONVERSATION_KEY, data.conversation_id);
      } catch { /* non-fatal */ }
      setStatus("CHANNEL OPEN");
      setMessages([]);
      setLearning(null);
      setConfidence(null);
      setMemoryResults([]);
      setLiveMemoryHits([]);
      setWebHits([]);
      setLoopTrace([]);
      setPhase("none");
      loadRecents();
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  async function resumeConversation(cid) {
    const ok = await adoptConversation(cid);
    if (ok) {
      try {
        window.localStorage.setItem(CONVERSATION_KEY, cid);
      } catch { /* non-fatal */ }
      setLoopTrace([]);
    }
  }

  function appendHop(hop) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (!last || last.role === "USER") return prev;
      const hops = [...(last.hops || [])];
      const openIndex = hops.findIndex((h) => h.name === hop.name && h.status === "calling");
      if (hop.status !== "calling" && openIndex >= 0) {
        hops[openIndex] = hop;
      } else {
        hops.push(hop);
      }
      next[next.length - 1] = { ...last, hops };
      return next;
    });
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
    const imagesToSend = pendingImages.map((p) => p.dataUrl);
    setMessages((prev) => [...prev, { role: "USER", content: userMsg,
                                      images: pendingImages.map((p) => p.dataUrl) }]);
    setPendingImages([]);
    setMessage("");
    setStatus(conversationMode === "direct" ? "DIRECT MODEL" : "CHANNEL OPEN");
    setIsStreaming(true);
    setLoopTrace([]);
    if (conversationMode === "direct") {
      setPhase("none");
    } else {
      setPhase("whisper");
    }
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
          mode: conversationMode,
          images: imagesToSend.length ? imagesToSend : undefined,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(await res.text());
      }

      let assistantText = "";
      let streamEnded = false;
      const responseRole = conversationMode === "direct" ? (directModel || "DIRECT") : ASSISTANT_NAME;
      setMessages((prev) => [...prev, { role: responseRole, content: "", hops: [] }]);

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
            setPhase(payload.name);
          } else if (payload.type === "memory") {
            setLiveMemoryHits(payload.items || []);
          } else if (payload.type === "web") {
            setWebHits(payload.items || []);
          } else if (payload.type === "tool_call") {
            // XIII-A: the seat asked; the runtime is resolving it against the registry.
            setLoopTrace((prev) => [...prev, { kind: "call", name: payload.name, at: Date.now() }]);
            appendHop({ name: payload.name, status: "calling" });
            playCue("ack");
          } else if (payload.type === "tool_result") {
            setLoopTrace((prev) => [...prev, { kind: "result", name: payload.name, status: payload.status, at: Date.now() }]);
            appendHop({ name: payload.name, status: payload.status || "unknown" });
            playCue(payload.status === "executed" ? "verified" : "chronicle");
          } else if (payload.type === "delta") {
            assistantText += payload.text || "";
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, role: responseRole, content: assistantText };
              return next;
            });
          } else if (payload.type === "learning") {
            setLearning(payload.data);
          } else if (payload.type === "confidence") {
            setConfidence(payload.data);
          } else if (payload.type === "done") {
            setStatus(conversationMode === "direct" ? "DIRECT COMPLETE" : "STREAM COMPLETE");
            setPhase(conversationMode === "direct" ? "none" : "silence");
            playCue("completion");
            speakReply(payload.text || assistantText);
          } else if (payload.type === "mode" && payload.name === "direct") {
            setStatus(`DIRECT // ${payload.model || directModel}`);
          } else if (payload.type === "end") {
            streamEnded = true;
          } else if (payload.type === "error") {
            throw new Error(payload.error);
          }
        }
      }
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setPhase("none");
    } finally {
      setIsStreaming(false);
      loadRecents();
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
    setStatus(conversationMode === "direct" ? "DIRECT MODEL" : "CHANNEL OPEN");
    setPhase(conversationMode === "direct" ? "none" : "guide");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: "demo",
          message: userMsg,
          mode: conversationMode,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const responseRole = conversationMode === "direct" ? (directModel || "DIRECT") : ASSISTANT_NAME;
      setMessages((prev) => [...prev, { role: responseRole, content: data.reply }]);
      setLearning(data.learning || null);
      setStatus(conversationMode === "direct" ? "DIRECT COMPLETE" : "LINK ESTABLISHED");
      setPhase(conversationMode === "direct" ? "none" : "silence");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
      setPhase("none");
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
      const res = await fetch(`${API_BASE}/conversations/${conversationId}/memories?q=${encodeURIComponent(memoryQuery)}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setMemoryResults(data.memories || []);
      setStatus("MEMORY SCAN COMPLETE");
    } catch (err) {
      setStatus(`WARNING: ${err.message}`);
    }
  }

  return {
    message, setMessage,
    messages,
    conversationId,
    conversationMode, setConversationMode,
    status,
    learning,
    confidence,
    memoryQuery, setMemoryQuery,
    memoryResults,
    liveMemoryHits,
    webHits,
    currentPhase,
    isStreaming,
    loopTrace,
    directModel,
    recents,
    loadRecents,
    resumeConversation,
    createConversation,
    sendMessage,
    streamMessage,
    searchMemory,
    pendingImages, setPendingImages, attachImages,
    voiceOut, toggleVoiceOut,
    recording, startRecording, stopRecording,
  };
}

function hopTone(status) {
  if (status === "executed") return "green";
  if (status === "awaiting_approval") return "violet";
  if (status === "calling") return "cyan";
  if (status === "refused" || status === "failed") return "red";
  return "steel";
}

function hopLabel(hop) {
  const state = hop.status === "calling" ? "…"
    : hop.status === "awaiting_approval" ? "AWAITING BIOMETRIC"
      : String(hop.status || "").toUpperCase();
  return `${hop.name} ${state ? `// ${state}` : ""}`;
}

export function LoopTraceStrip({ trace, active }) {
  if (!trace.length && !active) return null;
  const entries = trace.slice(-10);
  return (
    <div className={`loop-trace ${active ? "is-live" : ""}`} aria-label="Agent loop trace">
      <span className="loop-trace-tag">LOOP TRACE</span>
      <div className="loop-trace-window">
        <div className="loop-trace-track">
          {(entries.length ? entries : [{ kind: "idle" }]).map((entry, i) => (
            <span key={i} className={`loop-trace-entry tone-${entry.kind === "result" ? hopTone(entry.status) : "cyan"}`}>
              {entry.kind === "idle"
                ? "AWAITING TOOL ACTIVITY"
                : entry.kind === "call"
                  ? `⚙ ${entry.name} → RUNTIME`
                  : `⚙ ${entry.name} → ${entry.status === "awaiting_approval" ? "AWAITING BIOMETRIC" : String(entry.status).toUpperCase()}`}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ChatConsoleView({ chat, telemetry = null, onPopout = null, compact = false }) {
  const {
    message, setMessage, messages, conversationId, conversationMode, setConversationMode,
    status, memoryQuery, setMemoryQuery, memoryResults, isStreaming, loopTrace,
    directModel, recents, resumeConversation, createConversation, sendMessage, streamMessage,
    searchMemory, pendingImages, setPendingImages, attachImages,
    voiceOut, toggleVoiceOut, recording, startRecording, stopRecording,
  } = chat;
  const chatWindowRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const node = chatWindowRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages]);

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isStreaming) streamMessage();
    }
  };

  return (
    <>
      <div className="console-status">
        <SystemBadge label="Status" value={status} />
        <SystemBadge label="Session" value={conversationId ? conversationId.slice(0, 12) : "NONE"} />
        <SystemBadge label="Streaming" value={isStreaming ? "ACTIVE" : "IDLE"} />
      </div>
      {telemetry ? (
        <div className={`comm-plates ${isStreaming ? "is-live" : ""}`}>
          <small>COMM CHANNEL // BZ-COMM-01</small>
          <small>SYNC {telemetry.endpoint_up}/{telemetry.endpoint_total} // LAT {telemetry.poll_ms}ms // CRC OK</small>
        </div>
      ) : null}
      <div className={`conversation-mode ${conversationMode === "direct" ? "is-direct" : ""}`}>
        <div className="conversation-mode-buttons" role="group" aria-label="Conversation mode">
          <button
            className={conversationMode === "runtime" ? "is-active" : ""}
            onClick={() => setConversationMode("runtime")}
            disabled={isStreaming}
          >
            Runtime
          </button>
          <button
            className={conversationMode === "direct" ? "is-active" : ""}
            onClick={() => setConversationMode("direct")}
            disabled={isStreaming}
          >
            Direct Model
          </button>
          {onPopout ? (
            <button type="button" className="popout-button" onClick={onPopout} title="Open companion window">
              ⧉ Companion
            </button>
          ) : null}
        </div>
        {!compact ? (
          <small>
            {conversationMode === "direct"
              ? `PINNED ${directModel || "--"} // RAW HISTORY + INPUT // NO RUNTIME SUBSYSTEMS`
              : "OMEGA-ARC RUNTIME // AGENT LOOP + DETERMINISTIC SUBSYSTEMS"}
          </small>
        ) : null}
      </div>
      {recents.length ? (
        <div className="recents-rail" aria-label="Recent conversations">
          <small>RECENTS</small>
          <div className="recents-track">
            {recents.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`recent-chip ${item.id === conversationId ? "is-current" : ""}`}
                title={item.preview || item.id}
                disabled={isStreaming}
                onClick={() => resumeConversation(item.id)}
              >
                <span>{fmtDateTime(item.updated_at || item.created_at)}</span>
                <strong>{item.preview || item.title || item.id.slice(0, 8)}</strong>
                <span>{item.message_count} MSG</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
      <LoopTraceStrip trace={loopTrace} active={isStreaming && conversationMode !== "direct"} />
      <div ref={chatWindowRef} className={`chat-window ${isStreaming ? "is-streaming" : ""} ${compact ? "is-compact" : ""}`}>
        {messages.length === 0 ? (
          <div className="empty">
            {conversationId ? "NO TRANSMISSIONS YET." : "NO ACTIVE SESSION — OPEN A CHANNEL."}
          </div>
        ) : null}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role === "USER" ? "user" : "assistant"}`}>
            <div className="role">{m.role}</div>
            {m.images?.length ? (
              <div className="chat-images">
                {m.images.map((src, j) => <img key={j} src={src} alt="attached" />)}
              </div>
            ) : null}
            {m.hops?.length ? (
              <div className="chat-hops">
                {m.hops.map((hop, j) => (
                  <span key={j} className={`chat-hop tone-${hopTone(hop.status)}`}>⚙ {hopLabel(hop)}</span>
                ))}
              </div>
            ) : null}
            <div className="content">{m.content}</div>
          </div>
        ))}
      </div>
      {pendingImages.length ? (
        <div className="pending-images">
          {pendingImages.map((img, i) => (
            <div key={i} className="pending-thumb">
              <img src={img.dataUrl} alt={img.name} />
              <button type="button" title="Remove"
                      onClick={() => setPendingImages((prev) => prev.filter((_, j) => j !== i))}>✕</button>
            </div>
          ))}
          <small>ATTACHED — THE SEAT SEES THEM VIA look_at_image</small>
        </div>
      ) : null}
      <div className="command-line">&gt;</div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={recording ? "LISTENING…" : "ENTER TRANSMISSION..."}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          attachImages(e.target.files);
          e.target.value = "";
        }}
      />
      <div className="console-buttons">
        {!conversationId ? <button onClick={createConversation}>Open Channel</button> : null}
        {conversationId ? <button onClick={createConversation} disabled={isStreaming}>New Channel</button> : null}
        <button onClick={streamMessage} disabled={isStreaming}>Transmit</button>
        <button type="button" title="Attach image(s) — show it things"
                onClick={() => fileInputRef.current?.click()} disabled={isStreaming}>📷 Show</button>
        <button
          type="button"
          className={`mic-button ${recording ? "is-recording" : ""}`}
          title="Hold to talk"
          onPointerDown={startRecording}
          onPointerUp={stopRecording}
          onPointerLeave={() => recording && stopRecording()}
          disabled={isStreaming}
        >
          {recording ? "● REC" : "🎙 Talk"}
        </button>
        <button type="button" className={`voice-toggle ${voiceOut ? "is-on" : ""}`}
                title="Speak replies aloud (Kokoro, local)" onClick={toggleVoiceOut}>
          {voiceOut ? "🔊 Voice ON" : "🔇 Voice"}
        </button>
        {!compact ? <button onClick={sendMessage} disabled={isStreaming}>Send (no stream)</button> : null}
      </div>
      {!compact ? (
        <>
          <div className="memory-search">
            <input value={memoryQuery} onChange={(e) => setMemoryQuery(e.target.value)} placeholder="QUERY MEMORY INDEX..." />
            <button onClick={searchMemory}>Search</button>
          </div>
          <div className="memory-results">
            {memoryResults.slice(0, 4).map((m, i) => (
              <div key={i} className="memory-item">
                <strong>{m.kind}</strong>
                <p>{m.summary_text}</p>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}
