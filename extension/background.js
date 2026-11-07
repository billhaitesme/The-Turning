// OMEGA-ARC Browser Hands — background worker (Chrome/Edge: service worker; Firefox: event page).
// Long-polls the local backend for jobs, runs them in the operator's tabs, posts results back.
// Nothing listens in the browser; the extension only ever calls the configured backend URL.
// Works unchanged in Chrome, Edge and Firefox (chrome.* with promises, MV3).

const DEFAULTS = { backend: "http://127.0.0.1:8001", token: "" };
const BROWSER = detectBrowser();
const BROWSER_ID = `${BROWSER.name}-${Math.random().toString(36).slice(2, 8)}`;
let running = false;

function detectBrowser() {
  const ua = navigator.userAgent;
  const pick = (re) => (ua.match(re) || [])[1] || "";
  if (/Edg\//.test(ua)) return { name: "edge", version: pick(/Edg\/([\d.]+)/) };
  if (/Firefox\//.test(ua)) return { name: "firefox", version: pick(/Firefox\/([\d.]+)/) };
  if (/Chrome\//.test(ua)) return { name: "chrome", version: pick(/Chrome\/([\d.]+)/) };
  return { name: "unknown", version: "" };
}

async function settings() {
  const stored = await chrome.storage.local.get(["backend", "token"]);
  return { backend: (stored.backend || DEFAULTS.backend).replace(/\/+$/, ""), token: stored.token || "" };
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function post(path, body, token) {
  const s = await settings();
  return fetch(`${s.backend}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Browser-Token": token ?? s.token },
    body: JSON.stringify(body),
  });
}

async function tabCount() {
  try { return (await chrome.tabs.query({})).length; } catch { return 0; }
}

// ---------------------------------------------------------------- the poll loop
async function loop() {
  if (running) return;
  running = true;
  try {
    while (true) {
      const s = await settings();
      if (!s.token) { await setBadge("…", "#888"); await sleep(5000); continue; }
      try {
        const res = await post("/browser/next", {
          browser_id: BROWSER_ID, browser: BROWSER.name, version: BROWSER.version, tabs: await tabCount(), wait: 25,
        });
        if (res.status === 401) { await setBadge("!", "#c33"); await sleep(10000); continue; }
        if (!res.ok) { await setBadge("?", "#c93"); await sleep(3000); continue; }
        const data = await res.json();
        await setBadge(data.hands_on ? "ON" : "OFF", data.hands_on ? "#2a8" : "#666");
        if (data.job) {
          let out;
          try {
            out = { ok: true, result: await run(data.job) };
          } catch (err) {
            out = { ok: false, error: String(err && err.message ? err.message : err).slice(0, 1800) };
          }
          await post("/browser/result", { job_id: data.job.job_id, ...out });
        }
      } catch (err) {
        await setBadge("x", "#c33");
        await sleep(3000);
      }
    }
  } finally {
    running = false;
  }
}

async function setBadge(text, color) {
  try {
    await chrome.action.setBadgeText({ text });
    await chrome.action.setBadgeBackgroundColor({ color });
  } catch { /* no action badge on this browser */ }
}

// ---------------------------------------------------------------- the actions
async function run(job) {
  const p = job.params || {};
  switch (job.action) {
    case "list_tabs": return listTabs();
    case "read_page": return readPage(p.tab_id, p.max_chars || 6000);
    case "open_url": return openUrl(p.url, p.tab_id);
    case "click": return click(p.tab_id, p.selector, p.text);
    case "type": return type(p.tab_id, p.selector, p.text, p.submit);
    case "screenshot": return screenshot(p.tab_id);
    default: throw new Error(`unknown action ${job.action}`);
  }
}

async function listTabs() {
  const tabs = await chrome.tabs.query({});
  return tabs.map((t) => ({ id: t.id, title: t.title || "", url: t.url || "", active: !!t.active, windowId: t.windowId }));
}

async function inTab(tabId, func, args) {
  const id = Number(tabId);
  if (!Number.isInteger(id)) throw new Error("tab_id must be an integer");
  let results;
  try {
    results = await chrome.scripting.executeScript({ target: { tabId: id }, func, args: args || [] });
  } catch (err) {
    throw new Error(`cannot run in tab ${id}: ${err && err.message ? err.message : err} (browser-internal pages are off limits)`);
  }
  const first = results && results[0];
  if (!first) throw new Error(`no result from tab ${id}`);
  if (first.error) throw new Error(String(first.error.message || first.error));
  return first.result;
}

async function readPage(tabId, maxChars) {
  const out = await inTab(tabId, (max) => {
    const text = (document.body && document.body.innerText) || "";
    return { title: document.title, url: location.href, text: text.replace(/\n{3,}/g, "\n\n").slice(0, max) };
  }, [Number(maxChars) || 6000]);
  return { tab_id: Number(tabId), ...out };
}

function waitForLoad(tabId, timeoutMs) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => { if (!done) { done = true; chrome.tabs.onUpdated.removeListener(onUpdated); resolve(); } };
    const onUpdated = (id, info) => { if (id === tabId && info.status === "complete") finish(); };
    chrome.tabs.onUpdated.addListener(onUpdated);
    setTimeout(finish, timeoutMs);
  });
}

async function openUrl(url, tabId) {
  if (!/^https?:\/\//.test(String(url))) throw new Error("only http(s) URLs may be opened");
  let tab;
  if (tabId !== undefined && tabId !== null && tabId !== "") {
    tab = await chrome.tabs.update(Number(tabId), { url, active: true });
  } else {
    tab = await chrome.tabs.create({ url, active: true });
  }
  await waitForLoad(tab.id, 15000);
  const fresh = await chrome.tabs.get(tab.id);
  return { tab_id: fresh.id, title: fresh.title || "", url: fresh.url || url };
}

async function click(tabId, selector, text) {
  return inTab(tabId, (sel, txt) => {
    let el = null;
    if (sel) el = document.querySelector(sel);
    if (!el && txt) {
      const wanted = txt.trim().toLowerCase();
      const candidates = [...document.querySelectorAll("a, button, input[type=submit], input[type=button], [role=button], summary, label")];
      el = candidates.find((c) => (c.innerText || c.value || c.getAttribute("aria-label") || "").trim().toLowerCase() === wanted)
        || candidates.find((c) => (c.innerText || c.value || c.getAttribute("aria-label") || "").trim().toLowerCase().includes(wanted));
    }
    if (!el) throw new Error(`no element matches ${sel ? `selector "${sel}"` : `text "${txt}"`}`);
    el.scrollIntoView({ block: "center" });
    el.click();
    return { detail: `clicked ${el.tagName.toLowerCase()} "${(el.innerText || el.value || "").trim().slice(0, 80)}"`, url: location.href };
  }, [selector || "", text || ""]);
}

async function type(tabId, selector, value, submit) {
  return inTab(tabId, (sel, val, doSubmit) => {
    const el = document.querySelector(sel);
    if (!el) throw new Error(`no element matches selector "${sel}"`);
    el.focus();
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value");
    if (setter && setter.set) setter.set.call(el, val); else el.value = val;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    if (doSubmit) {
      if (el.form && el.form.requestSubmit) el.form.requestSubmit();
      else el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true }));
    }
    return { detail: `typed ${val.length} chars into ${el.tagName.toLowerCase()}${doSubmit ? " and submitted" : ""}`, url: location.href };
  }, [selector, String(value), !!submit]);
}

async function screenshot(tabId) {
  const id = Number(tabId);
  const tab = await chrome.tabs.get(id);
  await chrome.tabs.update(id, { active: true });
  await sleep(250);
  const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 60 });
  return { tab_id: id, image };
}

// ---------------------------------------------------------------- keep-alive
chrome.runtime.onInstalled.addListener(() => { chrome.alarms.create("omega-tick", { periodInMinutes: 1 }); loop(); });
chrome.runtime.onStartup.addListener(() => loop());
chrome.alarms.onAlarm.addListener((a) => { if (a.name === "omega-tick") loop(); });
chrome.storage.onChanged.addListener(() => loop());
loop();
