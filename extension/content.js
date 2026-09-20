// content.js
// Renders a dismissible warning banner at the top of the page when the
// background worker flags the current URL as high-risk phishing.

function injectBanner(result) {
  if (document.getElementById("ai-phishing-guard-banner")) return;

  const banner = document.createElement("div");
  banner.id = "ai-phishing-guard-banner";
  banner.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
    background: #c0392b; color: #fff; font-family: Arial, sans-serif;
    font-size: 14px; padding: 12px 16px; display: flex;
    align-items: center; justify-content: space-between;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  `;

  const signals = (result.top_signals || []).slice(0, 2).join("; ");
  banner.innerHTML = `
    <div>
      <strong>⚠️ Warning: this site looks like phishing</strong>
      (${Math.round(result.confidence * 100)}% confidence). ${signals}
    </div>
    <div>
      <button id="ai-phishing-guard-leave" style="margin-right:8px;padding:6px 12px;
        background:#fff;color:#c0392b;border:none;border-radius:4px;cursor:pointer;
        font-weight:bold;">Leave site</button>
      <button id="ai-phishing-guard-dismiss" style="padding:6px 12px;
        background:transparent;color:#fff;border:1px solid #fff;border-radius:4px;
        cursor:pointer;">Dismiss</button>
    </div>
  `;

  document.documentElement.appendChild(banner);

  document.getElementById("ai-phishing-guard-dismiss").addEventListener("click", () => {
    banner.remove();
  });
  document.getElementById("ai-phishing-guard-leave").addEventListener("click", () => {
    window.location.href = "https://www.google.com/search?q=is+this+site+safe";
  });
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "SHOW_WARNING") {
    // Wait for <body> in case we're at document_start.
    if (document.body) {
      injectBanner(message.payload);
    } else {
      document.addEventListener("DOMContentLoaded", () => injectBanner(message.payload));
    }
  }
});
