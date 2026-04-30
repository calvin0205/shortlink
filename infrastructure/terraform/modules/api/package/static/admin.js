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

async function loadUsers() {
  const section = document.getElementById("users-section");
  const countEl = document.getElementById("user-count");
  if (!section) return;

  if (!isAdmin()) {
    section.innerHTML = `<div class="empty-state" style="padding:32px"><p>🔒 Admin access required</p></div>`;
    return;
  }

  try {
    const users = await apiFetch("/api/admin/users");

    if (countEl) countEl.textContent = `${users.length} users`;

    if (users.length === 0) {
      section.innerHTML = `<div class="empty-state" style="padding:32px"><div class="empty-state-icon">👥</div><div>No users found</div></div>`;
      return;
    }

    section.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>User ID</th>
            </tr>
          </thead>
          <tbody>
            ${users
              .map(
                (u) => `
              <tr>
                <td>${u.name || "—"}</td>
                <td class="text-secondary">${u.email || "—"}</td>
                <td><span class="badge badge-${u.role === "admin" ? "admin" : "operator"}">${u.role || "—"}</span></td>
                <td><span class="font-mono text-secondary" style="font-size:0.75rem">${u.user_id || "—"}</span></td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  } catch (err) {
    if (err.status === 403) {
      section.innerHTML = `<div class="empty-state" style="padding:32px"><p>🔒 Admin access required</p></div>`;
    } else if (err.status !== 401) {
      section.innerHTML = `<div class="empty-state" style="padding:32px"><div class="empty-state-icon">❌</div><div>Failed to load users: ${err.message}</div></div>`;
    }
  }
}

renderUserInfo();
loadPlatformSummary();
loadUsers();
