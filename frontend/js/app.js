// Main Application Logic
class AITeacherApp {
  constructor() {
    this.apiUrl = "http://localhost:8000";
    this.currentDocument = null;
    this.currentSession = null;
    this.websocket = null;
    this.studentProfile = {
      student_id: "student_" + Date.now(),
      name: "Student",
      level: "intermediate",
      learning_preferences: {},
    };

    this.initializeApp();
  }

  initializeApp() {
    this.setupEventListeners();
    this.initializeUI();
    console.log("AI Teacher App initialized");
  }

  setupEventListeners() {
    // File upload events
    const fileInput = document.getElementById("fileInput");
    const uploadArea = document.getElementById("uploadArea");
    const startLessonBtn = document.getElementById("startLessonBtn");
    const removeDocBtn = document.getElementById("removeDoc");

    fileInput.addEventListener("change", (e) => this.handleFileSelect(e));

    // Drag and drop
    uploadArea.addEventListener("dragover", (e) => this.handleDragOver(e));
    uploadArea.addEventListener("drop", (e) => this.handleFileDrop(e));
    uploadArea.addEventListener("click", () => fileInput.click());

    startLessonBtn.addEventListener("click", () => this.startLesson());
    removeDocBtn.addEventListener("click", () => this.removeDocument());

    // Chat events
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const micBtn = document.getElementById("micBtn");

    messageInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    sendBtn.addEventListener("click", () => this.sendMessage());
    micBtn.addEventListener("click", () => this.toggleVoiceInput());

    // Quick action buttons
    document.querySelectorAll(".quick-action-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => this.handleQuickAction(e));
    });

    // Notes tabs
    document.querySelectorAll(".notes-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => this.switchNotesTab(e));
    });

    // Modal events
    const closeSummary = document.getElementById("closeSummary");
    const newLesson = document.getElementById("newLesson");

    closeSummary.addEventListener("click", () => this.closeSummaryModal());
    newLesson.addEventListener("click", () => this.startNewLesson());
  }

  initializeUI() {
    // Set student name
    document.getElementById("studentName").textContent =
      this.studentProfile.name;

    // Show welcome screen initially
    this.showWelcomeScreen();
  }

  // File Upload Functions
  async handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
      await this.uploadDocument(file);
    }
  }

  handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add("dragover");
  }

  async handleFileDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove("dragover");

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      await this.uploadDocument(files[0]);
    }
  }

  async uploadDocument(file) {
    try {
      this.showLoading("Processing your document...");

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${this.apiUrl}/api/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const result = await response.json();
      this.currentDocument = result;

      this.showUploadedDocument(file);
      this.hideLoading();
    } catch (error) {
      console.error("Upload error:", error);
      this.showError("Failed to upload document. Please try again.");
      this.hideLoading();
    }
  }

  showUploadedDocument(file) {
    const uploadArea = document.getElementById("uploadArea");
    const uploadedDoc = document.getElementById("uploadedDoc");
    const docName = document.getElementById("docName");
    const docSize = document.getElementById("docSize");

    uploadArea.style.display = "none";
    uploadedDoc.style.display = "block";

    docName.textContent = file.name;
    docSize.textContent = this.formatFileSize(file.size);
  }

  removeDocument() {
    const uploadArea = document.getElementById("uploadArea");
    const uploadedDoc = document.getElementById("uploadedDoc");
    const fileInput = document.getElementById("fileInput");

    uploadArea.style.display = "block";
    uploadedDoc.style.display = "none";
    fileInput.value = "";

    this.currentDocument = null;
  }

  // Lesson Management
  async startLesson() {
    if (!this.currentDocument) {
      this.showError("Please upload a document first");
      return;
    }

    try {
      this.showLoading("Starting your lesson...");

      const response = await fetch(`${this.apiUrl}/api/sessions/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: this.currentDocument.document_id,
          student_profile: this.studentProfile,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to create session");
      }

      const result = await response.json();
      this.currentSession = result;

      this.showLessonInterface();
      this.connectWebSocket();
      this.hideLoading();
    } catch (error) {
      console.error("Start lesson error:", error);
      this.showError("Failed to start lesson. Please try again.");
      this.hideLoading();
    }
  }

  showLessonInterface() {
    document.getElementById("welcomeScreen").style.display = "none";
    document.getElementById("lessonInterface").style.display = "flex";

    // Add welcome message
    this.addMessage(
      "assistant",
      "Hello! I'm ready to help you learn from your document. What would you like to explore first?"
    );
  }

  showWelcomeScreen() {
    document.getElementById("welcomeScreen").style.display = "flex";
    document.getElementById("lessonInterface").style.display = "none";
  }

  // Chat Functions
  async sendMessage() {
    const messageInput = document.getElementById("messageInput");
    const message = messageInput.value.trim();

    if (!message || !this.websocket) return;

    // Add user message to chat
    this.addMessage("user", message);
    messageInput.value = "";

    // Send message via WebSocket
    this.websocket.send(
      JSON.stringify({
        type: "chat",
        content: message,
      })
    );
  }

  addMessage(role, content, options = {}) {
    const chatMessages = document.getElementById("chatMessages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    const avatarDiv = document.createElement("div");
    avatarDiv.className = "message-avatar";
    avatarDiv.innerHTML =
      role === "user"
        ? '<i class="fas fa-user"></i>'
        : '<i class="fas fa-robot"></i>';

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = content;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    // Add message actions for assistant messages
    if (role === "assistant") {
      const actionsDiv = document.createElement("div");
      actionsDiv.className = "message-actions";
      actionsDiv.innerHTML = `
                <button class="message-action" onclick="app.playTTS('${content}')">
                    <i class="fas fa-volume-up"></i> Listen
                </button>
                <button class="message-action" onclick="app.copyToClipboard('${content}')">
                    <i class="fas fa-copy"></i> Copy
                </button>
            `;
      contentDiv.appendChild(actionsDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Update subtitles for assistant messages
    if (role === "assistant") {
      this.updateSubtitles(content);
    }
  }

  updateSubtitles(text) {
    const subtitleText = document.getElementById("subtitleText");
    subtitleText.textContent = text;
  }

  handleQuickAction(event) {
    const action = event.currentTarget.dataset.action;
    const messageInput = document.getElementById("messageInput");

    const actionMessages = {
      explain: "Can you explain this concept in more detail?",
      example: "Can you give me an example of this?",
      practice: "Can we practice this topic?",
      summary: "Can you summarize what we've learned so far?",
    };

    messageInput.value = actionMessages[action] || "";
    messageInput.focus();
  }

  // Notes Management
  switchNotesTab(event) {
    const tabName = event.currentTarget.dataset.tab;

    // Update tab buttons
    document.querySelectorAll(".notes-tab").forEach((tab) => {
      tab.classList.remove("active");
    });
    event.currentTarget.classList.add("active");

    // Update tab panels
    document.querySelectorAll(".notes-panel").forEach((panel) => {
      panel.classList.remove("active");
    });
    document.getElementById(`${tabName}Panel`).classList.add("active");
  }

  addVocabularyItem(item) {
    const vocabularyList = document.getElementById("vocabularyList");

    // Remove empty state if it exists
    const emptyState = vocabularyList.querySelector(".empty-state");
    if (emptyState) {
      emptyState.remove();
    }

    const itemDiv = document.createElement("div");
    itemDiv.className = "vocabulary-item";
    itemDiv.innerHTML = `
            <h4>${item.word}</h4>
            <div class="vocabulary-definition">${item.definition}</div>
            <div class="vocabulary-example">"${item.example}"</div>
        `;

    vocabularyList.appendChild(itemDiv);
  }

  addGrammarNote(note) {
    const grammarList = document.getElementById("grammarList");

    // Remove empty state if it exists
    const emptyState = grammarList.querySelector(".empty-state");
    if (emptyState) {
      emptyState.remove();
    }

    const noteDiv = document.createElement("div");
    noteDiv.className = "grammar-item";
    noteDiv.innerHTML = `
            <h4>${note.rule}</h4>
            <div class="grammar-explanation">${note.explanation}</div>
            <div class="grammar-examples">${note.examples.join(", ")}</div>
        `;

    grammarList.appendChild(noteDiv);
  }

  // Audio Functions
  async playTTS(text) {
    try {
      const response = await fetch(`${this.apiUrl}/api/tts/synthesize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: text,
          language: "en",
        }),
      });

      if (!response.ok) {
        throw new Error("TTS failed");
      }

      const result = await response.json();
      const audio = document.getElementById("ttsAudio");
      audio.src = `data:audio/wav;base64,${result.audio_data}`;
      audio.play();
    } catch (error) {
      console.error("TTS error:", error);
    }
  }

  toggleVoiceInput() {
    // Voice input functionality will be implemented in audio.js
    if (window.audioManager) {
      window.audioManager.toggleRecording();
    }
  }

  // Utility Functions
  formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  showLoading(message) {
    const loadingOverlay = document.getElementById("loadingOverlay");
    const loadingText = document.getElementById("loadingText");

    loadingText.textContent = message;
    loadingOverlay.style.display = "flex";
  }

  hideLoading() {
    document.getElementById("loadingOverlay").style.display = "none";
  }

  showError(message) {
    // Simple error display - could be enhanced with a proper toast/notification system
    alert(message);
  }

  copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      console.log("Text copied to clipboard");
    });
  }

  // Session Summary
  async showSessionSummary() {
    if (!this.currentSession) return;

    try {
      const response = await fetch(
        `${this.apiUrl}/api/sessions/${this.currentSession.session_id}/summary`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to get summary");
      }

      const summary = await response.json();
      this.displaySummary(summary);
    } catch (error) {
      console.error("Summary error:", error);
      this.showError("Failed to generate summary");
    }
  }

  displaySummary(summary) {
    const summaryContent = document.getElementById("summaryContent");
    summaryContent.innerHTML = `
            <div class="summary-section">
                <h3>Key Concepts</h3>
                <ul>
                    ${summary.key_concepts
                      .map((concept) => `<li>${concept}</li>`)
                      .join("")}
                </ul>
            </div>
            <div class="summary-section">
                <h3>Vocabulary Learned</h3>
                <div class="vocabulary-summary">
                    ${summary.vocabulary_learned
                      .map(
                        (item) => `
                        <div class="vocab-item">
                            <strong>${item.word}</strong>: ${item.definition}
                        </div>
                    `
                      )
                      .join("")}
                </div>
            </div>
            <div class="summary-section">
                <h3>Recommendations</h3>
                <ul>
                    ${summary.recommendations
                      .map((rec) => `<li>${rec}</li>`)
                      .join("")}
                </ul>
            </div>
        `;

    document.getElementById("summaryModal").style.display = "flex";
  }

  closeSummaryModal() {
    document.getElementById("summaryModal").style.display = "none";
  }

  startNewLesson() {
    this.closeSummaryModal();
    this.currentSession = null;
    this.currentDocument = null;
    this.removeDocument();
    this.showWelcomeScreen();

    // Clear chat and notes
    document.getElementById("chatMessages").innerHTML = "";
    document.getElementById("vocabularyList").innerHTML =
      '<div class="empty-state"><i class="fas fa-book-open"></i><p>Vocabulary will appear here during the lesson</p></div>';
    document.getElementById("grammarList").innerHTML =
      '<div class="empty-state"><i class="fas fa-lightbulb"></i><p>Grammar notes will appear here during the lesson</p></div>';
  }

  // WebSocket connection (will be implemented in websocket.js)
  connectWebSocket() {
    if (window.websocketManager) {
      window.websocketManager.connect(this.currentSession.session_id);
    }
  }
}

// Initialize app when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.app = new AITeacherApp();
});
