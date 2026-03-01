// Function to copy text to clipboard
function copyToClipboard(elementId) {
  const element = document.getElementById(elementId);
  if (!element) return;

  // Select the text
  element.select();
  element.setSelectionRange(0, 99999); // For mobile devices

  // Copy the text
  navigator.clipboard
    .writeText(element.value)
    .then(() => {
      // Get the button
      const button = element.nextElementSibling;
      const originalText = button.textContent;

      // Change button style to show success
      button.textContent = "Copied!";
      button.classList.remove("bg-red-500", "hover:bg-red-600");
      button.classList.add("bg-green-500", "hover:bg-green-600");

      // Reset button after 2 seconds
      setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove("bg-green-500", "hover:bg-green-600");
        button.classList.add("bg-red-500", "hover:bg-red-600");
      }, 2000);
    })
    .catch(() => {
      // Error silently handled or use a custom tracker if available
    });
}

function getCookie(name) {
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
}

// Function to refresh a section of the repository detail page
async function refreshSection(button, section) {
  // Check if already spinning
  if (button.querySelector(".animate-spin")) {
    return;
  }

  // Get the SVG icon
  const svgIcon = button.querySelector("svg");

  // Hide the original icon
  if (svgIcon) {
    svgIcon.classList.add("opacity-0");
  }

  // Create spinner with Tailwind classes
  const spinner = document.createElement("div");
  spinner.className = "absolute inset-0 flex items-center justify-center";
  spinner.innerHTML = `<div class="w-5 h-5 border-2 border-[#e74c3c] border-t-transparent rounded-full animate-spin"></div>`;
  button.appendChild(spinner);

  // Create message container if it doesn't exist
  let container = button.closest(".refresh-container");
  if (!container) {
    container = button.parentElement || document.body;
  }
  let messageContainer = container.querySelector(".refresh-message");
  if (!messageContainer) {
    messageContainer = document.createElement("div");
    messageContainer.className =
      "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10";
    container.appendChild(messageContainer);
  }

  try {
    // Create a FormData object
    const formData = new FormData();

    // Ensure section is a string and properly formatted
    const sectionValue = String(section).trim();
    formData.append("section", sectionValue);

    // Try to get CSRF token from cookie first, then fallback to meta tag
    let csrfToken = getCookie("csrftoken");

    // If not found in cookie, try to get from meta tag
    if (!csrfToken) {
      const csrfMetaTag = document.querySelector('meta[name="csrf-token"]');
      if (csrfMetaTag) {
        csrfToken = csrfMetaTag.getAttribute("content");
      }
    }

    if (!csrfToken) {
      // CSRF token not found. Cookies might be disabled or meta tag is missing.
    }

    const response = await fetch(window.location.href, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken || "",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: formData,
    });

    // Check if response is OK before trying to parse JSON
    if (!response.ok) {
      throw new Error(`Server responded with status: ${response.status}`);
    }

    // Try to parse the response as JSON
    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      throw new Error("Failed to parse server response");
    }

    if (sectionValue === "ai_summary") {
      // Update AI summary content
      const summaryContainer = document.getElementById("ai-summary-content");
      if (summaryContainer && data && data.data && data.data.ai_summary) {
        // Safely update the content using DOMPurify
        if (typeof DOMPurify !== "undefined") {
          summaryContainer.innerHTML = DOMPurify.sanitize(data.data.ai_summary);
        } else {
          summaryContainer.textContent = data.data.ai_summary;
        }
      } else if (summaryContainer) {
        summaryContainer.innerHTML =
          '<p class="text-gray-600 italic">AI summary unavailable for this repo.</p>';
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent =
        data.message || "AI summary regenerated successfully";
    } else if (sectionValue === "basic") {
      // Update stats with new data
      const safeLastUpdated = data.data.last_updated
        ? `Updated ${data.data.last_updated.replace("\u00a0", " ")}`
        : "Updated N/A";
      const updates = {
        stars: data.data.stars,
        forks: data.data.forks,
        watchers: data.data.watchers,
        network: data.data.network_count,
        subscribers: data.data.subscribers_count,
        "last-updated": safeLastUpdated,
      };

      // Update each stat if the element exists
      for (const [key, value] of Object.entries(updates)) {
        const element = document.querySelector(`[data-stat="${key}"]`);
        if (element) {
          element.textContent = value;
        }
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent = data.message;
    } else if (sectionValue === "metrics") {
      // Update metrics with new data
      const updates = {
        open_issues: data.data.open_issues,
        closed_issues: data.data.closed_issues,
        total_issues: data.data.total_issues,
        open_pull_requests: data.data.open_pull_requests,
        commit_count: data.data.commit_count,
        last_commit_date: data.data.last_commit_date,
      };

      // Update each stat if the element exists
      for (const [key, value] of Object.entries(updates)) {
        const element = document.querySelector(`[data-stat="${key}"]`);
        if (element && value !== null && value !== undefined) {
          element.textContent = value.toLocaleString();
        } else if (element) {
          element.textContent = "";
        }
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent = data.message;
    } else if (sectionValue === "technical") {
      // Update technical details with new data
      const sizeMb = Number.isFinite(data.data.size)
        ? `${(data.data.size / 1024).toFixed(2)} MB`
        : "N/A";
      const technicalElements = {
        primary_language: data.data.primary_language,
        size: sizeMb,
        license: data.data.license,
        release_name: data.data.release_name,
        release_date: data.data.release_date,
        last_commit_date: data.data.last_commit_date,
      };

      // Update each technical element
      for (const [key, value] of Object.entries(technicalElements)) {
        const element = document.querySelector(`[data-tech="${key}"]`);
        if (element) {
          element.textContent = value;
        }
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent = data.message;
    } else if (sectionValue === "community") {
      const contributorsContainer =
        document.querySelector(".contributors-grid");
      if (!contributorsContainer) return;

      const communityData = data.data;

      // Update total count
      const totalCountEl = document.querySelector(
        '[data-community="total-count"]',
      );
      if (totalCountEl) {
        const total = Number.isFinite(communityData.total_contributors)
          ? communityData.total_contributors.toLocaleString()
          : "0";
        totalCountEl.textContent = `${total} total contributors`;
      }

      // Update contributors grid
      let contributorsHtml = "";
      communityData.contributors.forEach((contributor) => {
        contributorsHtml += `
                    <div class="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group">
                        <img src="${contributor.avatar_url}" width="30" height="30" alt="${contributor.name}" class="w-12 h-12 rounded-full border-2 border-white shadow-md group-hover:scale-110 transition-transform">
                        <div class="flex-grow">
                            <div class="font-medium text-gray-900">
                                ${contributor.name}
                                ${contributor.verified ? '<span class="ml-1 text-green-500" title="Verified Contributor">✓</span>' : ""}
                            </div>
                            <div class="text-sm text-gray-500">${(contributor.contributions ?? 0).toLocaleString()} commits</div>
                        </div>
                        <a href="${contributor.github_url}" target="_blank" class="p-2 text-gray-400 hover:text-gray-600">
                            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                            </svg>
                        </a>
                    </div>
                `;
      });

      if (typeof DOMPurify !== "undefined") {
        contributorsContainer.innerHTML = DOMPurify.sanitize(contributorsHtml);
      } else {
        contributorsContainer.textContent =
          "Failed to load contributors: Sanitization library missing.";
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent = data.message;
    } else if (sectionValue === "contributor_stats") {
      const statsTableBody = document.querySelector(
        ".contributor-stats-table tbody",
      );
      if (!statsTableBody) return;

      // Clear existing table content
      statsTableBody.innerHTML = "";

      // Populate new data
      if (data.data.stats && data.data.stats.length > 0) {
        data.data.stats.forEach((stat) => {
          const row = document.createElement("tr");
          row.className = "hover:bg-gray-50 transition-colors";

          const rowHtml = `
                        <td class="px-4 py-4 whitespace-nowrap">
                            <div class="flex items-center">
                                <img class="h-8 w-8 rounded-full" width="20" height="20" src="${stat.contributor.avatar_url}" alt="${stat.contributor.name}">
                                <div class="ml-3">
                                    <div class="text-sm font-medium text-gray-900">${stat.contributor.name}</div>
                                    <div class="text-sm text-gray-500">@${stat.contributor.github_id}</div>
                                </div>
                            </div>
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center text-emerald-600 font-medium">
                            ${stat.commits ? stat.commits.toLocaleString() : "0"}
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center text-blue-600 font-medium">
                            ${stat.issues_opened ? stat.issues_opened.toLocaleString() : "0"}
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center text-purple-600 font-medium">
                            ${stat.issues_closed ? stat.issues_closed.toLocaleString() : "0"}
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center text-orange-600 font-medium">
                            ${stat.pull_requests ? stat.pull_requests.toLocaleString() : "0"}
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center text-cyan-600 font-medium">
                            ${stat.comments ? stat.comments.toLocaleString() : "0"}
                        </td>
                        <td class="px-4 py-4 whitespace-nowrap text-center">
                            <div class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${stat.impact_level?.class ?? ""}">
                                ${stat.impact_level?.text ?? "N/A"}
                            </div>
                        </td>
                    `;

          if (typeof DOMPurify !== "undefined") {
            row.innerHTML = DOMPurify.sanitize(rowHtml);
          } else {
            // Minimal fallback if DOMPurify is missing (though we added it to the template)
            row.textContent = "Error: Sanitization required.";
          }
          statsTableBody.appendChild(row);
        });
      } else {
        statsTableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                            No contributor statistics available for this period
                        </td>
                    </tr>
                `;
      }

      // Show success message
      messageContainer.className =
        "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600";
      messageContainer.textContent =
        data.message || "Contributor statistics refreshed successfully";
    }
  } catch (error) {
    messageContainer.className =
      "absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-red-600";
    messageContainer.textContent = error.message;
  } finally {
    // Remove spinner and restore icon
    const spinnerElement = button.querySelector(".animate-spin");
    if (spinnerElement && spinnerElement.parentNode) {
      spinnerElement.parentNode.remove();
    }

    // Show the original icon
    const svgIcon = button.querySelector("svg");
    if (svgIcon) {
      svgIcon.classList.remove("opacity-0");
    }

    // Remove message after 5 seconds
    setTimeout(() => {
      if (messageContainer && messageContainer.parentElement) {
        messageContainer.remove();
      }
    }, 5000);
  }
}

// Function to update contributor stats
function updateContributorStats(timePeriod, page = 1) {
  // Show loading state
  const tableContainer = document.querySelector(".contributor-stats-table");
  if (!tableContainer) return; // Guard clause

  tableContainer.classList.add("opacity-50");

  // Prepare form data
  const formData = new FormData();
  formData.append("time_period", timePeriod);
  formData.append("page", page);

  // Get the current URL
  const currentUrl = new URL(window.location.href);

  // Update query parameters
  currentUrl.searchParams.set("time_period", timePeriod);
  currentUrl.searchParams.set("page", page);

  // Make AJAX request
  fetch(window.location.pathname, {
    method: "POST",
    body: formData,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken":
        getCookie("csrftoken") ||
        document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content") ||
        "",
    },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.text();
    })
    .then((html) => {
      if (typeof DOMPurify !== "undefined") {
        tableContainer.innerHTML = DOMPurify.sanitize(html);
      } else {
        tableContainer.textContent =
          "Unable to safely load contributor statistics. Please refresh.";
        return;
      }
      // Update URL without page reload
      window.history.pushState({}, "", currentUrl.toString());

      // Re-attach event listeners to new pagination buttons
      attachPaginationListeners();
    })
    .catch((error) => {
      tableContainer.classList.remove("opacity-50");
    })
    .finally(() => {
      tableContainer.classList.remove("opacity-50");
    });
}

// Function to attach pagination event listeners
function attachPaginationListeners() {
  document.querySelectorAll(".pagination-link").forEach((button) => {
    button.addEventListener("click", (e) => {
      e.preventDefault();
      const page = e.currentTarget.dataset.page;
      const timePeriod = document.getElementById("time-period-select").value;
      updateContributorStats(timePeriod, page);
    });
  });
}

// --- AJAX Stargazers Pagination & Filter ---
function attachStargazersListeners() {
  // Pagination links
  document.querySelectorAll(".stargazers-pagination-link").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      fetchStargazers(this.getAttribute("href"));
    });
  });
  // Filter links
  document.querySelectorAll(".stargazers-filter-link").forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      fetchStargazers(this.getAttribute("href"));
    });
  });
}

function fetchStargazers(url) {
  const stargazersSection = document.getElementById("stargazers-section");
  if (!stargazersSection) return;
  // Show loading state
  stargazersSection.classList.add("opacity-50");
  fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.text();
    })
    .then((html) => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const newSection = doc.querySelector("#stargazers-section");

      if (newSection) {
        if (typeof DOMPurify !== "undefined") {
          stargazersSection.innerHTML =
            DOMPurify.sanitize(newSection.innerHTML);
        } else {
          stargazersSection.textContent =
            "Unable to load stargazers safely. Please try again later.";
          return;
        }

        window.history.pushState({}, "", url);
        attachStargazersListeners();
      }
    })
    .catch((error) => {
      // Error silently handled
    })
    .finally(() => {
      stargazersSection.classList.remove("opacity-50");
    });
}

// Initialize everything when the DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Initialize progress bars
  document.querySelectorAll(".progress-bar").forEach(function (bar) {
    const percentage = bar.getAttribute("data-percentage") + "%";
    bar.style.width = percentage;
  });

  // Attach pagination listeners
  attachPaginationListeners();

  // Set up all refresh buttons
  document.querySelectorAll(".refresh-btn").forEach((button) => {
    const section = button.getAttribute("data-section");

    // Remove the inline onclick attribute
    button.removeAttribute("onclick");

    // Add a proper event listener
    button.addEventListener("click", function (e) {
      e.preventDefault();
      refreshSection(this, section);
    });
  });

  attachStargazersListeners();

  // Set up the "Refresh from GitHub" button
  const refreshGithubBtn = document.getElementById("refresh-github-btn");
  if (refreshGithubBtn) {
    refreshGithubBtn.addEventListener("click", async function () {
      const refreshUrl = this.getAttribute("data-refresh-url");
      const originalHTML = this.innerHTML;

      // Show loading state
      this.disabled = true;
      this.innerHTML =
        '<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>Refreshing...';

      let csrfToken =
        getCookie("csrftoken") ||
        document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ||
        "";

      try {
        const response = await fetch(refreshUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
          },
        });
        if (!response.ok) {
          // If the user is not authenticated or CSRF failed, reload so Django can redirect appropriately
          if (response.status === 401 || response.status === 403) {
            window.location.reload();
            return;
          }
          throw new Error("Request failed with status " + response.status);
        }
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          // If we were redirected to a login page or received HTML, reload to let the server handle it
          if (response.redirected) {
            window.location.href = response.url;
            return;
          }
          throw new Error("Unexpected response content type: " + contentType);
        }
        const data = await response.json();
        if (data.status === "success") {
          this.innerHTML =
            '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>Refreshed!';
          this.classList.remove("bg-gray-600", "hover:bg-gray-700");
          this.classList.add("bg-green-600", "hover:bg-green-700");
          setTimeout(() => window.location.reload(), 1500);
        } else {
          this.innerHTML =
            '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>Failed';
          this.classList.remove("bg-gray-600", "hover:bg-gray-700");
          this.classList.add("bg-red-600", "hover:bg-red-700");
          setTimeout(() => {
            this.innerHTML = originalHTML;
            this.classList.remove("bg-red-600", "hover:bg-red-700");
            this.classList.add("bg-gray-600", "hover:bg-gray-700");
            this.disabled = false;
          }, 3000);
        }
      } catch (error) {
        this.innerHTML =
          '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>Error';
        this.classList.remove("bg-gray-600", "hover:bg-gray-700");
        this.classList.add("bg-red-600", "hover:bg-red-700");
        setTimeout(() => {
          this.innerHTML = originalHTML;
          this.classList.remove("bg-red-600", "hover:bg-red-700");
          this.classList.add("bg-gray-600", "hover:bg-gray-700");
          this.disabled = false;
        }, 3000);
      }
    });
  }
});
