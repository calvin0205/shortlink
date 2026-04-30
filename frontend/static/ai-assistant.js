/**
 * OT Sentinel — AI Assistant page (Phase 3)
 */

requireAuth();
initPageHeader();

let incidents = [];

async function init() {
    await loadIncidents();
    await loadSuggestedQueries();
}

async function loadIncidents() {
    try {
        const data = await apiFetch("/api/incidents");
        incidents = Array.isArray(data) ? data : [];
        const select = document.getElementById("incident-context");
        incidents.forEach(function(inc) {
            const opt = document.createElement("option");
            opt.value = inc.incident_id;
            opt.textContent = "[" + inc.severity.toUpperCase() + "] " + inc.title + " — " + inc.device_name;
            select.appendChild(opt);
        });
    } catch (err) {
        // Non-fatal — continue without incident list
    }
}

async function loadSuggestedQueries() {
    try {
        const data = await apiFetch("/api/assistant/suggested-queries");
        const container = document.getElementById("suggested-queries");
        (data.queries || []).forEach(function(q) {
            const btn = document.createElement("button");
            btn.className = "suggested-query-btn";
            btn.textContent = q;
            btn.onclick = function() {
                document.getElementById("chat-input").value = q;
                sendMessage();
            };
            container.appendChild(btn);
        });
    } catch (err) {
        // Non-fatal
    }
}

function handleChatKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message) return;

    const incidentId = document.getElementById("incident-context").value || null;
    input.value = "";

    // Add user message to chat
    appendUserMessage(message);

    // Show typing indicator
    const typingId = appendTypingIndicator();

    const sendBtn = document.getElementById("send-btn");
    sendBtn.disabled = true;

    try {
        const data = await apiFetch("/api/assistant/query", {
            method: "POST",
            body: JSON.stringify({ message: message, incident_id: incidentId }),
        });
        removeTypingIndicator(typingId);
        appendAIResponse(data);
    } catch (err) {
        removeTypingIndicator(typingId);
        appendErrorMessage("Failed to get response. Please try again.");
    } finally {
        sendBtn.disabled = false;
    }
}

function appendUserMessage(content) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message chat-message-user";
    div.innerHTML = '<div class="chat-bubble">' + escapeHtml(content) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendErrorMessage(content) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message chat-message-error";
    div.innerHTML = '<div class="chat-bubble">' + escapeHtml(content) + '</div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendAIResponse(data) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = "chat-message chat-message-ai";

    // Format the answer (convert **bold** markdown)
    const formattedAnswer = (data.answer || "")
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    let html = '<div class="chat-bubble ai-bubble">'
        + '<div class="ai-answer">' + formattedAnswer + '</div>';

    if (data.incident_context) {
        html += '<div class="ai-context-badge">'
            + '📋 Context: ' + escapeHtml(data.incident_context.title || "")
            + ' — <span class="badge badge-' + (data.incident_context.severity || "") + '">'
            + escapeHtml((data.incident_context.severity || "").toUpperCase()) + '</span>'
            + ' (Risk: ' + (data.incident_context.risk_score || 0) + ')'
            + '</div>';
    }

    if (data.recommendations && data.recommendations.length > 0) {
        html += '<div class="ai-section">'
            + '<div class="ai-section-title">✅ Recommendations</div>'
            + '<ol class="ai-recommendations">'
            + data.recommendations.map(function(r) { return '<li>' + escapeHtml(r) + '</li>'; }).join('')
            + '</ol>'
            + '</div>';
    }

    if (data.references && data.references.length > 0) {
        html += '<div class="ai-section">'
            + '<div class="ai-section-title">📚 References</div>'
            + '<div class="ai-references">'
            + data.references.map(function(r) { return '<span class="ref-badge">' + escapeHtml(r) + '</span>'; }).join('')
            + '</div>'
            + '</div>';
    }

    const sourceLabel = data.source === "llm" ? "🧠 Claude AI" : "📖 Rule Engine";
    html += '<div class="ai-source">' + sourceLabel + '</div>';
    html += '</div>';

    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
    const container = document.getElementById("chat-messages");
    const id = "typing-" + Date.now();
    const div = document.createElement("div");
    div.id = id;
    div.className = "chat-message chat-message-ai";
    div.innerHTML = '<div class="chat-bubble typing-indicator"><span></span><span></span><span></span></div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
}

init();
