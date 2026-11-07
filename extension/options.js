// Options page: store the backend URL and pairing token, then prove the pairing with /browser/hello.
const $ = (id) => document.getElementById(id);

async function load() {
  const s = await chrome.storage.local.get(["backend", "token"]);
  $("backend").value = s.backend || "http://127.0.0.1:8001";
  $("token").value = s.token || "";
}

async function saveAndTest() {
  const backend = $("backend").value.trim().replace(/\/+$/, "") || "http://127.0.0.1:8001";
  const token = $("token").value.trim();
  await chrome.storage.local.set({ backend, token });
  $("status").textContent = "testing…";
  try {
    const res = await fetch(`${backend}/browser/hello`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Browser-Token": token },
      body: JSON.stringify({ browser_id: "options-page", browser: "options", version: "", tabs: 0 }),
    });
    if (res.status === 401) { $("status").textContent = "NOT PAIRED: the token does not match the console's."; return; }
    if (!res.ok) { $("status").textContent = `backend answered HTTP ${res.status}`; return; }
    const data = await res.json();
    $("status").textContent = `PAIRED. Browser Hands switch is ${data.hands_on ? "ON" : "OFF"} on the console. ` +
      `Actions: ${(data.actions || []).join(", ")}.`;
  } catch (err) {
    $("status").textContent = `cannot reach ${backend}: ${err}`;
  }
}

$("save").addEventListener("click", saveAndTest);
load();
