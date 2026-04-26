const API_URL = "https://my-rag-backend-cjke.onrender.com/";

// ── State ─────────────────────────────────────────────────
let collectionId  = null;
let chatHistory   = [];
let isStreaming   = false;
let selectedFile  = null;
let statusInterval= null;

// ── DOM refs ──────────────────────────────────────────────
const fileInput      = document.getElementById("fileInput");
const uploadBox      = document.getElementById("uploadBox");
const uploadContent  = document.getElementById("uploadContent");
const uploadBtn      = document.getElementById("uploadBtn");
const statusBar      = document.getElementById("statusBar");
const statusDot      = document.getElementById("statusDot");
const statusText     = document.getElementById("statusText");
const messages       = document.getElementById("messages");
const questionInput  = document.getElementById("questionInput");
const sendBtn        = document.getElementById("sendBtn");
const clearBtn       = document.getElementById("clearBtn");
const topbarTitle    = document.getElementById("topbarTitle");
const topbarBadge    = document.getElementById("topbarBadge");

// ── File Selection ────────────────────────────────────────
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  selectedFile = file;

  uploadContent.innerHTML = `
    <div class="upload-icon">✅</div>
    <p class="upload-text">${file.name}</p>
    <p class="upload-hint">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
  `;
  uploadBtn.disabled = false;
});

// ── Drag & Drop ───────────────────────────────────────────
uploadBox.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadBox.classList.add("dragover");
});

uploadBox.addEventListener("dragleave", () => {
  uploadBox.classList.remove("dragover");
});

uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadBox.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith(".pdf")) {
    selectedFile = file;
    uploadContent.innerHTML = `
      <div class="upload-icon">✅</div>
      <p class="upload-text">${file.name}</p>
      <p class="upload-hint">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
    `;
    uploadBtn.disabled = false;
  }
});

// ── Upload & Index ────────────────────────────────────────
uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  const formData = new FormData();
  formData.append("file", selectedFile);

  uploadBtn.disabled   = true;
  uploadBtn.textContent = "Uploading...";
  statusBar.style.display = "flex";
  setStatus("indexing", "Uploading PDF...");

  try {
    const res  = await fetch(`${API_URL}/upload`, { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      setStatus("error", data.error);
      uploadBtn.disabled    = false;
      uploadBtn.textContent = "Upload & Index";
      return;
    }

    collectionId = data.collection_id;
    topbarTitle.textContent = selectedFile.name;
    setStatus("indexing", "Indexing your PDF...");

    // Poll status every 5 seconds
    statusInterval = setInterval(pollStatus, 5000);

  } catch (err) {
    setStatus("error", "Something Wrong Happened, wait for 30 secs");
    uploadBtn.disabled    = false;
    uploadBtn.textContent = "Upload & Index";
  }
});

// ── Poll Indexing Status ──────────────────────────────────
async function pollStatus() {
  if (!collectionId) return;
  try {
    const res  = await fetch(`${API_URL}/status/${collectionId}`);
    const data = await res.json();

    if (data.status === "done") {
      clearInterval(statusInterval);
      setStatus("done", "Ready to chat!");
      topbarBadge.style.display = "inline";
      enableChat();
      addBotMessage("✅ PDF indexed! Ask me anything about your document.");

    } else if (data.status.startsWith("error")) {
      clearInterval(statusInterval);
      setStatus("error", "Indexing failed — check backend logs");
    }
    // if still "indexing" — keep polling
  } catch (err) {
    console.error("Status poll failed:", err);
  }
}

// ── Set Status Bar ────────────────────────────────────────
function setStatus(type, text) {
  statusDot.className  = `status-dot ${type}`;
  statusText.textContent = text;
}

// ── Enable Chat Input ─────────────────────────────────────
function enableChat() {
  questionInput.disabled = false;
  sendBtn.disabled       = false;
  questionInput.focus();
  uploadBtn.textContent  = "Upload & Index";
}

// ── Send Message ──────────────────────────────────────────
sendBtn.addEventListener("click", sendMessage);

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Auto-resize textarea
questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = questionInput.scrollHeight + "px";
});

async function sendMessage() {
  const question = questionInput.value.trim();
  if (!question || isStreaming || !collectionId) return;

  // Clear empty state if first message
  const emptyState = messages.querySelector(".empty-state");
  if (emptyState) emptyState.remove();

  // Add user message
  addUserMessage(question);
  questionInput.value = "";
  questionInput.style.height = "auto";

  // Lock input while streaming
  isStreaming            = true;
  sendBtn.disabled       = true;
  questionInput.disabled = true;

  // Create bot bubble
  const botBubble = addBotMessage("", true);

  try {
    const res = await fetch(`${API_URL}/chat`, {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({
        question,
        collection_id: collectionId,
        chat_history : chatHistory
      })
    });

    // Stream response token by token
    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   fullReply = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const token = decoder.decode(value);
      fullReply  += token;
      botBubble.textContent = fullReply;
      scrollToBottom();
    }

    // Done streaming — remove cursor
    botBubble.classList.remove("streaming");

    // Save to history (only raw question, not context)
    chatHistory.push({ role: "user",      content: question   });
    chatHistory.push({ role: "assistant", content: fullReply  });

    // Keep last 12 messages (6 turns)
    if (chatHistory.length > 12) chatHistory = chatHistory.slice(-12);

  } catch (err) {
    botBubble.textContent = "❌ Something went wrong — check if backend is running.";
    botBubble.classList.remove("streaming");
  }

  // Unlock input
  isStreaming            = false;
  sendBtn.disabled       = false;
  questionInput.disabled = false;
  questionInput.focus();
}

// ── Add Messages to UI ────────────────────────────────────
function addUserMessage(text) {
  const msg = document.createElement("div");
  msg.className = "message user";
  msg.innerHTML = `
    <div class="avatar">🧑</div>
    <div class="bubble">${escapeHtml(text)}</div>
  `;
  messages.appendChild(msg);
  scrollToBottom();
}

function addBotMessage(text, streaming = false) {
  const msg = document.createElement("div");
  msg.className = "message bot";

  const bubble = document.createElement("div");
  bubble.className = streaming ? "bubble streaming" : "bubble";
  bubble.textContent = text;

  msg.innerHTML = `<div class="avatar">⚡</div>`;
  msg.appendChild(bubble);
  messages.appendChild(msg);
  scrollToBottom();

  return bubble;  // return bubble so we can update it while streaming
}

// ── Helpers ───────────────────────────────────────────────
function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Clear Chat ────────────────────────────────────────────
clearBtn.addEventListener("click", () => {
  chatHistory = [];
  messages.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🤖</div>
      <h2>Chat cleared</h2>
      <p>Ask anything about your document.</p>
    </div>
  `;
});