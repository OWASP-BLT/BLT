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
        this.startGithubStatusPolling();
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
      "sync-github-btn",
    ];
    ids.forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) {
        btn.disabled = true;
        btn.classList.add("opacity-50");
        btn.classList.add("pointer-events-none");
      }
    });
    // Ensure polling is stopped
    this.stopGithubStatusPolling();
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
      .getElementById("sync-github-btn")
      ?.addEventListener("click", () => this.syncGithubData());
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
            cacheHitRatioEl.textContent = isNaN(hitRatio) ? "N/A" : `${hitRatio.toFixed(2)}%`;
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
   * Sync GitHub data
   */
  syncGithubData() {
    if (!confirm("Sync GitHub data? This may take a few minutes.")) {
      return;
    }

    this.showStatus("Syncing GitHub data...", "info");
    this.makeRequest(
      "POST",
      `${this.apiBaseUrl}/sync-github/`,
      { confirm: true },
      (data) => {
        if (data.success) {
          this.showStatus(
            data.message ? data.message : "GitHub data synced successfully!",
            "success"
          );
        } else {
          this.showStatus(
            `Error: ${data.error || "Failed to sync GitHub data"}`,
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
      if (content.classList.contains("hidden")) {
        this.stopGithubStatusPolling();
      } else {
        this.startGithubStatusPolling();
      }
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
    messageDiv.className = `text-${colorClass} mb-2`;
    messageDiv.textContent = `[${timestamp}] ${message}`;
    statusContent.appendChild(messageDiv);
    statusContent.scrollTop = statusContent.scrollHeight;
  },

  /**
   * Get status color class
   */
  getStatusColor(type) {
    const colors = {
      success: "green-400",
      error: "red-400",
      info: "blue-400",
      warning: "yellow-400",
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
   * Start polling the debug status endpoint for GitHub sync state
   */
  startGithubStatusPolling(intervalMs = 5000) {
    // allow optional override from DOM (data attribute on #dev-panel)
    const panel = document.getElementById("dev-panel");
    const configured = panel?.dataset?.pollIntervalMs;
    this._defaultPollInterval = typeof configured !== "undefined" ? parseInt(configured, 10) || intervalMs : intervalMs;

    // avoid starting multiple timers
    if (this.githubStatusTimer) return;

    // track the currently used interval so we can adapt when state changes
    this._currentPollInterval = this._defaultPollInterval;

    // schedule first poll asynchronously to avoid blocking initialization
    setTimeout(() => this.pollGithubSyncStatus(), 0);
    this.githubStatusTimer = setInterval(() => this.pollGithubSyncStatus(), this._currentPollInterval);
  },

  /**
   * Stop polling the debug status endpoint
   */
  stopGithubStatusPolling() {
    if (this.githubStatusTimer) {
      clearInterval(this.githubStatusTimer);
      this.githubStatusTimer = null;
      this._currentPollInterval = null;
    }
  },

  /**
   * Poll the /api/debug/status/ endpoint and update a persistent badge in the dev panel
   */
  pollGithubSyncStatus() {
    this.makeRequest(
      "GET",
      `${this.apiBaseUrl}/status/`,
      null,
      (data) => {
        try {
          if (!data || !data.data) {
            this.updateGithubStatusBadge({ running: false, started_at: null, last_finished_at: null, last_error: null });
            return;
          }
          const sync = data.data.github_sync || {};
          this.updateGithubStatusBadge(sync);
        } catch (e) {
          // if any parsing error occurs, show unavailable
          this.updateGithubStatusBadge({ running: false, started_at: null, last_finished_at: null, last_error: "parse error" });
        }
      },
      (error) => {
        // network or auth error: show unavailable status
        this.updateGithubStatusBadge({ running: false, started_at: null, last_finished_at: null, last_error: error });
      }
    );
  },

  /**
   * Format ISO timestamp (or null) to a compact human-readable string
   */
  formatTimestamp(iso) {
    if (!iso) return "N/A";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString();
    } catch (e) {
      return iso;
    }
  },

  /**
   * Create or update a persistent GitHub sync status badge inside the dev panel
   */
  updateGithubStatusBadge(sync) {
    const panel = document.getElementById("dev-panel");
    if (!panel) return;

    let badge = document.getElementById("github-sync-badge");
    const isRunning = Boolean(sync.running);

    if (!badge) {
      badge = document.createElement("div");
      badge.id = "github-sync-badge";
      // Use Tailwind utility classes instead of long inline styles
      // these classes assume Tailwind is available in the project
      badge.className = "inline-block ml-3 px-2 py-1 rounded text-xs font-mono";
      // Prefer a dedicated header container with a stable ID to avoid brittle DOM queries
      let header = document.getElementById("dev-panel-header");
      if (!header) {
        // Fallback to legacy selector used previously
        header = panel.querySelector(".flex.items-center") || panel.firstElementChild;
      }
      if (header && header.parentNode) {
        header.parentNode.insertBefore(badge, header.nextSibling);
      } else {
        panel.insertBefore(badge, panel.firstChild);
      }
    }

    // Reset color classes
    badge.classList.remove(
      "bg-amber-400",
      "bg-red-500",
      "bg-emerald-500",
      "text-black",
      "text-white"
    );

    // Adaptive polling: speed up when running, slow down when idle
    try {
      const desiredInterval = isRunning ? 1000 : (this._defaultPollInterval || 5000);
      if (this._currentPollInterval !== desiredInterval) {
        // Restart poll timer with new interval
        if (this.githubStatusTimer) {
          clearInterval(this.githubStatusTimer);
        }
        this._currentPollInterval = desiredInterval;
        this.githubStatusTimer = setInterval(() => this.pollGithubSyncStatus(), this._currentPollInterval);
      }
    } catch (e) {
      // ignore timer adjustment errors
    }

    if (isRunning) {
      badge.textContent = `Sync: RUNNING (started: ${this.formatTimestamp(sync.started_at)})`;
      badge.classList.add("bg-amber-400", "text-black");
      badge.title = "";
    } else if (sync.last_error) {
      // Show a shortened error in the badge text while keeping full details in the tooltip
      const errorMsg = String(sync.last_error);
      // Shorten to first sentence or first 50 characters
      let shortError = errorMsg.split(/[.!?]\s/)[0] || errorMsg;
      if (shortError.length > 50) {
        shortError = shortError.slice(0, 47) + "...";
      }
      badge.textContent = `Sync: ERROR (${shortError})`;
      badge.classList.add("bg-red-500", "text-white");
      badge.title = errorMsg;
    } else {
      badge.textContent = `Sync: idle (last: ${this.formatTimestamp(sync.last_finished_at)})`;
      badge.classList.add("bg-emerald-500", "text-white");
      badge.title = "";
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
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => DebugPanel.init());
} else {
  DebugPanel.init();
}