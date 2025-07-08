// WebSocket Manager for real-time communication
class WebSocketManager {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect(sessionId) {
    const wsUrl = `ws://localhost:8000/ws/${sessionId}`;

    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventListeners();
      console.log("Connecting to WebSocket:", wsUrl);
    } catch (error) {
      console.error("WebSocket connection error:", error);
      this.handleConnectionError();
    }
  }

  setupEventListeners() {
    this.socket.onopen = (event) => {
      console.log("WebSocket connected");
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.updateConnectionStatus("connected");
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    this.socket.onclose = (event) => {
      console.log("WebSocket disconnected:", event.code, event.reason);
      this.isConnected = false;
      this.updateConnectionStatus("disconnected");

      // Attempt to reconnect if not a clean close
      if (
        event.code !== 1000 &&
        this.reconnectAttempts < this.maxReconnectAttempts
      ) {
        this.attemptReconnect();
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.handleConnectionError();
    };
  }

  handleMessage(data) {
    switch (data.type) {
      case "chat_response":
        this.handleChatResponse(data);
        break;
      case "vocabulary_update":
        this.handleVocabularyUpdate(data);
        break;
      case "grammar_update":
        this.handleGrammarUpdate(data);
        break;
      case "error":
        this.handleError(data);
        break;
      default:
        console.log("Unknown message type:", data.type);
    }
  }

  handleChatResponse(data) {
    // Add AI response to chat
    if (window.app) {
      window.app.addMessage("assistant", data.content);

      // Update learning notes
      if (data.vocabulary && data.vocabulary.length > 0) {
        data.vocabulary.forEach((item) => {
          window.app.addVocabularyItem(item);
        });
      }

      if (data.grammar && data.grammar.length > 0) {
        data.grammar.forEach((note) => {
          window.app.addGrammarNote(note);
        });
      }
    }
  }

  handleVocabularyUpdate(data) {
    if (window.app && data.items) {
      data.items.forEach((item) => {
        window.app.addVocabularyItem(item);
      });
    }
  }

  handleGrammarUpdate(data) {
    if (window.app && data.notes) {
      data.notes.forEach((note) => {
        window.app.addGrammarNote(note);
      });
    }
  }

  handleError(data) {
    console.error("WebSocket error message:", data.error);
    if (window.app) {
      window.app.showError(data.error);
    }
  }

  sendMessage(message) {
    if (this.isConnected && this.socket) {
      this.socket.send(JSON.stringify(message));
      return true;
    } else {
      console.error("WebSocket not connected");
      return false;
    }
  }

  attemptReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`
    );

    setTimeout(() => {
      if (!this.isConnected && window.app && window.app.currentSession) {
        this.connect(window.app.currentSession.session_id);
      }
    }, delay);
  }

  updateConnectionStatus(status) {
    const statusIndicator = document.getElementById("statusIndicator");
    const avatarStatus = document.getElementById("avatarStatus");

    if (statusIndicator && avatarStatus) {
      switch (status) {
        case "connected":
          statusIndicator.style.backgroundColor = "#10b981";
          avatarStatus.textContent = "Ready to teach";
          break;
        case "connecting":
          statusIndicator.style.backgroundColor = "#f59e0b";
          avatarStatus.textContent = "Connecting...";
          break;
        case "disconnected":
          statusIndicator.style.backgroundColor = "#ef4444";
          avatarStatus.textContent = "Disconnected";
          break;
      }
    }
  }

  handleConnectionError() {
    this.updateConnectionStatus("disconnected");
    if (window.app) {
      window.app.showError(
        "Connection lost. Please check your internet connection."
      );
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close(1000, "User initiated disconnect");
      this.socket = null;
      this.isConnected = false;
    }
  }

  // Public methods for sending different types of messages
  sendChatMessage(content) {
    return this.sendMessage({
      type: "chat",
      content: content,
    });
  }

  sendVoiceMessage(audioData) {
    return this.sendMessage({
      type: "voice",
      audio_data: audioData,
    });
  }

  requestSessionSummary() {
    return this.sendMessage({
      type: "request_summary",
    });
  }

  sendUserAction(action, data = {}) {
    return this.sendMessage({
      type: "user_action",
      action: action,
      data: data,
    });
  }
}

// Initialize WebSocket manager
document.addEventListener("DOMContentLoaded", () => {
  window.websocketManager = new WebSocketManager();

  // Override app's WebSocket connection method
  if (window.app) {
    window.app.connectWebSocket = function () {
      if (this.currentSession) {
        window.websocketManager.connect(this.currentSession.session_id);
      }
    };

    // Override send message to use WebSocket
    const originalSendMessage = window.app.sendMessage;
    window.app.sendMessage = function () {
      const messageInput = document.getElementById("messageInput");
      const message = messageInput.value.trim();

      if (!message) return;

      // Add user message to chat
      this.addMessage("user", message);
      messageInput.value = "";

      // Send via WebSocket
      window.websocketManager.sendChatMessage(message);
    };
  }
});

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  if (window.websocketManager) {
    window.websocketManager.disconnect();
  }
});
