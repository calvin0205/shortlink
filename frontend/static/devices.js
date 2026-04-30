/**
 * OT Sentinel — Devices page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

let allDevices = [];
let currentFilter = "all";
let _simulateDeviceId = null;

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
      <td>
        <button onclick="openSimulateModal('${d.device_id}', '${(d.name || "").replace(/'/g, "\\'")}')" class="btn btn-danger" style="font-size:0.75rem;padding:4px 10px">⚡ Simulate</button>
      </td>
    </tr>`
    )
    .join("");
}

// ── Simulate Anomaly Modal ─────────────────────────────────────────────────────

async function loadAnomalyTypes() {
  try {
    const types = await apiFetch("/api/devices/anomaly-types");
    const select = document.getElementById("anomaly-type-select");
    if (!select) return;
    select.innerHTML = types
      .map((t) => `<option value="${t.value}">${t.label}</option>`)
      .join("");
  } catch (err) {
    console.error("Failed to load anomaly types:", err.message);
  }
}

function openSimulateModal(deviceId, deviceName) {
  _simulateDeviceId = deviceId;
  const nameEl = document.getElementById("modal-device-name");
  if (nameEl) nameEl.textContent = deviceName;

  // Reset result area
  const resultEl = document.getElementById("simulate-result");
  if (resultEl) {
    resultEl.style.display = "none";
    resultEl.innerHTML = "";
  }

  // Re-enable simulate button
  const btn = document.getElementById("simulate-btn");
  if (btn) {
    btn.disabled = false;
    btn.textContent = "⚡ Simulate";
  }

  document.getElementById("simulate-modal").style.display = "flex";
}

function closeSimulateModal() {
  document.getElementById("simulate-modal").style.display = "none";
  _simulateDeviceId = null;
}

async function runSimulation() {
  if (!_simulateDeviceId) return;

  const select = document.getElementById("anomaly-type-select");
  const anomalyType = select ? select.value : "";
  if (!anomalyType) {
    showToast("Please select an anomaly type", "error");
    return;
  }

  const btn = document.getElementById("simulate-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Running…";
  }

  try {
    const result = await apiFetch(`/api/devices/${_simulateDeviceId}/simulate`, {
      method: "POST",
      body: JSON.stringify({ anomaly_type: anomalyType }),
    });

    const resultEl = document.getElementById("simulate-result");
    if (resultEl) {
      resultEl.style.display = "block";
      resultEl.innerHTML = `
        <div style="text-align:center;margin-bottom:12px">
          <div style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em">Risk Score</div>
          <div class="risk-score-display">${result.risk_score}</div>
          <div>${severityBadge(result.severity)}</div>
        </div>
        <div style="font-size:0.875rem;font-weight:600;margin-bottom:4px">${result.title}</div>
        <div style="font-size:0.8rem;color:var(--text-secondary)">${result.message}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">Incident ID: <span class="font-mono">${shortId(result.incident_id)}</span></div>
      `;
    }

    // Reload device list to reflect updated status
    await loadDevices();

    showToast(`Anomaly simulated — risk score ${result.risk_score} (${result.severity})`, "error");

    // Auto-close after brief delay
    setTimeout(() => closeSimulateModal(), 4000);
  } catch (err) {
    showToast("Simulation failed: " + err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "⚡ Simulate";
    }
  }
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

loadAnomalyTypes();
loadDevices();
