/**
 * OT Sentinel — Devices page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

let allDevices = [];
let currentFilter = "all";

async function loadDevices() {
  const tbody = document.getElementById("devices-body");
  try {
    allDevices = await apiFetch("/api/devices");
    renderDevices(currentFilter);
  } catch (err) {
    if (err.status !== 401) {
      tbody.innerHTML = emptyState("❌", "Failed to load devices: " + err.message);
      showToast("Failed to load devices", "error");
    }
  }
}

function renderDevices(filter) {
  const tbody = document.getElementById("devices-body");
  const countEl = document.getElementById("device-count");

  const filtered =
    filter === "all"
      ? allDevices
      : allDevices.filter((d) => (d.status || "").toLowerCase() === filter);

  if (countEl) {
    countEl.textContent =
      filter === "all"
        ? `${allDevices.length} devices`
        : `${filtered.length} of ${allDevices.length} devices`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = emptyState("🔍", `No ${filter === "all" ? "" : filter + " "}devices found`);
    return;
  }

  // Sort: critical first, then warning, offline, online
  const order = { critical: 0, warning: 1, offline: 2, online: 3 };
  const sorted = [...filtered].sort(
    (a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9)
  );

  tbody.innerHTML = sorted
    .map(
      (d) => `
    <tr>
      <td><strong>${d.name || "—"}</strong></td>
      <td>
        <span style="background:var(--bg-elevated);padding:2px 8px;border-radius:4px;font-size:0.75rem">
          ${d.type || "—"}
        </span>
      </td>
      <td class="text-secondary">${d.site_name || d.site_id || "—"}</td>
      <td>${deviceStatusBadge(d.status)}</td>
      <td><span class="font-mono text-secondary">${d.ip_address || "—"}</span></td>
      <td><span class="font-mono text-sm">${d.firmware_version || "—"}</span></td>
      <td class="text-secondary">${timeAgo(d.last_seen)}</td>
      <td>${riskBar(d.risk_score)}</td>
    </tr>`
    )
    .join("");
}

// Filter button click handlers
document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    this.classList.add("active");
    currentFilter = this.dataset.filter;
    renderDevices(currentFilter);
  });
});

loadDevices();
