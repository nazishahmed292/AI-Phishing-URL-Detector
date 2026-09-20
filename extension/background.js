// background.js
// Watches for tab navigation, calls the local/deployed prediction API,
// caches results per-tab, and updates the toolbar icon badge.
// Configure API_BASE_URL to point at your deployed FastAPI backend.

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const resultsByTab = {}; // tabId -> { url, is_phishing, confidence, risk_level, top_signals }

async function getApiBaseUrl() {
  const stored = await chrome.storage.local.get("apiBaseUrl");
  return stored.apiBaseUrl || DEFAULT_API_BASE_URL;
}

function isCheckableUrl(url) {
  return url && (url.startsWith("http://") || url.startsWith("https://"));
}

async function checkUrl(url) {
  const apiBaseUrl = await getApiBaseUrl();
  const res = await fetch(`${apiBaseUrl}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, source: "extension" }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

function setBadge(tabId, result) {
  if (!result) {
    chrome.action.setBadgeText({ tabId, text: "" });
    return;
  }
  if (result.is_phishing) {
    chrome.action.setBadgeText({ tabId, text: "!" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#e74c3c" });
  } else {
    chrome.action.setBadgeText({ tabId, text: "✓" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#2ecc71" });
  }
}

async function handleTabUpdate(tabId, url) {
  if (!isCheckableUrl(url)) return;
  try {
    const result = await checkUrl(url);
    resultsByTab[tabId] = { url, ...result };
    setBadge(tabId, result);

    if (result.is_phishing && result.risk_level === "high") {
      // Ask the content script to render an in-page warning banner.
      chrome.tabs.sendMessage(tabId, {
        type: "SHOW_WARNING",
        payload: result,
      }).catch(() => {
        /* content script may not be ready yet — safe to ignore */
      });
    }
  } catch (err) {
    console.warn("Phishing Guard: could not reach API:", err.message);
    resultsByTab[tabId] = { url, error: err.message };
    setBadge(tabId, null);
  }
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "loading" && tab.url) {
    handleTabUpdate(tabId, tab.url);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  delete resultsByTab[tabId];
});

// Let the popup ask for the current tab's cached result.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_RESULT_FOR_TAB") {
    sendResponse(resultsByTab[message.tabId] || null);
  }
  if (message.type === "RECHECK_TAB") {
    handleTabUpdate(message.tabId, message.url).then(() => {
      sendResponse(resultsByTab[message.tabId] || null);
    });
    return true; // keep the message channel open for async sendResponse
  }
  return true;
});
