/**
 * OT Sentinel — Incidents page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

let allIncidents = [];
let currentFilter = "all";

async function loadIncidents() {
  const tbody = document.getElementById("incidents-body");
  try {
    allIncidents = await apiFetch("/api/incidents");
    renderIncidents(currentFilter);
  } catch (err) {
    if (err.status !== 401) {
      tbody.innerHTML = emptyState("❌", "Failed to load incidents: " + err.message);
      showToast("Failed to load incidents", "error");
    }
  }
}

function renderIncidents(filter) {
  const tbody = document.getElementById("incidents-body");
  const countEl = document.getElementById("incident-count");

  const filtered =
    filter === "all"
      ? allIncidents
      : allIncidents.filter((inc) => (inc.severity || "").toLowerCase() === filter);

  if (countEl) {
    countEl.textContent =
      filter === "all"
        ? `${allIncidents.length} incidents`
        : `${filtered.length} of ${allIncidents.length} incidents`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = emptyState("✅", `No ${filter === "all" ? "" : filter + " "}incidents found`);
    return;
  }

  // Sort: by severity then created_at desc
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sorted = [...filtered].sort((a, b) => {
    const sA = severityOrder[(a.severity || "").toLowerCase()] ?? 9;
    const sB = severityOrder[(b.severity || "").toLowerCase()] ?? 9;
    if (sA !== sB) return sA - sB;
    return (b.created_at || "") > (a.created_at || "") ? 1 : -1;
  });

  tbody.innerHTML = sorted
    .map(
      (inc) => `
    <tr>
      <td><span class="font-mono text-secondary">${shortId(inc.incident_id)}</span></td>
      <td>${inc.device_name || "—"}</td>
      <td>${severityBadge(inc.severity)}</td>
      <td>${statusBadge(inc.status)}</td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${inc.title || ""}">
        ${inc.title || "—"}
      </td>
      <td>${riskBar(inc.risk_score)}</td>
      <td class="text-secondary">${timeAgo(inc.created_at)}</td>
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
    renderIncidents(currentFilter);
  });
});

loadIncidents();
