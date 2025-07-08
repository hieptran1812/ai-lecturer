// UI Manager for handling user interface interactions and animations
class UIManager {
  constructor() {
    this.currentTheme = "light";
    this.setupTheme();
    this.setupAnimations();
    this.setupNotifications();
  }

  setupTheme() {
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem("ai-teacher-theme") || "light";
    this.setTheme(savedTheme);
  }

  setTheme(theme) {
    this.currentTheme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ai-teacher-theme", theme);
  }

  toggleTheme() {
    const newTheme = this.currentTheme === "light" ? "dark" : "light";
    this.setTheme(newTheme);
  }

  setupAnimations() {
    // Setup intersection observer for scroll animations
    this.setupScrollAnimations();

    // Setup hover effects
    this.setupHoverEffects();
  }

  setupScrollAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate-in");
        }
      });
    }, observerOptions);

    // Observe elements that should animate on scroll
    document
      .querySelectorAll(".feature-card, .vocabulary-item, .grammar-item")
      .forEach((el) => {
        observer.observe(el);
      });
  }

  setupHoverEffects() {
    // Add hover effects to interactive elements
    document
      .querySelectorAll(".btn-primary, .btn-secondary, .quick-action-btn")
      .forEach((btn) => {
        btn.addEventListener("mouseenter", this.addHoverEffect);
        btn.addEventListener("mouseleave", this.removeHoverEffect);
      });
  }

  addHoverEffect(event) {
    event.target.style.transform = "translateY(-2px)";
    event.target.style.boxShadow = "0 4px 12px rgba(0,0,0,0.15)";
  }

  removeHoverEffect(event) {
    event.target.style.transform = "";
    event.target.style.boxShadow = "";
  }

  setupNotifications() {
    // Create notification container
    this.createNotificationContainer();
  }

  createNotificationContainer() {
    const container = document.createElement("div");
    container.id = "notification-container";
    container.className = "notification-container";
    document.body.appendChild(container);
  }

  // Notification Methods
  showNotification(message, type = "info", duration = 5000) {
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;

    const icon = this.getNotificationIcon(type);
    notification.innerHTML = `
            <div class="notification-content">
                <i class="${icon}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;

    const container = document.getElementById("notification-container");
    container.appendChild(notification);

    // Add click to close
    notification
      .querySelector(".notification-close")
      .addEventListener("click", () => {
        this.hideNotification(notification);
      });

    // Auto hide after duration
    setTimeout(() => {
      this.hideNotification(notification);
    }, duration);

    // Animate in
    setTimeout(() => {
      notification.classList.add("show");
    }, 100);

    return notification;
  }

  hideNotification(notification) {
    notification.classList.remove("show");
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }

  getNotificationIcon(type) {
    const icons = {
      success: "fas fa-check-circle",
      error: "fas fa-exclamation-circle",
      warning: "fas fa-exclamation-triangle",
      info: "fas fa-info-circle",
    };
    return icons[type] || icons.info;
  }

  // Modal Methods
  showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";

      // Animate in
      setTimeout(() => {
        modal.classList.add("show");
      }, 100);
    }
  }

  hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("show");
      document.body.style.overflow = "";

      setTimeout(() => {
        modal.style.display = "none";
      }, 300);
    }
  }

  // Loading Methods
  showGlobalLoading(message = "Loading...") {
    const overlay = document.getElementById("loadingOverlay");
    const text = document.getElementById("loadingText");

    if (overlay && text) {
      text.textContent = message;
      overlay.style.display = "flex";

      setTimeout(() => {
        overlay.classList.add("show");
      }, 100);
    }
  }

  hideGlobalLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
      overlay.classList.remove("show");

      setTimeout(() => {
        overlay.style.display = "none";
      }, 300);
    }
  }

  // Progress Methods
  showProgress(percentage, message = "") {
    let progressBar = document.getElementById("progress-bar");

    if (!progressBar) {
      progressBar = this.createProgressBar();
    }

    const fill = progressBar.querySelector(".progress-fill");
    const text = progressBar.querySelector(".progress-text");

    fill.style.width = `${percentage}%`;
    text.textContent = message;

    progressBar.style.display = "block";
  }

  hideProgress() {
    const progressBar = document.getElementById("progress-bar");
    if (progressBar) {
      progressBar.style.display = "none";
    }
  }

  createProgressBar() {
    const progressBar = document.createElement("div");
    progressBar.id = "progress-bar";
    progressBar.className = "progress-bar";
    progressBar.innerHTML = `
            <div class="progress-track">
                <div class="progress-fill"></div>
            </div>
            <div class="progress-text"></div>
        `;

    document.body.appendChild(progressBar);
    return progressBar;
  }

  // Animation Methods
  animateTyping(element, text, speed = 50) {
    return new Promise((resolve) => {
      element.textContent = "";
      let i = 0;

      const typeInterval = setInterval(() => {
        element.textContent += text.charAt(i);
        i++;

        if (i > text.length) {
          clearInterval(typeInterval);
          resolve();
        }
      }, speed);
    });
  }

  animateCounter(element, start, end, duration = 1000) {
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const current = Math.floor(start + (end - start) * progress);
      element.textContent = current;

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }

  // Utility Methods
  smoothScrollTo(element, duration = 500) {
    const start = window.pageYOffset;
    const target = element.offsetTop;
    const distance = target - start;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const ease = this.easeInOutCubic(progress);
      window.scrollTo(0, start + distance * ease);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }

  easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
  }

  // Responsive Methods
  isMobile() {
    return window.innerWidth <= 768;
  }

  isTablet() {
    return window.innerWidth > 768 && window.innerWidth <= 1024;
  }

  isDesktop() {
    return window.innerWidth > 1024;
  }

  // Accessibility Methods
  announceToScreenReader(message) {
    const announcement = document.createElement("div");
    announcement.setAttribute("aria-live", "polite");
    announcement.setAttribute("aria-atomic", "true");
    announcement.className = "sr-only";
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  // Focus Management
  trapFocus(element) {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    element.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        if (e.shiftKey) {
          if (document.activeElement === firstFocusable) {
            lastFocusable.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastFocusable) {
            firstFocusable.focus();
            e.preventDefault();
          }
        }
      }
    });

    firstFocusable.focus();
  }
}

// Initialize UI manager
document.addEventListener("DOMContentLoaded", () => {
  window.uiManager = new UIManager();

  // Override app methods to use UI manager
  if (window.app) {
    window.app.showError = function (message) {
      window.uiManager.showNotification(message, "error");
    };

    window.app.showLoading = function (message) {
      window.uiManager.showGlobalLoading(message);
    };

    window.app.hideLoading = function () {
      window.uiManager.hideGlobalLoading();
    };

    window.app.showSuccess = function (message) {
      window.uiManager.showNotification(message, "success");
    };
  }
});

// Add CSS for notifications and animations
const uiStyles = document.createElement("style");
uiStyles.textContent = `
    .notification-container {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        pointer-events: none;
    }
    
    .notification {
        background: white;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        transform: translateX(100%);
        opacity: 0;
        transition: all 0.3s ease;
        pointer-events: auto;
    }
    
    .notification.show {
        transform: translateX(0);
        opacity: 1;
    }
    
    .notification-success { border-left-color: #10b981; }
    .notification-error { border-left-color: #ef4444; }
    .notification-warning { border-left-color: #f59e0b; }
    .notification-info { border-left-color: #3b82f6; }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        padding: 4px;
    }
    
    .progress-bar {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        min-width: 300px;
        z-index: 10000;
        display: none;
    }
    
    .progress-track {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 8px;
    }
    
    .progress-fill {
        height: 100%;
        background: #3b82f6;
        border-radius: 4px;
        transition: width 0.3s ease;
        width: 0%;
    }
    
    .progress-text {
        text-align: center;
        font-size: 14px;
        color: #64748b;
    }
    
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    
    .animate-in {
        animation: slideInUp 0.6s ease-out;
    }
    
    @keyframes slideInUp {
        from {
            transform: translateY(30px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .modal.show {
        animation: fadeIn 0.3s ease-out;
    }
    
    .loading-overlay.show {
        animation: fadeIn 0.3s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
`;
document.head.appendChild(uiStyles);
