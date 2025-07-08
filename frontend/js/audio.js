// Audio Manager for Speech Recognition and Text-to-Speech
class AudioManager {
  constructor() {
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.recognition = null;
    this.audioContext = null;
    this.stream = null;

    this.initializeSpeechRecognition();
    this.setupAudioElements();
  }

  initializeSpeechRecognition() {
    // Check for speech recognition support
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();

      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = "en-US";

      this.setupSpeechRecognitionEvents();
    } else {
      console.warn("Speech recognition not supported in this browser");
    }
  }

  setupSpeechRecognitionEvents() {
    this.recognition.onstart = () => {
      console.log("Speech recognition started");
      this.updateMicButtonState(true);
      this.showListeningIndicator();
    };

    this.recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      this.displayTranscription(finalTranscript, interimTranscript);

      if (finalTranscript) {
        this.handleSpeechResult(finalTranscript);
      }
    };

    this.recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      this.handleSpeechError(event.error);
    };

    this.recognition.onend = () => {
      console.log("Speech recognition ended");
      this.updateMicButtonState(false);
      this.hideListeningIndicator();
    };
  }

  setupAudioElements() {
    // Setup TTS audio element
    const ttsAudio = document.getElementById("ttsAudio");
    if (ttsAudio) {
      ttsAudio.onloadstart = () => {
        this.showAudioLoading();
      };

      ttsAudio.oncanplay = () => {
        this.hideAudioLoading();
      };

      ttsAudio.onplay = () => {
        this.updateAvatarState("speaking");
      };

      ttsAudio.onended = () => {
        this.updateAvatarState("idle");
      };

      ttsAudio.onerror = () => {
        this.hideAudioLoading();
        console.error("TTS audio error");
      };
    }
  }

  // Speech Recognition Methods
  toggleRecording() {
    if (!this.recognition) {
      this.showError("Speech recognition not supported in this browser");
      return;
    }

    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  startRecording() {
    try {
      this.isRecording = true;
      this.recognition.start();
      this.clearTranscriptionDisplay();
    } catch (error) {
      console.error("Error starting speech recognition:", error);
      this.isRecording = false;
      this.updateMicButtonState(false);
    }
  }

  stopRecording() {
    if (this.recognition) {
      this.recognition.stop();
    }
    this.isRecording = false;
  }

  handleSpeechResult(transcript) {
    const messageInput = document.getElementById("messageInput");
    if (messageInput) {
      messageInput.value = transcript;
      messageInput.focus();
    }

    // Auto-send if transcript seems complete
    if (transcript.trim().length > 5 && window.app) {
      setTimeout(() => {
        window.app.sendMessage();
      }, 500);
    }
  }

  handleSpeechError(error) {
    this.updateMicButtonState(false);
    this.hideListeningIndicator();

    let errorMessage = "Speech recognition error: ";
    switch (error) {
      case "no-speech":
        errorMessage += "No speech detected. Please try again.";
        break;
      case "audio-capture":
        errorMessage +=
          "No microphone found. Please check your microphone settings.";
        break;
      case "not-allowed":
        errorMessage +=
          "Microphone access denied. Please allow microphone access.";
        break;
      case "network":
        errorMessage += "Network error. Please check your internet connection.";
        break;
      default:
        errorMessage += error;
    }

    if (window.app) {
      window.app.showError(errorMessage);
    }
  }

  // Audio Recording for Server Processing
  async startAudioRecording() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      this.mediaRecorder.onstop = () => {
        this.processRecordedAudio();
      };

      this.mediaRecorder.start();
      this.updateMicButtonState(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      this.showError("Could not access microphone. Please check permissions.");
    }
  }

  stopAudioRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }

    this.updateMicButtonState(false);
  }

  async processRecordedAudio() {
    const audioBlob = new Blob(this.audioChunks, { type: "audio/wav" });

    try {
      // Send audio to server for transcription
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.wav");

      const response = await fetch("http://localhost:8000/api/stt/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Transcription failed");
      }

      const result = await response.json();
      this.handleSpeechResult(result.transcribed_text);
    } catch (error) {
      console.error("Audio processing error:", error);
      this.showError("Failed to process audio. Please try again.");
    }
  }

  // Text-to-Speech Methods
  async playTTS(text, language = "en") {
    try {
      this.showAudioLoading();

      const response = await fetch("http://localhost:8000/api/tts/synthesize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: text,
          language: language,
        }),
      });

      if (!response.ok) {
        throw new Error("TTS synthesis failed");
      }

      const result = await response.json();
      const audio = document.getElementById("ttsAudio");

      if (audio) {
        audio.src = `data:audio/wav;base64,${result.audio_data}`;
        await audio.play();
      }
    } catch (error) {
      console.error("TTS error:", error);
      this.hideAudioLoading();
      this.showError("Failed to generate speech. Please try again.");
    }
  }

  // UI Update Methods
  updateMicButtonState(isActive) {
    const micBtn = document.getElementById("micBtn");
    if (micBtn) {
      if (isActive) {
        micBtn.classList.add("recording");
        micBtn.innerHTML = '<i class="fas fa-stop"></i>';
        micBtn.title = "Stop Recording";
      } else {
        micBtn.classList.remove("recording");
        micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        micBtn.title = "Voice Input";
      }
    }
  }

  showListeningIndicator() {
    const statusIndicator = document.getElementById("statusIndicator");
    const avatarStatus = document.getElementById("avatarStatus");

    if (statusIndicator) {
      statusIndicator.style.backgroundColor = "#f59e0b";
      statusIndicator.style.animation = "pulse 1s infinite";
    }

    if (avatarStatus) {
      avatarStatus.textContent = "Listening...";
    }
  }

  hideListeningIndicator() {
    const statusIndicator = document.getElementById("statusIndicator");
    const avatarStatus = document.getElementById("avatarStatus");

    if (statusIndicator) {
      statusIndicator.style.backgroundColor = "#10b981";
      statusIndicator.style.animation = "";
    }

    if (avatarStatus) {
      avatarStatus.textContent = "Ready to teach";
    }
  }

  displayTranscription(final, interim) {
    const subtitleText = document.getElementById("subtitleText");
    if (subtitleText) {
      const text =
        final +
        (interim ? ` <span style="opacity: 0.6">${interim}</span>` : "");
      subtitleText.innerHTML = text || "Listening...";
    }
  }

  clearTranscriptionDisplay() {
    const subtitleText = document.getElementById("subtitleText");
    if (subtitleText) {
      subtitleText.textContent = "Listening...";
    }
  }

  updateAvatarState(state) {
    const avatar = document.getElementById("aiAvatar");
    if (avatar) {
      avatar.className = `ai-avatar ${state}`;
    }
  }

  showAudioLoading() {
    // Could add loading indicator for audio processing
    this.updateAvatarState("processing");
  }

  hideAudioLoading() {
    this.updateAvatarState("idle");
  }

  showError(message) {
    if (window.app) {
      window.app.showError(message);
    } else {
      console.error(message);
    }
  }

  // Cleanup method
  cleanup() {
    if (this.recognition) {
      this.recognition.stop();
    }

    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
  }
}

// Initialize audio manager
document.addEventListener("DOMContentLoaded", () => {
  window.audioManager = new AudioManager();

  // Override app's TTS method
  if (window.app) {
    window.app.playTTS = function (text, language = "en") {
      window.audioManager.playTTS(text, language);
    };

    window.app.toggleVoiceInput = function () {
      window.audioManager.toggleRecording();
    };
  }
});

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  if (window.audioManager) {
    window.audioManager.cleanup();
  }
});

// Add CSS for recording state
const style = document.createElement("style");
style.textContent = `
    .btn-icon.recording {
        background-color: #ef4444 !important;
        color: white !important;
        animation: pulse 2s infinite;
    }
    
    .ai-avatar.speaking .avatar-image {
        animation: bounce 0.6s ease-in-out infinite alternate;
    }
    
    .ai-avatar.processing .avatar-image {
        animation: spin 2s linear infinite;
    }
    
    @keyframes bounce {
        from { transform: scale(1); }
        to { transform: scale(1.1); }
    }
`;
document.head.appendChild(style);
