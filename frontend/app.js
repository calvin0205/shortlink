const API_BASE = ["localhost", "shortlink.local"].includes(window.location.hostname)
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "";  // same origin in production (CloudFront routes /api/* to Lambda)

// ── Shorten form ─────────────────────────────────────────────────────────────

const form       = document.getElementById("shorten-form");
const urlInput   = document.getElementById("url-input");
const codeInput  = document.getElementById("code-input");
const submitBtn  = document.getElementById("submit-btn");
const resultDiv  = document.getElementById("result");
const shortText  = document.getElementById("short-url-text");
const copyBtn    = document.getElementById("copy-btn");
const errorMsg   = document.getElementById("error-msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide(resultDiv); hide(errorMsg);
  submitBtn.disabled = true;
  submitBtn.textContent = "Shortening…";

  const body = { url: urlInput.value.trim() };
  const custom = codeInput.value.trim();
  if (custom) body.custom_code = custom;

  try {
    const resp = await fetch(`${API_BASE}/api/links`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail ?? "Failed to shorten URL");

    shortText.textContent = data.short_url;
    show(resultDiv);
    urlInput.value = "";
    codeInput.value = "";
  } catch (err) {
    showError(errorMsg, err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Shorten";
  }
});

copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(shortText.textContent).then(() => {
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1800);
  });
});

// ── Stats lookup ─────────────────────────────────────────────────────────────

const statsCodeInput = document.getElementById("stats-code");
const statsBtn       = document.getElementById("stats-btn");
const statsResult    = document.getElementById("stats-result");
const statsError     = document.getElementById("stats-error");

statsBtn.addEventListener("click", async () => {
  const code = statsCodeInput.value.trim();
  if (!code) return;
  hide(statsResult); hide(statsError);
  statsBtn.disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/api/links/${encodeURIComponent(code)}/stats`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail ?? "Not found");

    document.getElementById("s-code").textContent    = data.code;
    document.getElementById("s-url").textContent     = data.url;
    document.getElementById("s-short").textContent   = data.short_url;
    document.getElementById("s-created").textContent = new Date(data.created_at).toLocaleString();
    document.getElementById("s-hits").textContent    = data.hits;
    show(statsResult);
  } catch (err) {
    showError(statsError, err.message);
  } finally {
    statsBtn.disabled = false;
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }
function showError(el, msg) { el.textContent = msg; show(el); }
