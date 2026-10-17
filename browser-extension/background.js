// Imaa Helper — connects to the Imaa desktop app on 127.0.0.1 and runs its commands in the active tab.
// No page content, history or browsing data is ever sent to the app: only {clicked: true|false}.

const DEFAULT_PORT = 47812;
const KEEPALIVE_MS = 20000;
let socket = null;
let keepAlive = null;
let retryDelay = 1000;

async function port() {
  try {
    const { port } = await chrome.storage.local.get("port");
    return Number(port) || DEFAULT_PORT;
  } catch {
    return DEFAULT_PORT;
  }
}

async function connect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
  const p = await port();
  try {
    socket = new WebSocket(`ws://127.0.0.1:${p}`);
  } catch {
    scheduleReconnect();
    return;
  }
  socket.onopen = () => {
    retryDelay = 1000;
    setStatus(true);
    clearInterval(keepAlive);
    keepAlive = setInterval(() => send({ type: "ping" }), KEEPALIVE_MS);
  };
  socket.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (msg.type === "skip_ad") {
      const clicked = await runInActiveTab(skipAdInPage);
      send({ type: "result", id: msg.id, clicked });
    }
  };
  socket.onclose = () => {
    clearInterval(keepAlive);
    setStatus(false);
    scheduleReconnect();
  };
  socket.onerror = () => socket && socket.close();
}

function scheduleReconnect() {
  setTimeout(connect, retryDelay);
  retryDelay = Math.min(retryDelay * 2, 30000);
}

function send(obj) {
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(obj));
}

function setStatus(connected) {
  chrome.storage.local.set({ connected });
  chrome.action.setBadgeText({ text: connected ? "" : "!" });
  chrome.action.setBadgeBackgroundColor({ color: "#D93025" });
}

async function runInActiveTab(func) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab || !tab.id || !/^https?:/.test(tab.url || "")) return false;
    const results = await chrome.scripting.executeScript({ target: { tabId: tab.id, allFrames: true }, func });
    return results.some((r) => r && r.result === true);
  } catch {
    return false;
  }
}

// Runs inside the page. Must be self-contained.
function skipAdInPage() {
  const selectors = [
    ".ytp-skip-ad-button",
    ".ytp-ad-skip-button",
    ".ytp-ad-skip-button-modern",
    ".ytp-ad-skip-button-slot button",
    "button[id^='skip-button']",
    "[class*='skip-ad'] button",
    "button[class*='skipAd']",
    "button[aria-label*='Skip' i]",
  ];
  const pattern =
    /^\s*(skip(\s+ads?)?|skip\s+ad\s*now|تخط[يّ]+(\s+الإعلان(ات)?)?|تجاوز(\s+الإعلان)?|passer(\s+l['’]annonce)?|omitir(\s+anuncios?)?|(werbung\s+)?überspringen|pular(\s+anúncios?)?|salta(\s+annunci)?|reklam[ıi]\s+geç|atla)\s*[›>»▶]*\s*$/i;
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 4 && r.height > 4 && s.visibility !== "hidden" && s.display !== "none" && Number(s.opacity) > 0.1;
  };
  const press = (el) => {
    el.click();
    return true;
  };
  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      if (visible(el)) return press(el);
    }
  }
  const candidates = document.querySelectorAll("button, [role='button'], a, div[tabindex]");
  for (const el of candidates) {
    const text = (el.innerText || el.getAttribute("aria-label") || "").trim();
    if (text.length <= 30 && pattern.test(text) && visible(el)) return press(el);
  }
  return false;
}

chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
chrome.storage.onChanged.addListener((changes) => {
  if (changes.port && socket) socket.close();
});
connect();
