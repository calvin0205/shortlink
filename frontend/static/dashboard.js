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

// Load on page ready
loadDashboard();
