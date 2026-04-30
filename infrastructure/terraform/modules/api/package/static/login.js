/**
 * OT Sentinel — Login page logic
 */

// If already authenticated, redirect to dashboard
if (getToken() && getUser()) {
  window.location.replace("/dashboard.html");
}

document.getElementById("login-form").addEventListener("submit", async function (e) {
  e.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("login-error");
  const btnEl = document.getElementById("login-btn");

  errorEl.style.display = "none";
  errorEl.textContent = "";
  btnEl.disabled = true;
  btnEl.textContent = "Signing in…";

  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    saveAuth(data.access_token, data.user);
    window.location.href = "/dashboard.html";
  } catch (err) {
    errorEl.textContent =
      err.status === 401
        ? "Invalid email or password. Please try again."
        : `Error: ${err.message}`;
    errorEl.style.display = "block";
    btnEl.disabled = false;
    btnEl.textContent = "Sign In";
  }
});
