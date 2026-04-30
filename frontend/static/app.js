/**
 * OT Sentinel — Shared app utilities
 * Loaded on every page (after style.css, before page-specific JS).
 */

// ── Auth helpers ──────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem("ots_token");
}

function getUser() {
  const raw = localStorage.getItem("ots_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveAuth(token, user) {
  localStorage.setItem("ots_token", token);
  localStorage.setItem("ots_user", JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem("ots_token");
  localStorage.removeItem("ots_user");
}

function requireAuth() {
  const token = getToken();
  const user = getUser();
  if (!token || !user) {
    window.location.href = "/login.html";
    return false;
  }
  return true;
}

function logout() {
  clearAuth();
  window.location.href = "/login.html";
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const resp = await fetch(path, { ...options, headers });

  if (resp.status === 401 || resp.status === 403) {
    // If 401, likely token expired — redirect to login
    if (resp.status === 401) {
      clearAuth();
      window.location.href = "/login.html";
    }
    const err = await resp.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || "Unauthorized"), { status: resp.status });
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || `HTTP ${resp.status}`), { status: resp.status });
  }

  return resp.json();
}

// ── Page header helpers ───────────────────────────────────────────────────────

function initPageHeader() {
  const user = getUser();
  if (!user) return;

  const nameEl = document.getElementById("header-user");
  const roleEl = document.getElementById("header-role");

  if (nameEl) nameEl.textContent = user.name || user.email;
  if (roleEl) {
    roleEl.textContent = user.role;
    roleEl.className = `badge badge-${user.role === "admin" ? "admin" : "operator"}`;
  }
}

// ── Toast notifications ───────────────────────────────────────────────────────

function showToast(message, type = "success", durationMs = 3000) {
  const existing = document.querySelectorAll(".toast");
  existing.forEach((t) => t.remove());

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, durationMs);
}

// ── Badge helpers ──────────────────────────────────────────────────────────────

function severityBadge(severity) {
  const s = (severity || "").toLowerCase();
  return `<span class="badge badge-${s}">${severity || "—"}</span>`;
}

function statusBadge(status) {
  const s = (status || "").toLowerCase().replace(/\s+/g, "-");
  return `<span class="badge badge-status-${s}">${status || "—"}</span>`;
}

function deviceStatusBadge(status) {
  const s = (status || "").toLowerCase();
  return `<span class="badge badge-${s}">${status || "—"}</span>`;
}

// ── Risk score bar ────────────────────────────────────────────────────────────

function riskBar(score) {
  const pct = Math.min(100, Math.max(0, Number(score) || 0));
  let color = "#22c55e";
  if (pct >= 70) color = "#ef4444";
  else if (pct >= 40) color = "#f59e0b";
  return `
    <div class="risk-bar-wrapper">
      <div class="risk-bar-bg">
        <div class="risk-bar-fill" style="width:${pct}%;background:${color}"></div>
      </div>
      <span class="text-sm" style="min-width:28px;text-align:right">${pct}</span>
    </div>`;
}

// ── Date formatting ───────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function formatDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

function timeAgo(iso) {
  if (!iso) return "—";
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return iso;
  }
}

// ── Short ID ──────────────────────────────────────────────────────────────────

function shortId(id) {
  return (id || "").substring(0, 8);
}

// ── Empty state HTML ──────────────────────────────────────────────────────────

function emptyState(icon, message) {
  return `
    <tr>
      <td colspan="99">
        <div class="empty-state">
          <div class="empty-state-icon">${icon}</div>
          <div>${message}</div>
        </div>
      </td>
    </tr>`;
}
