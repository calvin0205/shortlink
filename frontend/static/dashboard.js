/**
 * OT Sentinel — Dashboard page
 */

if (!requireAuth()) {
  // requireAuth redirects; stop execution
  throw new Error("Not authenticated");
}

initPageHeader();

let deviceChart = null;
let severityChart = null;

async function loadDashboard() {
  try {
    const summary = await apiFetch("/api/dashboard/summary");
    renderStats(summary);
    renderRecentIncidents(summary.recent_incidents || []);
    renderCharts(summary);
  } catch (err) {
    if (err.status !== 401) {
      showToast("Failed to load dashboard data: " + err.message, "error");
    }
  }
}

function renderStats(summary) {
  const el = (id, val) => {
    const e = document.getElementById(id);
    if (e) e.textContent = val !== undefined && val !== null ? val : "—";
  };

  el("stat-total-devices", summary.total_devices);
  el("stat-active-incidents", summary.active_incidents);
  el("stat-critical-incidents", summary.critical_incidents);
  el("stat-avg-risk", summary.avg_risk_score);

  renderBays(summary.bays);
}

function renderBays(bays) {
  const grid = document.getElementById('bay-status-grid');
  if (!grid || !bays) return;
  grid.innerHTML = bays.map(bay => `
    <div class="bay-card ${bay.status}">
      <div class="bay-card-name">${bay.bay_name}</div>
      <div class="bay-card-status ${bay.status}">${bay.status}</div>
      <div class="bay-card-counts">
        ${bay.online} online
        ${bay.warning  > 0 ? ` · <span style="color:#f59e0b">${bay.warning} warn</span>`   : ''}
        ${bay.critical > 0 ? ` · <span style="color:#ef4444">${bay.critical} crit</span>` : ''}
        ${bay.offline  > 0 ? ` · <span style="color:#6b7280">${bay.offline} off</span>`   : ''}
        / ${bay.total} total
      </div>
    </div>
  `).join('');
}

function renderRecentIncidents(incidents) {
  const tbody = document.getElementById("recent-incidents-body");
  if (!tbody) return;

  if (!incidents || incidents.length === 0) {
    tbody.innerHTML = emptyState("✅", "No active incidents");
    return;
  }

  tbody.innerHTML = incidents
    .map(
      (inc) => `
    <tr>
      <td><span class="font-mono text-secondary">${shortId(inc.incident_id)}</span></td>
      <td>${inc.device_name || "—"}</td>
      <td>${severityBadge(inc.severity)}</td>
      <td>${statusBadge(inc.status)}</td>
      <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${inc.title || "—"}</td>
      <td class="text-secondary">${timeAgo(inc.created_at)}</td>
    </tr>`
    )
    .join("");
}

function renderCharts(summary) {
  Chart.defaults.color = "#94a3b8";
  Chart.defaults.borderColor = "#334155";

  // Device Status Doughnut
  const ctxDevice = document.getElementById("chart-device-status");
  if (ctxDevice) {
    if (deviceChart) deviceChart.destroy();

    const labels = ["Online", "Warning", "Critical", "Offline"];
    const data = [
      summary.online_devices || 0,
      summary.warning_devices || 0,
      summary.critical_devices || 0,
      summary.offline_devices || 0,
    ];

    deviceChart = new Chart(ctxDevice, {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: ["#14532d", "#713f12", "#7f1d1d", "#450a0a"],
            borderColor: ["#22c55e", "#f59e0b", "#ef4444", "#fca5a5"],
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              padding: 16,
              font: { size: 12 },
              color: "#94a3b8",
            },
          },
        },
      },
    });
  }

  // Incidents by Severity Bar
  const ctxSeverity = document.getElementById("chart-incidents-severity");
  if (ctxSeverity) {
    if (severityChart) severityChart.destroy();

    // We need to fetch all incidents to count by severity
    apiFetch("/api/incidents").then((incidents) => {
      const counts = { critical: 0, high: 0, medium: 0, low: 0 };
      incidents.forEach((inc) => {
        const s = (inc.severity || "").toLowerCase();
        if (counts.hasOwnProperty(s)) counts[s]++;
      });

      severityChart = new Chart(ctxSeverity, {
        type: "bar",
        data: {
          labels: ["Critical", "High", "Medium", "Low"],
          datasets: [
            {
              label: "Incidents",
              data: [counts.critical, counts.high, counts.medium, counts.low],
              backgroundColor: ["#7f1d1d", "#7c2d12", "#713f12", "#1e3a5f"],
              borderColor: ["#ef4444", "#f97316", "#f59e0b", "#3b82f6"],
              borderWidth: 2,
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              ticks: { color: "#94a3b8" },
              grid: { color: "#334155" },
            },
            y: {
              beginAtZero: true,
              ticks: { color: "#94a3b8", stepSize: 1 },
              grid: { color: "#334155" },
            },
          },
        },
      });
    });
  }
}

// ── In-place chart update (avoids destroy/recreate flicker) ───────────────────

function updateChartsInPlace(summary) {
  if (deviceChart) {
    deviceChart.data.datasets[0].data = [
      summary.online_devices || 0,
      summary.warning_devices || 0,
      summary.critical_devices || 0,
      summary.offline_devices || 0,
    ];
    deviceChart.update("none");
  } else {
    // Charts not yet created — fall through to full renderCharts
    renderCharts(summary);
    return;
  }

  apiFetch("/api/incidents").then((incidents) => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    incidents.forEach((inc) => {
      const s = (inc.severity || "").toLowerCase();
      if (Object.prototype.hasOwnProperty.call(counts, s)) counts[s]++;
    });
    if (severityChart) {
      severityChart.data.datasets[0].data = [
        counts.critical,
        counts.high,
        counts.medium,
        counts.low,
      ];
      severityChart.update("none");
    }
  }).catch(() => {});
}

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

// Inject the indicator into the header bar between the <h2> and the user info
setTimeout(() => {
  const header = document.querySelector(".header");
  if (header && !document.getElementById("last-updated-indicator")) {
    const el = document.createElement("span");
    el.id = "last-updated-indicator";
    el.className = "last-updated";
    // Parent is a flex row; override float and use flex ordering instead
    el.style.cssText = "font-size:0.75rem;color:var(--text-secondary);margin-left:auto;margin-right:16px;align-self:center;float:none";
    el.textContent = "↻ Updated just now";
    const userInfo = header.querySelector(".user-info");
    if (userInfo) {
      header.insertBefore(el, userInfo);
    } else {
      header.appendChild(el);
    }
  }
  startLastUpdatedTicker();
}, 0);

// ── Polling ───────────────────────────────────────────────────────────────────

const POLL_INTERVAL = 30000;
let _pollTimer = null;

async function refreshDashboard() {
  try {
    const summary = await apiFetch("/api/dashboard/summary");
    renderStats(summary);
    renderRecentIncidents(summary.recent_incidents || []);
    updateChartsInPlace(summary);
    setLastUpdatedNow();
  } catch (err) {
    if (err.status !== 401) {
      showToast("Failed to load dashboard data: " + err.message, "error");
    }
  }
}

function startPolling() {
  if (_pollTimer) return;
  _pollTimer = setInterval(refreshDashboard, POLL_INTERVAL);
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
    // Immediately re-fetch when tab becomes visible again, then resume polling
    refreshDashboard();
    startPolling();
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────

loadDashboard().then(() => {
  setLastUpdatedNow();
});

startPolling();
