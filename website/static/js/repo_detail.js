// Function to copy text to clipboard
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);

    // Select the text
    element.select();
    element.setSelectionRange(0, 99999); // For mobile devices

    // Copy the text
    try {
        navigator.clipboard.writeText(element.value).then(() => {
            // Get the button
            const button = element.nextElementSibling;
            const originalText = button.textContent;

            // Change button style to show success
            button.textContent = 'Copied!';
            button.classList.remove('bg-red-500', 'hover:bg-red-600');
            button.classList.add('bg-green-500', 'hover:bg-green-600');

            // Reset button after 2 seconds
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('bg-green-500', 'hover:bg-green-600');
                button.classList.add('bg-red-500', 'hover:bg-red-600');
            }, 2000);
        });
    } catch (err) {
        console.error('Failed to copy text: ', err);
    }
}

// Function to refresh a section of the repository detail page
async function refreshSection(button, section) {
    // Check if already spinning
    if (button.querySelector('.animate-spin')) {
        return;
    }

    // Get the SVG icon
    const svgIcon = button.querySelector('svg');

    // Hide the original icon
    if (svgIcon) {
        svgIcon.classList.add('opacity-0');
    }

    // Create spinner with Tailwind classes (using document fragment for better performance)
    const fragment = document.createDocumentFragment();
    const spinner = document.createElement('div');
    spinner.className = 'absolute inset-0 flex items-center justify-center';
    spinner.innerHTML = `<div class="w-5 h-5 border-2 border-[#e74c3c] border-t-transparent rounded-full animate-spin"></div>`;
    fragment.appendChild(spinner);
    button.appendChild(fragment);

    // Create or reuse message container
    const container = button.closest('.refresh-container');
    let messageContainer = container.querySelector('.refresh-message');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.className = 'absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10';
        container.appendChild(messageContainer);
    }

    try {
        // Create a FormData object
        const formData = new FormData();
        formData.append('section', String(section).trim());

        // Get CSRF token (reuse implementation)
        const csrfToken = getCookie('csrftoken') || 
                        document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        // Fetch with fewer console.log statements to reduce memory usage
        const response = await fetch(window.location.href, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }

        // Parse response with error handling
        let data;
        const responseText = await response.text();
        
        try {
            // Only try to parse as JSON if it looks like JSON
            if (responseText.trim().startsWith('{')) {
                data = JSON.parse(responseText);
            } else {
                throw new Error('Response is not valid JSON');
            }
        } catch (parseError) {
            throw new Error('Failed to parse server response');
        }

        // Process different section types (implementation kept the same)
        // AI Summary section
        if (section === 'ai_summary') {
            const summaryContainer = document.getElementById('ai-summary-content');
            if (summaryContainer && data?.data?.ai_summary) {
                summaryContainer.innerHTML = data.data.ai_summary;
            } else if (summaryContainer) {
                summaryContainer.innerHTML = '<p class="text-gray-600 italic">AI summary unavailable for this repo.</p>';
            }
            showSuccessMessage(messageContainer, data.message || 'AI summary regenerated successfully');
        }
        // Basic stats section 
        else if (section === 'basic') {
            updateBasicStats(data);
            showSuccessMessage(messageContainer, data.message);
        }
        // Metrics section
        else if (section === 'metrics') {
            updateMetrics(data);
            showSuccessMessage(messageContainer, data.message);
        }
        // Technical section
        else if (section === 'technical') {
            updateTechnicalDetails(data);
            showSuccessMessage(messageContainer, data.message);
        }
        // Community section
        else if (section === 'community') {
            updateCommunitySection(data);
            showSuccessMessage(messageContainer, data.message);
        }
        // Contributor stats section
        else if (section === 'contributor_stats') {
            updateContributorStatsSection(data);
            showSuccessMessage(messageContainer, data.message || 'Contributor statistics refreshed successfully');
        }
    } catch (error) {
        // Show error message
        messageContainer.className = 'absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-red-600';
        messageContainer.textContent = error.message;
    } finally {
        // Clean up: remove spinner and restore icon
        const spinnerElement = button.querySelector('.animate-spin')?.parentNode;
        if (spinnerElement) {
            spinnerElement.remove();
        }

        if (svgIcon) {
            svgIcon.classList.remove('opacity-0');
        }

        // Remove message after 5 seconds
        setTimeout(() => {
            if (messageContainer && messageContainer.parentElement) {
                messageContainer.remove();
            }
        }, 5000);
    }
}

// Helper function to get cookie value
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper function to show success message
function showSuccessMessage(container, message) {
    container.className = 'absolute top-full right-0 mt-2 text-sm whitespace-nowrap z-10 text-green-600';
    container.textContent = message;
}

// Helper function to update basic stats
function updateBasicStats(data) {
    const updates = {
        'stars': data.data.stars,
        'forks': data.data.forks,
        'watchers': data.data.watchers,
        'network': data.data.network_count,
        'subscribers': data.data.subscribers_count,
        'last-updated': `Updated ${data.data.last_updated.replace('\u00a0', ' ')}`
    };

    // Update each stat if the element exists
    Object.entries(updates).forEach(([key, value]) => {
        const element = document.querySelector(`[data-stat="${key}"]`);
        if (element) {
            element.textContent = value;
        }
    });
}

// Helper function to update metrics
function updateMetrics(data) {
    const updates = {
        'open_issues': data.data.open_issues,
        'closed_issues': data.data.closed_issues,
        'total_issues': data.data.total_issues,
        'open_pull_requests': data.data.open_pull_requests,
        'commit_count': data.data.commit_count,
        'last_commit_date': data.data.last_commit_date
    };

    // Update each stat if the element exists
    Object.entries(updates).forEach(([key, value]) => {
        const element = document.querySelector(`[data-stat="${key}"]`);
        if (element) {
            element.textContent = value.toLocaleString();
        }
    });
}

// Helper function to update technical details
function updateTechnicalDetails(data) {
    const technicalElements = {
        'primary_language': data.data.primary_language,
        'size': `${(data.data.size / 1024).toFixed(2)} MB`,
        'license': data.data.license,
        'release_name': data.data.release_name,
        'release_date': data.data.release_date,
        'last_commit_date': data.data.last_commit_date
    };

    // Update each technical element
    Object.entries(technicalElements).forEach(([key, value]) => {
        const element = document.querySelector(`[data-tech="${key}"]`);
        if (element) {
            element.textContent = value;
        }
    });
}

// Helper function to update community section
function updateCommunitySection(data) {
    const contributorsContainer = document.querySelector('.contributors-grid');
    if (!contributorsContainer) return;

    const communityData = data.data;

    // Update total count
    const totalCountEl = document.querySelector('[data-community="total-count"]');
    if (totalCountEl) {
        totalCountEl.textContent = `${communityData.total_contributors.toLocaleString()} total contributors`;
    }

    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    // Process contributors in batches
    const BATCH_SIZE = 10;
    const contributors = communityData.contributors || [];
    
    function processBatch(startIndex) {
        const endIndex = Math.min(startIndex + BATCH_SIZE, contributors.length);
        
        for (let i = startIndex; i < endIndex; i++) {
            const contributor = contributors[i];
            const div = document.createElement('div');
            div.className = 'flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group';
            div.innerHTML = `
                <img src="${contributor.avatar_url}" width="30" height="30" alt="${contributor.name}" class="w-12 h-12 rounded-full border-2 border-white shadow-md group-hover:scale-110 transition-transform">
                <div class="flex-grow">
                    <div class="font-medium text-gray-900">
                        ${contributor.name}
                        ${contributor.verified ? '<span class="ml-1 text-green-500" title="Verified Contributor">✓</span>' : ''}
                    </div>
                    <div class="text-sm text-gray-500">${contributor.contributions.toLocaleString()} commits</div>
                </div>
                <a href="${contributor.github_url}" target="_blank" class="p-2 text-gray-400 hover:text-gray-600">
                    <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                </a>
            `;
            fragment.appendChild(div);
        }
        
        // If we have more batches, process them asynchronously
        if (endIndex < contributors.length) {
            setTimeout(() => processBatch(endIndex), 0);
        } else {
            // When all batches are processed, update the DOM
            contributorsContainer.innerHTML = '';
            contributorsContainer.appendChild(fragment);
        }
    }
    
    // Start processing the first batch
    if (contributors.length > 0) {
        processBatch(0);
    } else {
        contributorsContainer.innerHTML = '<div class="p-4 text-center text-gray-500">No contributors found</div>';
    }
}

// Helper function to update contributor stats section
function updateContributorStatsSection(data) {
    const statsTableBody = document.querySelector('.contributor-stats-table tbody');
    if (!statsTableBody) return;

    // Clear existing table content
    statsTableBody.innerHTML = '';

    if (!data.data.stats || !data.data.stats.length) {
        statsTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                    No contributor statistics available for this period
                </td>
            </tr>
        `;
        return;
    }
    
    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    // Process stats in batches
    const BATCH_SIZE = 10;
    const stats = data.data.stats;
    
    function processBatch(startIndex) {
        const endIndex = Math.min(startIndex + BATCH_SIZE, stats.length);
        
        for (let i = startIndex; i < endIndex; i++) {
            const stat = stats[i];
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 transition-colors';
            row.innerHTML = `
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
                    ${stat.commits ? stat.commits.toLocaleString() : '0'}
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-center text-blue-600 font-medium">
                    ${stat.issues_opened ? stat.issues_opened.toLocaleString() : '0'}
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-center text-purple-600 font-medium">
                    ${stat.issues_closed ? stat.issues_closed.toLocaleString() : '0'}
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-center text-orange-600 font-medium">
                    ${stat.pull_requests ? stat.pull_requests.toLocaleString() : '0'}
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-center text-cyan-600 font-medium">
                    ${stat.comments ? stat.comments.toLocaleString() : '0'}
                </td>
                <td class="px-4 py-4 whitespace-nowrap text-center">
                    <div class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${stat.impact_level.class}">
                        ${stat.impact_level.text}
                    </div>
                </td>
            `;
            fragment.appendChild(row);
        }
        
        // If we have more batches, process them asynchronously
        if (endIndex < stats.length) {
            setTimeout(() => processBatch(endIndex), 0);
        } else {
            // When all batches are processed, update the DOM
            statsTableBody.appendChild(fragment);
        }
    }
    
    // Start processing the first batch
    processBatch(0);
}

// Function to update contributor stats
function updateContributorStats(timePeriod, page = 1) {
    // Show loading state
    const tableContainer = document.querySelector('.contributor-stats-table');
    if (!tableContainer) return;  // Guard clause

    tableContainer.classList.add('opacity-50');

    // Prepare form data
    const formData = new FormData();
    formData.append('time_period', timePeriod);
    formData.append('page', page);

    // Update URL query parameters without reloading
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('time_period', timePeriod);
    currentUrl.searchParams.set('page', page);

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    // Use fetch with fewer console logs to reduce memory usage
    fetch(window.location.pathname, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.text();
    })
    .then(html => {
        // Use document fragment for better performance
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Clear existing content
        tableContainer.innerHTML = '';
        
        // Append elements
        while (tempDiv.firstChild) {
            tableContainer.appendChild(tempDiv.firstChild);
        }
        
        // Update URL without page reload
        window.history.pushState({}, '', currentUrl.toString());

        // Re-attach event listeners to new pagination buttons
        attachPaginationListeners();
    })
    .catch(error => {
        // Handle error with less console output
        tableContainer.innerHTML = '<div class="text-center text-red-500 p-4">Failed to load data</div>';
    })
    .finally(() => {
        tableContainer.classList.remove('opacity-50');
    });
}

// Function to attach pagination event listeners
function attachPaginationListeners() {
    document.querySelectorAll('.pagination-link').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const page = e.target.dataset.page;
            const timePeriod = document.getElementById('time-period-select').value;
            updateContributorStats(timePeriod, page);
        });
    });
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    // Initialize progress bars
    document.querySelectorAll('.progress-bar').forEach(function (bar) {
        const percentage = bar.getAttribute('data-percentage') + '%';
        bar.style.width = percentage;
    });

    // Attach pagination listeners
    attachPaginationListeners();

    // Set up AI Summary button with direct event listener
    const aiSummaryButton = document.querySelector('button[data-section="ai_summary"]');
    if (aiSummaryButton) {
        console.log('AI Summary button found:', aiSummaryButton);

        // Remove the inline onclick attribute and add a proper event listener
        aiSummaryButton.removeAttribute('onclick');

        aiSummaryButton.addEventListener('click', function (e) {
            e.preventDefault();
            console.log('AI Summary button clicked via event listener');
            refreshSection(this, 'ai_summary');
        });
    }

    // Set up all refresh buttons
    document.querySelectorAll('.refresh-btn').forEach(button => {
        const section = button.getAttribute('data-section');

        // Remove the inline onclick attribute
        button.removeAttribute('onclick');

        // Add a proper event listener
        button.addEventListener('click', function (e) {
            e.preventDefault();
            console.log(`Refresh button clicked for section: ${section}`);
            refreshSection(this, section);
        });
    });
}); 