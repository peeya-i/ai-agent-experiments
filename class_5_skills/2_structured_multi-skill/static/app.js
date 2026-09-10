/**
 * Antigravity Multi-Skill Agent Frontend Logic
 * Implements 2-page navigation, chat interaction, and dynamic log inspection with JSON modal.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Navigation elements
  const navBtnChat = document.getElementById("nav-btn-chat");
  const navBtnLogs = document.getElementById("nav-btn-logs");
  const pageChat = document.getElementById("page-chat");
  const pageLogs = document.getElementById("page-logs");

  // Chat elements
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatSendBtn = document.getElementById("chat-send-btn");
  const chatMessages = document.getElementById("chat-messages");
  const promptChips = document.getElementById("prompt-chips");
  const newChatBtn = document.getElementById("new-chat-btn");
  const chatSessionBadge = document.getElementById("chat-session-badge");

  // Log Review elements
  const refreshLogsBtn = document.getElementById("refresh-logs-btn");
  const conversationsCount = document.getElementById("conversations-count");
  const conversationsTbody = document.getElementById("conversations-tbody");
  const selectedConvBadge = document.getElementById("selected-conv-badge");
  const eventsCount = document.getElementById("events-count");
  const eventsTbody = document.getElementById("events-tbody");

  // Modal elements
  const jsonModal = document.getElementById("json-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalCopyBtn = document.getElementById("modal-copy-btn");
  const modalTitle = document.getElementById("modal-title");
  const modalEventTypeBadge = document.getElementById("modal-event-type-badge");
  const modalEventId = document.getElementById("modal-event-id");
  const modalTimestamp = document.getElementById("modal-timestamp");
  const modalInvokerTarget = document.getElementById("modal-invoker-target");
  const modalShortDesc = document.getElementById("modal-short-desc");
  const modalJsonContent = document.getElementById("modal-json-content");

  // Application State
  let currentConversationId = null;
  let selectedLogConversationId = null;
  let cachedEvents = {};

  // ================= 1. Navigation Switching =================
  function switchPage(page) {
    if (page === "chat") {
      navBtnChat.classList.add("active");
      navBtnChat.setAttribute("aria-selected", "true");
      navBtnLogs.classList.remove("active");
      navBtnLogs.setAttribute("aria-selected", "false");

      pageChat.classList.add("active");
      pageLogs.classList.remove("active");
    } else if (page === "logs") {
      navBtnLogs.classList.add("active");
      navBtnLogs.setAttribute("aria-selected", "true");
      navBtnChat.classList.remove("active");
      navBtnChat.setAttribute("aria-selected", "false");

      pageLogs.classList.add("active");
      pageChat.classList.remove("active");

      loadConversations();
    }
  }

  navBtnChat.addEventListener("click", () => switchPage("chat"));
  navBtnLogs.addEventListener("click", () => switchPage("logs"));

  // ================= 2. Chat Functionality =================
  function appendMessage(sender, text, timestamp = null) {
    const timeStr = timestamp || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const isUser = sender === "user";

    const card = document.createElement("div");
    card.className = `message-card ${isUser ? "user-message" : "agent-message"}`;

    card.innerHTML = `
      <div class="message-avatar">${isUser ? "👤" : "⚡"}</div>
      <div class="message-body">
        <div class="message-header">
          <span class="message-sender">${isUser ? "You" : "Multi-Skill Agent"}</span>
          <span class="message-time">${timeStr}</span>
        </div>
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    `;

    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return card;
  }

  function appendLoadingMessage() {
    const card = document.createElement("div");
    card.className = "message-card agent-message loading-card";
    card.id = "chat-loading-indicator";

    card.innerHTML = `
      <div class="message-avatar">⚡</div>
      <div class="message-body">
        <div class="message-header">
          <span class="message-sender">Multi-Skill Agent</span>
          <span class="message-time">Thinking & executing skills...</span>
        </div>
        <div class="message-text">
          <span style="font-style: italic; color: var(--text-secondary);">Querying domain skills & generating response...</span>
        </div>
      </div>
    `;

    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function removeLoadingMessage() {
    const loadingCard = document.getElementById("chat-loading-indicator");
    if (loadingCard) {
      loadingCard.remove();
    }
  }

  async function handleSendMessage(queryText) {
    const text = (queryText || chatInput.value).trim();
    if (!text) return;

    chatInput.value = "";
    appendMessage("user", text);
    appendLoadingMessage();
    chatSendBtn.disabled = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
        }),
      });

      removeLoadingMessage();

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server error occurred");
      }

      const data = await response.json();
      currentConversationId = data.conversation_id;
      if (chatSessionBadge) {
        chatSessionBadge.textContent = currentConversationId;
        chatSessionBadge.classList.remove("new-session");
      }
      appendMessage("agent", data.response);
    } catch (err) {
      removeLoadingMessage();
      appendMessage("agent", `⚠️ Error: ${err.message}`);
    } finally {
      chatSendBtn.disabled = false;
      chatInput.focus();
    }
  }

  // Initial welcome message template
  const WELCOME_TEMPLATE = `
    <div class="message-card agent-message">
      <div class="message-avatar">⚡</div>
      <div class="message-body">
        <div class="message-header">
          <span class="message-sender">Multi-Skill Agent</span>
          <span class="message-time">Just now</span>
        </div>
        <div class="message-text">
          <p>Hello! I am your autonomous AI assistant equipped with domain skills:</p>
          <ul class="skills-bullet-list">
            <li><strong>🌦️ datetime-weather-skill:</strong> Real-time weather, temperature, humidity, wind, and local clock/timezone analytics via OpenStreetMap Nominatim and Open-Meteo.</li>
            <li><strong>🏡 house-registry-skill:</strong> Verified property records (resident name, city, country, house color) scanned against the flat-file database without hallucinations.</li>
            <li><strong>🌿 plant-care-skill:</strong> Comprehensive botanical profiles and structured plant care guides (soil, light, watering, temperature, maintenance, propagation, safety).</li>
          </ul>
          <p>How can I assist you today?</p>
        </div>
      </div>
    </div>
  `;

  function startNewChat() {
    currentConversationId = null;
    if (chatSessionBadge) {
      chatSessionBadge.textContent = "New Chat";
      chatSessionBadge.classList.add("new-session");
    }
    chatMessages.innerHTML = WELCOME_TEMPLATE;
    chatInput.value = "";
    chatInput.focus();
  }

  if (newChatBtn) {
    newChatBtn.addEventListener("click", startNewChat);
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Prompt chips
  promptChips.addEventListener("click", (e) => {
    const chip = e.target.closest(".prompt-chip");
    if (chip) {
      const prompt = chip.dataset.prompt;
      if (prompt) {
        handleSendMessage(prompt);
      }
    }
  });

  // ================= 3. Log Review Functionality =================
  async function loadConversations() {
    conversationsTbody.innerHTML = `<tr><td colspan="4" class="table-empty">Loading conversations...</td></tr>`;

    try {
      const resp = await fetch("/api/conversations");
      const data = await resp.json();
      const conversations = data.conversations || [];

      conversationsCount.textContent = `${conversations.length} conversation${conversations.length === 1 ? "" : "s"}`;

      if (conversations.length === 0) {
        conversationsTbody.innerHTML = `<tr><td colspan="4" class="table-empty">No conversations recorded yet. Send a message on Page 1 to generate logs.</td></tr>`;
        return;
      }

      conversationsTbody.innerHTML = "";
      conversations.forEach((conv) => {
        const row = document.createElement("tr");
        row.dataset.conversationId = conv.conversation_id;
        if (selectedLogConversationId === conv.conversation_id) {
          row.classList.add("selected");
        }

        const formattedTime = formatTimestamp(conv.timestamp);

        row.innerHTML = `
          <td><code style="color: #a5b4fc;">${escapeHtml(conv.conversation_id)}</code></td>
          <td style="color: var(--text-secondary); font-size: 0.8rem;">${formattedTime}</td>
          <td>${escapeHtml(truncate(conv.user_query, 70))}</td>
          <td>${escapeHtml(truncate(conv.agent_response, 70))}</td>
        `;

        row.addEventListener("click", () => {
          document.querySelectorAll("#conversations-tbody tr").forEach((r) => r.classList.remove("selected"));
          row.classList.add("selected");
          selectConversation(conv.conversation_id);
        });

        conversationsTbody.appendChild(row);
      });

      // Auto-select first conversation if none selected
      if (!selectedLogConversationId && conversations.length > 0) {
        const firstRow = conversationsTbody.querySelector("tr");
        if (firstRow) {
          firstRow.classList.add("selected");
          selectConversation(conversations[0].conversation_id);
        }
      } else if (selectedLogConversationId) {
        selectConversation(selectedLogConversationId);
      }
    } catch (err) {
      conversationsTbody.innerHTML = `<tr><td colspan="4" class="table-empty" style="color: #ef4444;">Failed to load conversations: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  async function selectConversation(conversationId) {
    selectedLogConversationId = conversationId;
    selectedConvBadge.textContent = `Conversation: ${conversationId}`;
    eventsTbody.innerHTML = `<tr><td colspan="5" class="table-empty">Loading events for ${escapeHtml(conversationId)}...</td></tr>`;

    try {
      const resp = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/events`);
      const data = await resp.json();
      const events = data.events || [];

      cachedEvents[conversationId] = events;
      eventsCount.textContent = `${events.length} event${events.length === 1 ? "" : "s"}`;

      if (events.length === 0) {
        eventsTbody.innerHTML = `<tr><td colspan="5" class="table-empty">No events found for this conversation.</td></tr>`;
        return;
      }

      eventsTbody.innerHTML = "";
      events.forEach((ev) => {
        const row = document.createElement("tr");
        row.dataset.eventId = ev.event_id;

        const badgeClass = getBadgeClass(ev.event_type);
        const formattedTime = formatTimestamp(ev.timestamp);

        row.innerHTML = `
          <td style="color: var(--text-secondary); font-size: 0.8rem;">${formattedTime}</td>
          <td><span class="event-badge ${badgeClass}">${escapeHtml(ev.event_type)}</span></td>
          <td style="font-weight: 500;">${escapeHtml(ev.invoker)}</td>
          <td style="color: var(--text-secondary);">${escapeHtml(ev.target)}</td>
          <td style="color: var(--text-primary); font-size: 0.84rem;">${escapeHtml(truncate(ev.short_description || "-", 85))}</td>
        `;

        row.addEventListener("click", () => {
          showEventModal(ev);
        });

        eventsTbody.appendChild(row);
      });
    } catch (err) {
      eventsTbody.innerHTML = `<tr><td colspan="5" class="table-empty" style="color: #ef4444;">Failed to load events: ${escapeHtml(err.message)}</td></tr>`;
    }
  }

  refreshLogsBtn.addEventListener("click", () => {
    loadConversations();
  });

  // ================= 4. JSON Modal Viewer =================
  function showEventModal(ev) {
    modalEventTypeBadge.textContent = ev.event_type;
    modalEventTypeBadge.className = `event-badge ${getBadgeClass(ev.event_type)}`;

    modalTitle.textContent = `Event Audit: ${ev.event_type}`;
    modalEventId.textContent = ev.event_id || "N/A";
    modalTimestamp.textContent = ev.timestamp;
    modalInvokerTarget.textContent = `${ev.invoker} ➔ ${ev.target}`;
    if (modalShortDesc) {
      modalShortDesc.textContent = ev.short_description || "-";
    }

    // Clean JSON formatting
    const formattedJson = JSON.stringify(ev, null, 2);
    modalJsonContent.textContent = formattedJson;

    jsonModal.classList.add("open");
    jsonModal.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    jsonModal.classList.remove("open");
    jsonModal.setAttribute("aria-hidden", "true");
  }

  modalCloseBtn.addEventListener("click", closeModal);
  jsonModal.addEventListener("click", (e) => {
    if (e.target === jsonModal) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && jsonModal.classList.contains("open")) {
      closeModal();
    }
  });

  modalCopyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(modalJsonContent.textContent);
      const span = modalCopyBtn.querySelector("span");
      const origText = span.textContent;
      span.textContent = "Copied!";
      setTimeout(() => {
        span.textContent = origText;
      }, 1500);
    } catch (err) {
      alert("Failed to copy JSON to clipboard.");
    }
  });

  // ================= Utilities =================
  function getBadgeClass(eventType) {
    switch (eventType) {
      case "USER_QUERY":
        return "badge-user-query";
      case "AGENT_INVOCATION":
        return "badge-agent-invoc";
      case "LLM_REQUEST":
        return "badge-llm-req";
      case "LLM_RESPONSE":
        return "badge-llm-resp";
      case "TOOL_INVOCATION":
        return "badge-tool-invoc";
      case "TOOL_RESPONSE":
        return "badge-tool-resp";
      case "EXTERNAL_API_REQUEST":
        return "badge-api-req";
      case "EXTERNAL_API_RESPONSE":
        return "badge-api-resp";
      case "AGENT_RESPONSE":
        return "badge-agent-resp";
      default:
        return "badge-user-query";
    }
  }

  function formatTimestamp(isoStr) {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) + " " + d.toLocaleDateString();
    } catch (e) {
      return isoStr;
    }
  }

  function truncate(str, maxLen = 60) {
    if (!str) return "-";
    return str.length > maxLen ? str.slice(0, maxLen) + "..." : str;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
