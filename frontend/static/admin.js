/**
 * OT Sentinel — Admin page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

function renderUserInfo() {
  const user = getUser();
  if (!user) return;

  const el = (id, val) => {
    const e = document.getElementById(id);
    if (e) e.textContent = val || "—";
  };

  el("admin-name", user.name);
  el("admin-email", user.email);
  el("admin-id", user.user_id);

  const roleEl = document.getElementById("admin-role");
  if (roleEl) {
    roleEl.innerHTML = `<span class="badge badge-${user.role === "admin" ? "admin" : "operator"}">${user.role}</span>`;
  }
}

async function loadPlatformSummary() {
  try {
    const summary = await apiFetch("/api/dashboard/summary");
    const el = (id, val) => {
      const e = document.getElementById(id);
      if (e) e.textContent = val !== undefined ? val : "—";
    };
    el("platform-devices", summary.total_devices);
    el("platform-incidents", summary.active_incidents);
    el("platform-risk", summary.avg_risk_score);
  } catch (err) {
    if (err.status !== 401) {
      console.error("Failed to load platform summary:", err.message);
    }
  }
}

renderUserInfo();
loadPlatformSummary();
