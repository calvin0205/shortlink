/**
 * OT Sentinel — Devices page
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

let allDevices = [];
let currentFilter = "all";
let currentBayFilter = "";
let _simulateDeviceId = null;

async function loadDevices() {
  const tbody = document.getElementById("devices-body");
  try {
    let url = '/api/devices';
    const params = new URLSearchParams();
    if (currentFilter && currentFilter !== "all") params.set('status', currentFilter);
    if (currentBayFilter) params.set('bay_id', currentBayFilter);
    if (params.toString()) url += '?' + params.toString();
    allDevices = await apiFetch(url);
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
    tbody.innerHTML = `<tr><td colspan="12">${emptyState("🔍", `No ${filter === "all" ? "" : filter + " "}devices found`)}</td></tr>`;
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
      <td class="text-secondary">${d.bay_name || "—"}</td>
      <td class="text-secondary">${d.site_name || d.site_id || "—"}</td>
      <td>${deviceStatusBadge(d.status)}</td>
      <td><span class="font-mono text-secondary">${d.ip_address || "—"}</span></td>
      <td><span class="font-mono text-sm">${d.firmware_version || "—"}</span></td>
      <td class="text-secondary">${timeAgo(d.last_seen)}</td>
      <td>${riskBar(d.risk_score)}</td>
      <td>${healthBadge(d.health_score)}</td>
      <td>${pmDueBadge(d.pm_status, d.next_pm_date)}</td>
      <td style="white-space:nowrap">
        <button onclick="openMetricsModal('${d.device_id}', '${(d.name || "").replace(/'/g, "\\'")}')" class="btn btn-ghost" style="font-size:0.75rem;padding:4px 10px;margin-right:4px">📈 Metrics</button>
        <button onclick="openSimulateModal('${d.device_id}', '${(d.name || "").replace(/'/g, "\\'")}')" class="btn btn-danger" style="font-size:0.75rem;padding:4px 10px">⚡ Simulate</button>
      </td>
    </tr>`
    )
    .join("");
}

// ── Health-score badge ────────────────────────────────────────────────────────

function healthBadge(score) {
  if (score === null || score === undefined) return '<span class="text-secondary" style="font-size:0.75rem">—</span>';
  const n = parseInt(score, 10);
  let cls = "health-ok";
  if (n < 40)      cls = "health-critical";
  else if (n < 60) cls = "health-poor";
  else if (n < 80) cls = "health-fair";
  return `<span class="health-badge ${cls}">${n}</span>`;
}

// ── PM-due badge ──────────────────────────────────────────────────────────────

function pmDueBadge(pmStatus, nextPmDate) {
  if (!nextPmDate) return '<span class="text-secondary" style="font-size:0.75rem">—</span>';
  const dateStr = nextPmDate.slice(0, 10); // YYYY-MM-DD
  const statusMap = {
    overdue:  `<span class="pm-badge pm-overdue">⚠ Overdue (${dateStr})</span>`,
    due_soon: `<span class="pm-badge pm-due-soon">⏰ Due ${dateStr}</span>`,
    ok:       `<span class="pm-badge pm-ok">✓ ${dateStr}</span>`,
  };
  return statusMap[pmStatus] || `<span class="text-secondary" style="font-size:0.75rem">${dateStr}</span>`;
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

// Bay filter button click handlers
document.querySelectorAll('#bay-filter-bar .filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#bay-filter-bar .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentBayFilter = btn.dataset.bay;
    loadDevices();
  });
});

// Status filter button click handlers
document.querySelectorAll(".filter-bar:not(#bay-filter-bar) .filter-btn").forEach((btn) => {
  btn.addEventListener("click", function () {
    document.querySelectorAll(".filter-bar:not(#bay-filter-bar) .filter-btn").forEach((b) => b.classList.remove("active"));
    this.classList.add("active");
    currentFilter = this.dataset.filter;
    loadDevices();
  });
});

// ── Last-updated indicator ────────────────────────────────────────────────────

let _lastUpdatedAt = Date.now();

function setLastUpdatedNow() {
  _lastUpdatedAt = Date.now();
  const el = document.getElementById("last-updated-indicator");
  if (el) el.textContent = "↻ Updated just now";
}

function startLastUpdatedTicker() {
  setInterval(() => {
    const el = document.getElementById("last-updated-indicator");
    if (!el) return;
    const secs = Math.floor((Date.now() - _lastUpdatedAt) / 1000);
    el.textContent = secs < 5 ? "↻ Updated just now" : `↻ ${secs}s ago`;
  }, 1000);
}

// Inject indicator into the .card-header alongside the existing device-count span
setTimeout(() => {
  const cardHeader = document.querySelector(".card-header");
  if (cardHeader && !document.getElementById("last-updated-indicator")) {
    const el = document.createElement("span");
    el.id = "last-updated-indicator";
    el.className = "last-updated";
    el.textContent = "↻ Updated just now";
    cardHeader.appendChild(el);
  }
  startLastUpdatedTicker();
}, 0);

// ── Polling ───────────────────────────────────────────────────────────────────

const POLL_INTERVAL = 30000;
let _pollTimer = null;

async function refreshDevices() {
  await loadDevices();
  setLastUpdatedNow();
}

function startPolling() {
  if (_pollTimer) return;
  _pollTimer = setInterval(refreshDevices, POLL_INTERVAL);
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopPolling();
  } else {
    refreshDevices();
    startPolling();
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────

loadAnomalyTypes();
loadDevices().then(() => {
  setLastUpdatedNow();
});

startPolling();

// ── Metrics Chart Modal ───────────────────────────────────────────────────────

let _metricsChart = null;

function openMetricsModal(deviceId, deviceName) {
  const nameEl = document.getElementById("metrics-modal-device-name");
  if (nameEl) nameEl.textContent = `📈 Metrics — ${deviceName}`;

  // Reset state
  document.getElementById("metrics-loading").style.display = "flex";
  document.getElementById("metrics-empty").style.display = "none";
  const canvas = document.getElementById("metrics-chart");
  canvas.style.display = "none";
  const spcEl = document.getElementById("metrics-spc-status");
  if (spcEl) { spcEl.style.display = "none"; spcEl.textContent = ""; }

  // Destroy previous chart instance if any
  if (_metricsChart) {
    _metricsChart.destroy();
    _metricsChart = null;
  }

  document.getElementById("metrics-modal").style.display = "flex";

  _fetchAndRenderMetrics(deviceId);
}

function closeMetricsModal() {
  document.getElementById("metrics-modal").style.display = "none";
  if (_metricsChart) {
    _metricsChart.destroy();
    _metricsChart = null;
  }
}

async function _fetchAndRenderMetrics(deviceId) {
  try {
    const data = await apiFetch(`/api/devices/${deviceId}/metrics?hours=24`);

    document.getElementById("metrics-loading").style.display = "none";

    // Parse new response shape
    const metrics   = data.metrics   ?? [];
    const baselines = data.baselines ?? {};

    if (data.metrics.length === 0) {
      document.getElementById("metrics-empty").style.display = "flex";
      return;
    }

    // ── SPC status text ──────────────────────────────────────────────────────
    const spcEl = document.getElementById("metrics-spc-status");
    if (spcEl) {
      const cpuB  = baselines.cpu_pct    ?? {};
      const tmpB  = baselines.temp_c     ?? {};
      const rskB  = baselines.risk_score ?? {};
      const anyActive = cpuB.ucl !== null && cpuB.ucl !== undefined
                     || tmpB.ucl !== null && tmpB.ucl !== undefined
                     || rskB.ucl !== null && rskB.ucl !== undefined;

      if (anyActive) {
        // Use the n from whichever baseline is available
        const n = cpuB.n ?? tmpB.n ?? rskB.n ?? "?";
        const fmt = (v) => v != null ? v.toFixed(1) : "—";
        spcEl.textContent =
          `SPC Active — n=${n} readings` +
          (cpuB.ucl != null ? ` | CPU: UCL ${fmt(cpuB.ucl)} / LCL ${fmt(cpuB.lcl)}` : "") +
          (tmpB.ucl != null ? ` | Temp: UCL ${fmt(tmpB.ucl)} / LCL ${fmt(tmpB.lcl)}` : "");
      } else {
        spcEl.textContent = "SPC: Collecting baseline data (need 10+ readings)";
      }
      spcEl.style.display = "block";
    }

    const canvas = document.getElementById("metrics-chart");
    canvas.style.display = "block";

    // Format timestamps as HH:MM labels
    const labels = metrics.map((m) => {
      const d = new Date(m.ts);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    });

    const cpuData  = metrics.map((m) => m.cpu_pct);
    const riskData = metrics.map((m) => m.risk_score);
    const tempData = metrics.map((m) => m.temp_c);

    // ── Build datasets, appending UCL/LCL fake datasets where available ──────
    const datasets = [
      {
        label: "CPU %",
        data: cpuData,
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.08)",
        tension: 0.3,
        fill: true,
        yAxisID: "yLeft",
        pointRadius: metrics.length > 50 ? 0 : 3,
      },
      {
        label: "Risk Score",
        data: riskData,
        borderColor: "#ef4444",
        backgroundColor: "rgba(239,68,68,0.08)",
        tension: 0.3,
        fill: false,
        yAxisID: "yLeft",
        borderDash: [4, 3],
        pointRadius: metrics.length > 50 ? 0 : 3,
      },
      {
        label: "Temp °C",
        data: tempData,
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245,158,11,0.08)",
        tension: 0.3,
        fill: false,
        yAxisID: "yRight",
        pointRadius: metrics.length > 50 ? 0 : 3,
      },
    ];

    // cpu_pct UCL / LCL
    if (baselines.cpu_pct && baselines.cpu_pct.ucl !== null && baselines.cpu_pct.ucl !== undefined) {
      datasets.push({
        label: "CPU UCL",
        data: labels.map(() => baselines.cpu_pct.ucl),
        borderColor: "rgba(255, 80, 80, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yLeft",
        tension: 0,
      });
      datasets.push({
        label: "CPU LCL",
        data: labels.map(() => baselines.cpu_pct.lcl),
        borderColor: "rgba(255, 160, 50, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yLeft",
        tension: 0,
      });
    }

    // temp_c UCL / LCL
    if (baselines.temp_c && baselines.temp_c.ucl !== null && baselines.temp_c.ucl !== undefined) {
      datasets.push({
        label: "Temp UCL",
        data: labels.map(() => baselines.temp_c.ucl),
        borderColor: "rgba(255, 80, 80, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yRight",
        tension: 0,
      });
      datasets.push({
        label: "Temp LCL",
        data: labels.map(() => baselines.temp_c.lcl),
        borderColor: "rgba(255, 160, 50, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yRight",
        tension: 0,
      });
    }

    // risk_score UCL / LCL
    if (baselines.risk_score && baselines.risk_score.ucl !== null && baselines.risk_score.ucl !== undefined) {
      datasets.push({
        label: "Risk UCL",
        data: labels.map(() => baselines.risk_score.ucl),
        borderColor: "rgba(255, 80, 80, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yLeft",
        tension: 0,
      });
      datasets.push({
        label: "Risk LCL",
        data: labels.map(() => baselines.risk_score.lcl),
        borderColor: "rgba(255, 160, 50, 0.6)",
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        fill: false,
        yAxisID: "yLeft",
        tension: 0,
      });
    }

    _metricsChart = new Chart(canvas, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            labels: { color: "#94a3b8", font: { size: 12 } },
          },
          tooltip: {
            backgroundColor: "#1e293b",
            borderColor: "#334155",
            borderWidth: 1,
            titleColor: "#f1f5f9",
            bodyColor: "#94a3b8",
          },
        },
        scales: {
          x: {
            ticks: {
              color: "#94a3b8",
              maxTicksLimit: 12,
              maxRotation: 0,
            },
            grid: { color: "rgba(51,65,85,0.4)" },
          },
          yLeft: {
            type: "linear",
            position: "left",
            min: 0,
            max: 100,
            title: { display: true, text: "% / Score", color: "#94a3b8" },
            ticks: { color: "#94a3b8" },
            grid: { color: "rgba(51,65,85,0.4)" },
          },
          yRight: {
            type: "linear",
            position: "right",
            min: 20,
            max: 95,
            title: { display: true, text: "Temp °C", color: "#94a3b8" },
            ticks: { color: "#94a3b8" },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  } catch (err) {
    document.getElementById("metrics-loading").style.display = "none";
    document.getElementById("metrics-empty").style.display = "flex";
    document.getElementById("metrics-empty").querySelector(".empty-state-icon").textContent = "❌";
    document.querySelector("#metrics-empty").lastChild.textContent = " Failed to load metrics: " + err.message;
    showToast("Failed to load metrics: " + err.message, "error");
  }
}
