/**
 * Debug Panel JavaScript
 * Handles interactions with the debug panel API endpoints
 * Only runs in DEBUG mode on local development
 */

const DebugPanel = {
  apiBaseUrl: "/api/debug",
  statusElement: "#dev-status-content",
  statusContainer: "#dev-status-messages",

  /**
   * Initialize debug panel event listeners
   */
  init() {
    if (!this.isDebugMode()) {
      return;
    }

    this.setupEventListeners();

    // Verify auth first; only load stats and start polling if auth succeeds
    this.verifyAuth().then((ok) => {
      if (ok) {
        this.loadInitialStats();
      } else {
        // Disable interactive controls when not authenticated
        this.disablePanel();
      }
    });
  },

  /**
   * Verify authentication status
   */
  verifyAuth() {
    return new Promise((resolve) => {
      this.makeRequest(
        "GET",
        `${this.apiBaseUrl}/system-stats/`,
        null,
        () => {
          this.showStatus("✓ Authentication verified", "success");
          this.authVerified = true;
          resolve(true);
        },
        (error) => {
          this.showStatus(
            `✗ Authentication failed: ${error}. Debug panel disabled.`,
            "error"
          );
          this.authVerified = false;
          resolve(false);
        }
      );
    });
  },

  disablePanel() {
    // Disable buttons and stop any polling; keep a visible status message
    const ids = [
      "populate-data-btn",
      "clear-cache-btn",
      "check-performance-btn",
      "management-commands-btn",
    ];
    ids.forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.disabled = true;
        btn.classList.add("opacity-50");
        btn.classList.add("pointer-events-none");
      }
    });
  },

  /**
   * Check if debug mode is enabled
   */
  isDebugMode() {
    return document.getElementById("dev-panel") !== null;
  },

  /**
   * Setup all event listeners for debug panel buttons
   */
  setupEventListeners() {
    document
      .getElementById("populate-data-btn")
      ?.addEventListener("click", () => this.populateTestData());
    document
      .getElementById("clear-cache-btn")
      ?.addEventListener("click", () => this.clearCache());
    document
      .getElementById("check-performance-btn")
      ?.addEventListener("click", () => this.checkPerformance());
    document
      .getElementById("management-commands-btn")
      ?.addEventListener("click", () => this.goToManagementCommands());
    document
      .getElementById("toggle-dev-panel")
      ?.addEventListener("click", () => this.togglePanel());
  },

  /**
   * Load initial statistics
   */
  loadInitialStats() {
    this.updateSystemStats();
    this.updateCacheStats();
  },

  /**
   * Update system statistics
   */
  updateSystemStats() {
    this.makeRequest(
      "GET",
      `${this.apiBaseUrl}/system-stats/`,
      null,
      (data) => {
        if (data.success && data.data) {
          const stats = data.data;

          const memoryEl = document.querySelector('[data-stat="memory"]');
          if (memoryEl && stats.memory) {
            const memValue =
              typeof stats.memory === "object"
                ? stats.memory.used || stats.memory
                : stats.memory;
            memoryEl.textContent = memValue;
          }

          const cpuEl = document.querySelector('[data-stat="cpu"]');
          if (cpuEl && stats.cpu && stats.cpu.percent !== undefined) {
            cpuEl.textContent = stats.cpu.percent;
          }

          const pythonEl = document.querySelector(
            '[data-stat="python_version"]'
          );
          if (pythonEl && stats.python_version) {
            pythonEl.textContent = stats.python_version.split(" ")[0];
          }

          const djangoEl = document.querySelector(
            '[data-stat="django_version"]'
          );
          if (djangoEl && stats.django_version) {
            djangoEl.textContent = stats.django_version.split(" ")[0];
          }

          const dbConnectionsEl = document.querySelector(
            '[data-stat="db_connections"]'
          );
          if (dbConnectionsEl && stats.database?.connections !== undefined) {
            dbConnectionsEl.textContent = stats.database.connections;
          }

          this.updateDatabaseStatsFromSystemStats(stats);
        }
      }
    );
  },

  /**
   * Update database statistics from system stats response
   */
  updateDatabaseStatsFromSystemStats(stats) {
    const elements = {
      "user-count": stats.database?.user_count,
      "issue-count": stats.database?.issue_count,
      "org-count": stats.database?.org_count,
      "domain-count": stats.database?.domain_count,
      "repo-count": stats.database?.repo_count,
    };

    Object.entries(elements).forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (el && value !== undefined) {
        el.textContent = value;
      }
    });
  },

  /**
   * Update cache statistics
   */
  updateCacheStats() {
    this.makeRequest(
      "GET",
      `${this.apiBaseUrl}/cache-info/`,
      null,
      (data) => {
        if (data.success) {
          const cacheInfo = data.data;
          const cacheBackendEl = document.getElementById("cache-backend");
          const cacheKeysEl = document.getElementById("cache-keys");
          const cacheHitRatioEl = document.getElementById("cache-hit-ratio");

          if (cacheBackendEl) {
            cacheBackendEl.textContent = cacheInfo.backend || "Unknown";
          }
          if (cacheKeysEl) {
            cacheKeysEl.textContent = cacheInfo.keys_count || "0";
          }
          if (cacheHitRatioEl) {
            const hitRatio = parseFloat(cacheInfo.hit_ratio);
            cacheHitRatioEl.textContent = Number.isNaN(hitRatio) ? "N/A" : `${hitRatio.toFixed(2)}%`;
          }
        }
      }
    );
  },

  /**
   * Populate test data
   */
  populateTestData() {
    if (
      !confirm(
        "Are you sure you want to populate test data? This may take a while."
      )
    ) {
      return;
    }

    this.showStatus("Populating test data...", "info");
    this.makeRequest(
      "POST",
      `${this.apiBaseUrl}/populate-data/`,
      { confirm: true },
      (data) => {
        if (data.success) {
          this.showStatus("Test data populated successfully!", "success");
          setTimeout(() => this.loadInitialStats(), 1000);
        } else {
          this.showStatus(`Error: ${data.error || "Unknown error"}`, "error");
        }
      },
      (error) => {
        this.showStatus(`Error: ${error}`, "error");
      }
    );
  },

  /**
   * Clear cache
   */
  clearCache() {
    if (!confirm("Are you sure you want to clear all cache?")) {
      return;
    }

    this.showStatus("Clearing cache...", "info");
    this.makeRequest(
      "POST",
      `${this.apiBaseUrl}/clear-cache/`,
      null,
      (data) => {
        if (data.success) {
          this.showStatus("Cache cleared successfully!", "success");
          this.updateCacheStats();
        } else {
          this.showStatus(`Error: ${data.error || "Unknown error"}`, "error");
        }
      },
      (error) => {
        this.showStatus(`Error: ${error}`, "error");
      }
    );
  },

  /**
   * Check performance metrics
   */
  checkPerformance() {
    this.showStatus("Checking performance...", "info");
    this.makeRequest(
      "GET",
      `${this.apiBaseUrl}/system-stats/`,
      null,
      (data) => {
        if (data.success) {
          const stats = data.data;
          const performanceReport = `
Performance Report (${new Date().toLocaleTimeString()}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Python: ${stats.python_version || "N/A"}
Django: ${stats.django_version || "N/A"}
Database: ${stats.database?.name || "N/A"} (${stats.database?.engine || "N/A"})
Memory: ${
            typeof stats.memory === "object"
              ? stats.memory.used || stats.memory
              : stats.memory || "N/A"
          }
Disk: ${stats.disk?.used || "N/A"} / ${stats.disk?.total || "N/A"}
CPU: ${stats.cpu?.percent || "N/A"}
DB Connections: ${stats.database?.connections || "N/A"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
          this.showStatus(performanceReport, "success");
        } else {
          this.showStatus(
            `Error: ${data.error || "Failed to fetch performance data"}`,
            "error"
          );
        }
      },
      (error) => {
        this.showStatus(`Error: ${error}`, "error");
      }
    );
  },

  /**
   * Toggle debug panel visibility
   */
  togglePanel() {
    const content = document.getElementById("dev-panel-content");
    const button = document.getElementById("toggle-dev-panel");

    if (content) {
      content.classList.toggle("hidden");
      const icon = button?.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-chevron-up");
        icon.classList.toggle("fa-chevron-down");
      }
    }
  },

  /**
   * Show status message
   */
  showStatus(message, type = "info") {
    const statusContainer = document.querySelector(this.statusContainer);
    const statusContent = document.querySelector(this.statusElement);

    if (!statusContainer || !statusContent) {
      return;
    }

    statusContainer.classList.remove("hidden");
    const timestamp = new Date().toLocaleTimeString();
    const colorClass = this.getStatusColor(type);
    const messageDiv = document.createElement("div");
    // Use explicit Tailwind classes to avoid purge issues
    messageDiv.className = `${colorClass} mb-2 whitespace-pre-wrap font-mono`;
    messageDiv.textContent = `[${timestamp}] ${message}`;
    statusContent.appendChild(messageDiv);
    statusContent.scrollTop = statusContent.scrollHeight;
  },

  /**
   * Get status color class
   */
  getStatusColor(type) {
    // Map to explicit Tailwind classes so the JIT scanner picks them up
    const colors = {
      success: "text-green-400",
      error: "text-red-400",
      info: "text-blue-400",
      warning: "text-yellow-400",
    };
    return colors[type] || colors.info;
  },

  /**
   * Get API token for TokenAuthentication
   */
  getApiToken() {
    const panel = document.getElementById("dev-panel");
    if (!panel) return null;
    return panel.dataset.apiToken || null;
  },

  /**
   * Format ISO timestamp (or null) to a compact human-readable string
   */
  formatTimestamp(iso) {
    if (!iso) return "N/A";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "Invalid date";
      return d.toLocaleString();
    } catch (e) {
      return "Invalid date";
    }
  },

  /**
   * Make API request with proper session authentication
   */
  makeRequest(method, url, data, onSuccess, onError) {
    const csrfToken = this.getCookie("csrftoken");
    const apiToken = this.getApiToken();

    const options = {
      method: method,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "include",
    };

    if (csrfToken) {
      options.headers["X-CSRFToken"] = csrfToken;
    }
    if (apiToken) {
      options.headers["Authorization"] = `Token ${apiToken}`;
    }

    if (data && method !== "GET") {
      options.body = JSON.stringify(data);
    }

    fetch(url, options)
      .then((response) => {
        const contentType = response.headers.get("content-type");

        if (!response.ok) {
          let errorMessage = `HTTP Error ${response.status}`;

          if (response.status === 401) {
            errorMessage =
              "401 Unauthorized. Please ensure you're logged in.";
            const error = new Error(errorMessage);
            error.status = response.status;
            throw error;
          } else if (response.status === 403) {
            errorMessage =
              "403 Forbidden. Debug endpoints may be restricted to local development.";
            const error = new Error(errorMessage);
            error.status = response.status;
            throw error;
          } else if (response.status === 404) {
            errorMessage = "404 Not Found. Debug API endpoint not found.";
            const error = new Error(errorMessage);
            error.status = response.status;
            throw error;
          }

          const error = new Error(errorMessage);
          error.status = response.status;
          throw error;
        }

        if (!contentType || !contentType.includes("application/json")) {
          throw new Error(
            "Invalid response format. Expected JSON but received " +
              (contentType || "unknown")
          );
        }

        return response.json();
      })
      .then((responseData) => {
        if (onSuccess) {
          onSuccess(responseData);
        }
      })
      .catch((error) => {
        let errorMsg = "Request failed";

        if (error instanceof TypeError) {
          errorMsg = `Network error: ${error.message}`;
        } else if (error.message) {
          errorMsg = error.message;
        }

        if (onError) {
          onError(errorMsg);
        } else {
          this.showStatus(`Request failed: ${errorMsg}`, "error");
        }
      });
  },

  /**
   * Get CSRF token from cookies
   */
  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  },

  /**
   * Go To Management Commands Page
   */
  goToManagementCommands() {
    window.location.href = window.location.origin + "/status/commands/";
  },
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => DebugPanel.init());
} else {
  DebugPanel.init();
}