const t = (key) => chrome.i18n.getMessage(key) || key;
document.documentElement.dir = chrome.i18n.getMessage("@@bidi_dir") || "ltr";
document.getElementById("title").textContent = t("popupTitle");
document.getElementById("portLabel").textContent = t("port");

async function refresh() {
  const { connected, port } = await chrome.storage.local.get(["connected", "port"]);
  document.getElementById("status").classList.toggle("ok", !!connected);
  document.getElementById("statusText").textContent = connected ? t("connected") : t("notConnected");
  document.getElementById("hint").textContent = connected ? t("hintConnected") : t("hintNotConnected");
  document.getElementById("port").value = port || 47812;
}

document.getElementById("port").addEventListener("change", (e) => {
  const value = Number(e.target.value);
  if (value >= 1024 && value <= 65535) chrome.storage.local.set({ port: value });
});
chrome.storage.onChanged.addListener(refresh);
refresh();
