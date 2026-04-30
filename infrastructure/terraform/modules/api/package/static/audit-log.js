/**
 * OT Sentinel — Audit Log page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

const ACTION_LABELS = {
  LOGIN: { label: "LOGIN", color: "badge-online" },
  LOGOUT: { label: "LOGOUT", color: "badge-offline" },
  VIEW_DEVICE: { label: "VIEW DEVICE", color: "badge-low" },
  VIEW_INCIDENT: { label: "VIEW INCIDENT", color: "badge-low" },
  UPDATE_DEVICE: { label: "UPDATE DEVICE", color: "badge-medium" },
  ACKNOWLEDGE_INCIDENT: { label: "ACKNOWLEDGE", color: "badge-warning" },
};

function actionBadge(action) {
  const cfg = ACTION_LABELS[action] || { label: action || "—", color: "badge-low" };
  return `<span class="badge ${cfg.color}">${cfg.label}</span>`;
}

async function loadAuditLogs() {
  const tbody = document.getElementById("audit-body");
  const deniedEl = document.getElementById("audit-access-denied");
  const tableWrapper = document.getElementById("audit-table-wrapper");

  try {
    const logs = await apiFetch("/api/audit");
    renderAuditLogs(logs);
  } catch (err) {
    if (err.status === 403) {
      // Non-admin user
      if (tableWrapper) tableWrapper.style.display = "none";
      if (deniedEl) deniedEl.style.display = "block";
    } else if (err.status !== 401) {
      tbody.innerHTML = emptyState("❌", "Failed to load audit log: " + err.message);
      showToast("Failed to load audit log", "error");
    }
  }
}

function renderAuditLogs(logs) {
  const tbody = document.getElementById("audit-body");

  if (!logs || logs.length === 0) {
    tbody.innerHTML = emptyState("📋", "No audit log entries found");
    return;
  }

  tbody.innerHTML = logs
    .map(
      (log) => `
    <tr>
      <td class="text-secondary font-mono text-xs">${formatDateTime(log.timestamp)}</td>
      <td>
        <div style="font-size:0.8rem">${log.user_email || "—"}</div>
      </td>
      <td>${actionBadge(log.action)}</td>
      <td>
        <span style="background:var(--bg-elevated);padding:2px 8px;border-radius:4px;font-size:0.72rem;color:var(--text-secondary)">
          ${log.resource_type || "—"}
        </span>
      </td>
      <td><span class="font-mono text-secondary text-xs">${shortId(log.resource_id)}</span></td>
      <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${log.detail || ""}">
        ${log.detail || "—"}
      </td>
      <td><span class="font-mono text-secondary text-xs">${log.ip_address || "—"}</span></td>
    </tr>`
    )
    .join("");
}

loadAuditLogs();
