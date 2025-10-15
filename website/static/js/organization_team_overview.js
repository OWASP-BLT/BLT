// Toggle row expansion for team overview table
function toggleRow(row) {
    const expandableContents = row.getElementsByClassName('expandable-content');
    for (let content of expandableContents) {
        const shortText = content.querySelector('.short-text');
        const fullText = content.querySelector('.full-text');
        
        if (shortText.classList.contains('hidden')) {
            shortText.classList.remove('hidden');
            fullText.classList.add('hidden');
        } else {
            shortText.classList.add('hidden');
            fullText.classList.remove('hidden');
        }
    }
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('Team Overview: Initializing...');
    
    const tableBody = document.getElementById('statusTableBody');
    const tabButtons = document.querySelectorAll('.tab-button');
    const filterPanels = document.querySelectorAll('.filter-panel');
    
    if (!tableBody) {
        console.error('Status table body not found!');
        return;
    }
    
    const initialReportCount = tableBody.dataset.initialCount || 0;
    
    console.log('Found elements:', {
        tableBody: !!tableBody,
        tabButtons: tabButtons.length,
        filterPanels: filterPanels.length,
        initialReports: initialReportCount
    });
    
    let currentTab = null;
    let taskSearchTimeout = null;
    let requestIdCounter = 0;
    let currentRequestId = 0;

    function updateTable(data) {
        console.log('Updating table with data:', data);
        tableBody.innerHTML = '';
        
        if (!data || data.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-12 text-center">
                        <div class="flex flex-col items-center">
                            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                </svg>
                            </div>
                            <h3 class="text-sm font-medium text-gray-900 mb-1">No Reports Found</h3>
                            <p class="text-sm text-gray-500">No reports found for the selected filter.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        data.forEach((report, index) => {
            console.log(`Adding row ${index}:`, report);
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 transition-colors duration-150 cursor-pointer';
            row.onclick = () => toggleRow(row);
            
            const avatarUrl = report.avatar_url || '/static/images/dummy-user.png';
            const previousWork = report.previous_work || '';
            const nextPlan = report.next_plan || '';
            const blockers = report.blockers || '';
            
            // Helper to escape HTML
            const escapeHtml = (text) => {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            };
            
            const escapedUsername     = escapeHtml(report.username);
            const escapedDate         = escapeHtml(report.date);
            const escapedAvatarUrl    = escapeHtml(avatarUrl);
            const escapedPreviousWork = escapeHtml(previousWork);
            const escapedNextPlan     = escapeHtml(nextPlan);
            const escapedBlockers     = escapeHtml(blockers);
            const escapedMood         = escapeHtml(report.current_mood || '😊');
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <img src="${escapedAvatarUrl}" alt="${escapedUsername}" class="w-8 h-8 rounded-full mr-3 object-cover">
                        <span class="text-sm font-medium text-gray-900">${escapedUsername}</span>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm text-gray-600">${escapedDate}</div>
                </td>
                <td class="px-6 py-4 expandable-content max-w-xs">
                    <div class="text-sm text-gray-600">
                        <span class="short-text">${escapedPreviousWork.slice(0, 50)}${previousWork.length > 50 ? '...' : ''}</span>
                        <span class="full-text hidden">${escapedPreviousWork}</span>
                    </div>
                </td>
                <td class="px-6 py-4 expandable-content max-w-xs">
                    <div class="text-sm text-gray-600">
                        <span class="short-text">${escapedNextPlan.slice(0, 50)}${nextPlan.length > 50 ? '...' : ''}</span>
                        <span class="full-text hidden">${escapedNextPlan}</span>
                    </div>
                </td>
                <td class="px-6 py-4 expandable-content max-w-xs">
                    <div class="text-sm text-gray-600">
                        <span class="short-text">${escapedBlockers.slice(0, 50)}${blockers.length > 50 ? '...' : ''}</span>
                        <span class="full-text hidden">${escapedBlockers}</span>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="inline-flex px-3 py-1 text-xs font-medium ${report.goal_accomplished ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'} rounded-full">
                        ${report.goal_accomplished ? 'Yes' : 'No'}
                    </span>
                </td>
                <td class="px-6 py-4">
                    <div class="text-xl">${escapedMood}</div>
                </td>
            `;
            tableBody.appendChild(row);
        });
        console.log(`Table updated with ${data.length} rows`);
    }

    function fetchFilteredData(filterType, filterValue) {
        // Increment and store request ID to prevent race conditions
        requestIdCounter++;
        const thisRequestId = requestIdCounter;
        currentRequestId = thisRequestId;
        
        const url = new URL(window.location.href);
        url.searchParams.set('filter_type', filterType);
        url.searchParams.set('filter_value', filterValue);

        console.log('Fetching data:', { requestId: thisRequestId, filterType, filterValue, url: url.toString() });
        
        // Show loading indicator
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[#e74c3c] mb-4"></div>
                        <div class="text-sm text-gray-600">Loading reports...</div>
                    </div>
                </td>
            </tr>
        `;

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            // Guard against stale responses
            if (thisRequestId !== currentRequestId) {
                console.log(`Discarding stale response (request ${thisRequestId}, current ${currentRequestId})`);
                return null;
            }
            
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Guard against stale responses
            if (thisRequestId !== currentRequestId) {
                console.log(`Discarding stale data (request ${thisRequestId}, current ${currentRequestId})`);
                return;
            }
            
            // Handle null response from discarded request
            if (data === null) {
                return;
            }
            
            console.log('Received data:', data);
            if (data && data.data !== undefined) {
                updateTable(data.data);
            } else {
                console.error('Invalid data format:', data);
                throw new Error('Invalid data format received');
            }
        })
        .catch(error => {
            // Guard against stale error handlers
            if (thisRequestId !== currentRequestId) {
                console.log(`Discarding stale error (request ${thisRequestId}, current ${currentRequestId})`);
                return;
            }
            
            console.error('Error fetching data:', error);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-12 text-center">
                        <div class="flex flex-col items-center">
                            <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                                <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                            </div>
                            <div class="text-sm text-red-600 font-medium mb-2">Error loading reports</div>
                            <div class="text-xs text-gray-500">${error.message || 'Please try refreshing the page.'}</div>
                        </div>
                    </td>
                </tr>
            `;
        });
    }

    function switchTab(tabName) {
        console.log('Switching to tab:', tabName);
        
        tabButtons.forEach(button => {
            if (button.dataset.tab === tabName) {
                button.classList.add('border-[#e74c3c]', 'text-[#e74c3c]', 'bg-[#e74c3c]/5');
                button.classList.remove('border-gray-300', 'text-gray-700');
            } else {
                button.classList.remove('border-[#e74c3c]', 'text-[#e74c3c]', 'bg-[#e74c3c]/5');
                button.classList.add('border-gray-300', 'text-gray-700');
            }
        });

        filterPanels.forEach(panel => {
            panel.classList.add('hidden');
        });
        
        const targetPanel = document.getElementById(`${tabName}-panel`);
        if (targetPanel) {
            targetPanel.classList.remove('hidden');
        } else {
            console.error(`Panel ${tabName}-panel not found`);
        }
        
        if (currentTab !== tabName) {
            const userFilter = document.getElementById('user-filter');
            const dateFilter = document.getElementById('date-filter');
            const goalFilter = document.getElementById('goal-filter');
            const taskFilter = document.getElementById('task-filter');
            
            if (userFilter) userFilter.value = '';
            if (dateFilter) dateFilter.value = '';
            if (goalFilter) goalFilter.value = '';
            if (taskFilter) taskFilter.value = '';
            
            fetchFilteredData('none', '');
        }
        
        currentTab = tabName;
    }

    // Add event listeners to tab buttons
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            switchTab(button.dataset.tab);
        });
    });

    // Add event listeners to filters with null checks
    const userFilter = document.getElementById('user-filter');
    const dateFilter = document.getElementById('date-filter');
    const goalFilter = document.getElementById('goal-filter');
    const taskFilter = document.getElementById('task-filter');

    if (userFilter) {
        userFilter.addEventListener('change', function() {
            console.log('User filter changed:', this.value);
            if (this.value) {
                fetchFilteredData('user', this.value);
            } else {
                fetchFilteredData('none', '');
            }
        });
    }

    if (dateFilter) {
        dateFilter.addEventListener('change', function() {
            console.log('Date filter changed:', this.value);
            if (this.value) {
                fetchFilteredData('date', this.value);
            } else {
                fetchFilteredData('none', '');
            }
        });
    }

    if (goalFilter) {
        goalFilter.addEventListener('change', function() {
            console.log('Goal filter changed:', this.value);
            if (this.value) {
                fetchFilteredData('goal', this.value);
            } else {
                fetchFilteredData('none', '');
            }
        });
    }

    if (taskFilter) {
        taskFilter.addEventListener('input', function() {
            const searchValue = this.value.trim();
            console.log('Task filter input:', searchValue);
            
            clearTimeout(taskSearchTimeout);
            taskSearchTimeout = setTimeout(() => {
                if (searchValue) {
                    fetchFilteredData('task', searchValue);
                } else {
                    fetchFilteredData('none', '');
                }
            }, 300);
        });
    }

    // Initialize by showing user tab
    console.log('Initializing with user tab');
    switchTab('user');
});
