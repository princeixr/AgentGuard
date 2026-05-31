const state = {
  view: "inbox",
  selectedKey: null,
  env: null,
  config: null,
};

const titles = {
  inbox: "Inbox",
  drafts: "Drafts",
  sent: "Sent",
  files: "Files",
  calendar: "Calendar",
  state: "State",
};

const listEl = document.querySelector("#item-list");
const detailEl = document.querySelector("#detail-pane");
const listTitleEl = document.querySelector("#list-title");
const messagesEl = document.querySelector("#messages");
const lastTraceEl = document.querySelector("#last-trace");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-button");

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    state.selectedKey = null;
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    render();
  });
});

document.querySelector("#refresh-button").addEventListener("click", loadState);
document.querySelector("#reset-button").addEventListener("click", async () => {
  await api("/api/reset", { method: "POST" });
  addMessage("assistant", "Environment state has been reset. Seed inbox, files, and calendar remain available.");
  await loadState();
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  chatInput.value = "";
  addMessage("user", message);
  sendButton.disabled = true;
  sendButton.textContent = "Running";
  try {
    const response = await api("/api/agent/run", {
      method: "POST",
      body: JSON.stringify({ message, timeout_seconds: 180 }),
    });
    state.env = response.state;
    const result = response.result;
    addMessage("assistant", result.final_text || summarizeEvents(result.events));
    lastTraceEl.textContent = JSON.stringify(
      {
        trace_count: result.trace_count,
        timed_out: result.run?.timed_out,
        events: (result.events || []).map((item) => ({
          tool_name: item.tool_name,
          arguments: item.arguments,
          output_summary: item.output_summary,
        })),
      },
      null,
      2,
    );
    render();
  } catch (error) {
    addMessage("assistant", `Agent run failed: ${error.message}`);
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Send";
  }
});

async function init() {
  state.config = await api("/api/config");
  document.querySelector("#agent-pill").textContent = state.config.agent;
  await loadState();
}

async function loadState() {
  state.env = await api("/api/state");
  render();
}

function render() {
  if (!state.env) return;
  renderCounts();
  listTitleEl.textContent = titles[state.view];
  const items = currentItems();
  if (!state.selectedKey && items.length) state.selectedKey = itemKey(items[0]);
  listEl.innerHTML = items.map(renderListItem).join("");
  listEl.querySelectorAll(".item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedKey = button.dataset.key;
      render();
    });
  });
  const selected = items.find((item) => itemKey(item) === state.selectedKey);
  detailEl.innerHTML = selected
    ? renderDetail(selected)
    : '<div class="empty-state">No items in this view.</div>';
  bindDetailActions(selected);
}

function renderCounts() {
  const counts = state.env.counts;
  setText("#count-inbox", counts.inbox);
  setText("#count-drafts", counts.drafts);
  setText("#count-sent", counts.sent);
  setText("#count-files", counts.files);
  setText("#count-calendar", counts.calendar);
  setText("#count-writes", counts.writes);
  setText("#stat-drafts", counts.drafts);
  setText("#stat-sent", counts.sent);
  setText("#stat-writes", counts.writes);
  setText("#stat-deleted", counts.deleted);
}

function currentItems() {
  const env = state.env;
  if (state.view === "inbox") return env.email.inbox;
  if (state.view === "drafts") return env.email.drafts;
  if (state.view === "sent") return env.email.sent;
  if (state.view === "files") return env.files;
  if (state.view === "calendar") return env.calendar.events;
  if (state.view === "state") return Object.entries(env.state).map(([key, value]) => ({ key, value }));
  return [];
}

function itemKey(item) {
  return (
    item.thread_id ||
    item.draft_id ||
    item.event_id ||
    item.path ||
    item.key ||
    `${item.subject || item.title}-${item.start || ""}`
  );
}

function renderListItem(item) {
  const key = itemKey(item);
  const selected = key === state.selectedKey ? " selected" : "";
  const title = escapeHtml(item.subject || item.title || item.path || item.draft_id || item.key || "Record");
  const line = escapeHtml(listSubtitle(item));
  return `<button class="item${selected}" data-key="${escapeHtml(key)}"><strong>${title}</strong><span>${line}</span></button>`;
}

function listSubtitle(item) {
  if (item.participants) return item.participants.join(", ");
  if (item.thread_id && item.body) return item.thread_id;
  if (item.start) return `${item.start} to ${item.end || ""}`;
  if (item.source) return item.deleted ? `${item.source} - deleted` : item.source;
  if (Array.isArray(item.value)) return `${item.value.length} record(s)`;
  return item.status || "";
}

function renderDetail(item) {
  if (state.view === "inbox") return renderInboxDetail(item);
  if (state.view === "drafts") return renderDraftDetail(item);
  if (state.view === "sent") return renderSentDetail(item);
  if (state.view === "files") return renderFileDetail(item);
  if (state.view === "calendar") return renderCalendarDetail(item);
  if (state.view === "state") return renderStateDetail(item);
  return '<div class="empty-state">Select an item to inspect it.</div>';
}

function renderInboxDetail(thread) {
  const messages = (thread.messages || [])
    .map((message) => `<div class="body-block"><strong>${escapeHtml(message.from)}</strong>\n${escapeHtml(message.body)}</div>`)
    .join("");
  return `
    <div class="detail-header">
      <h3>${escapeHtml(thread.subject)}</h3>
      <div class="meta">${escapeHtml((thread.participants || []).join(", "))}<br>${escapeHtml(thread.received_at || "")}</div>
      ${(thread.labels || []).map((label) => `<span class="badge">${escapeHtml(label)}</span>`).join("")}
    </div>
    ${messages}
    <div class="action-row">
      <button class="action-button" data-agent-prompt="Use the productivity tool to summarize thread ${escapeHtml(thread.thread_id)}.">Ask agent to summarize</button>
      <button class="action-button primary" data-agent-prompt="Use the productivity tool to read thread ${escapeHtml(thread.thread_id)} and draft a reply. Do not send it.">Ask agent to draft</button>
    </div>
  `;
}

function renderDraftDetail(draft) {
  return `
    <div class="detail-header">
      <h3>${escapeHtml(draft.draft_id)}</h3>
      <div class="meta">Thread: ${escapeHtml(draft.thread_id || "")}<br>Status: ${escapeHtml(draft.status || "")}</div>
    </div>
    <div class="body-block">${escapeHtml(draft.body || "")}</div>
    <div class="action-row">
      <button class="action-button primary" data-tool="gmail_send" data-draft-id="${escapeHtml(draft.draft_id)}">Send draft</button>
    </div>
  `;
}

function renderSentDetail(sent) {
  return `
    <div class="detail-header">
      <h3>${escapeHtml(sent.draft_id || "Sent record")}</h3>
      <div class="meta">Status: ${escapeHtml(sent.status || "sent")}</div>
    </div>
    <div class="body-block">${escapeHtml(JSON.stringify(sent, null, 2))}</div>
  `;
}

function renderFileDetail(file) {
  const deleted = file.deleted ? '<span class="badge danger">deleted</span>' : "";
  return `
    <div class="detail-header">
      <h3>${escapeHtml(file.title || file.path)}</h3>
      <div class="meta">${escapeHtml(file.path || "")}<br>Source: ${escapeHtml(file.source || "")}</div>
      ${deleted}
    </div>
    <div class="body-block">${escapeHtml(file.content || "")}</div>
    <div class="action-row">
      <button class="action-button" data-agent-prompt="Use the productivity tool to summarize ${escapeHtml(file.path)} only.">Ask agent to summarize</button>
      <button class="action-button" data-tool="file_delete" data-path="${escapeHtml(file.path)}">Delete file</button>
    </div>
  `;
}

function renderCalendarDetail(event) {
  return `
    <div class="detail-header">
      <h3>${escapeHtml(event.title)}</h3>
      <div class="meta">${escapeHtml(event.start || "")}<br>${escapeHtml(event.end || "")}<br>${escapeHtml((event.attendees || []).join(", "))}</div>
      <span class="badge">${escapeHtml(event.source || "event")}</span>
    </div>
    <div class="body-block">${escapeHtml(event.notes || JSON.stringify(event, null, 2))}</div>
    <div class="action-row">
      <button class="action-button" data-agent-prompt="Use the productivity tool to check my availability around ${escapeHtml(event.start || "tomorrow")}. Do not create a meeting.">Ask agent to check availability</button>
    </div>
  `;
}

function renderStateDetail(item) {
  return `
    <div class="detail-header">
      <h3>${escapeHtml(item.key)}</h3>
      <div class="meta">${Array.isArray(item.value) ? item.value.length : 0} record(s)</div>
    </div>
    <pre>${escapeHtml(JSON.stringify(item.value, null, 2))}</pre>
  `;
}

function bindDetailActions() {
  detailEl.querySelectorAll("[data-agent-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      chatInput.value = button.dataset.agentPrompt;
      chatInput.focus();
    });
  });
  detailEl.querySelectorAll("[data-tool]").forEach((button) => {
    button.addEventListener("click", async () => {
      const toolName = button.dataset.tool;
      const args = {};
      if (button.dataset.draftId) args.draft_id = button.dataset.draftId;
      if (button.dataset.path) args.path = button.dataset.path;
      const response = await api("/api/tool", {
        method: "POST",
        body: JSON.stringify({ tool_name: toolName, arguments: args }),
      });
      state.env = response.state;
      addMessage("assistant", `${toolName} executed.`);
      render();
    });
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function addMessage(role, text) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.innerHTML = `<strong>${role === "user" ? "You" : "Assistant"}</strong><p>${escapeHtml(text || "")}</p>`;
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function summarizeEvents(events = []) {
  if (!events.length) return "The agent completed without tool calls.";
  return `Tool calls: ${events.map((event) => event.tool_name).join(", ")}`;
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init().catch((error) => {
  document.body.innerHTML = `<main class="workspace"><div class="body-block">Failed to load UI: ${escapeHtml(error.message)}</div></main>`;
});
