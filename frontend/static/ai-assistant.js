/**
 * OT Sentinel — AI Assistant page (Phase 3 placeholder)
 */

if (!requireAuth()) {
  throw new Error("Not authenticated");
}

initPageHeader();

// Chat UI is intentionally disabled; Phase 3 will implement it.
// No API calls needed for this page in Phase 1.

const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

if (chatInput) {
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      showToast("AI Assistant coming in Phase 3!", "error", 2000);
    }
  });
}

if (chatSend) {
  chatSend.addEventListener("click", function () {
    showToast("AI Assistant coming in Phase 3!", "error", 2000);
  });
}
