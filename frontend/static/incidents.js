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
      (inc) => {
        const status = (inc.status || "").toLowerCase();
        const actions = [];
        if (status === "open") {
          actions.push(`<button onclick="acknowledgeIncident('${inc.incident_id}')" class="btn btn-ghost" style="font-size:0.75rem;padding:4px 8px">✔ Acknowledge</button>`);
        }
        if (status !== "resolved") {
          actions.push(`<button onclick="resolveIncident('${inc.incident_id}')" class="btn btn-ghost" style="font-size:0.75rem;padding:4px 8px;color:var(--success)">✅ Resolve</button>`);
        }
        return `
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
      <td style="white-space:nowrap">${actions.join(" ")}</td>
    </tr>`;
      }
    )
    .join("");
}

// ── Incident actions ──────────────────────────────────────────────────────────

async function acknowledgeIncident(incidentId) {
  try {
    await apiFetch(`/api/incidents/${incidentId}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    showToast("Incident acknowledged", "success");
    await loadIncidents();
  } catch (err) {
    showToast("Failed to acknowledge: " + err.message, "error");
  }
}

async function resolveIncident(incidentId) {
  try {
    await apiFetch(`/api/incidents/${incidentId}/resolve`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    showToast("Incident resolved", "success");
    await loadIncidents();
  } catch (err) {
    showToast("Failed to resolve: " + err.message, "error");
  }
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
