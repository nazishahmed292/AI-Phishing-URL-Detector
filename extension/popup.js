// popup.js
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function renderResult(result) {
  const card = document.getElementById("status-card");
  const verdictText = document.getElementById("verdict-text");
  const confidenceText = document.getElementById("confidence-text");
  const signalsList = document.getElementById("signals");
  signalsList.innerHTML = "";

  if (!result) {
    card.className = "unknown";
    verdictText.textContent = "No data yet";
    confidenceText.textContent = "Reload the page or click re-check.";
    return;
  }

  if (result.error) {
    card.className = "unknown";
    verdictText.textContent = "API unreachable";
    confidenceText.textContent = result.error;
    return;
  }

  if (result.is_phishing) {
    card.className = "danger";
    verdictText.textContent = "⚠️ Likely Phishing";
  } else {
    card.className = "safe";
    verdictText.textContent = "✅ Looks Legitimate";
  }
  confidenceText.textContent = `Phishing confidence: ${(result.confidence * 100).toFixed(1)}% (${result.risk_level} risk)`;

  (result.top_signals || []).forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    signalsList.appendChild(li);
  });
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) return;

  document.getElementById("url-display").textContent = tab.url;

  const stored = await chrome.storage.local.get("apiBaseUrl");
  const apiBaseUrl = stored.apiBaseUrl || DEFAULT_API_BASE_URL;
  document.getElementById("api-link").href = apiBaseUrl.replace(":8000", ":8501");

  chrome.runtime.sendMessage(
    { type: "GET_RESULT_FOR_TAB", tabId: tab.id },
    (result) => renderResult(result)
  );

  document.getElementById("recheck-btn").addEventListener("click", () => {
    document.getElementById("verdict-text").textContent = "Checking...";
    chrome.runtime.sendMessage(
      { type: "RECHECK_TAB", tabId: tab.id, url: tab.url },
      (result) => renderResult(result)
    );
  });
}

init();
