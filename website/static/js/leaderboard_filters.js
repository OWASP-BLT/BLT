/**
 * Leaderboard Filtering and Sorting
 */

class LeaderboardFilters {
    constructor() {
        this.currentFilters = {
            sortBy: 'stars',
            order: 'desc',
            search: '',
            language: '',
            minStars: null,
            limit: 10
        };
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadData();
    }

    attachEventListeners() {
        // Sort dropdown
        const sortSelect = document.getElementById('sort-by');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.currentFilters.sortBy = e.target.value;
                this.loadData();
            });
        }

        // Order toggle
        const orderSelect = document.getElementById('sort-order');
        if (orderSelect) {
            orderSelect.addEventListener('change', (e) => {
                this.currentFilters.order = e.target.value;
                this.loadData();
            });
        }

        // Search input
        const searchInput = document.getElementById('search-projects');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.currentFilters.search = e.target.value;
                    this.loadData();
                }, 500); // Debounce 500ms
            });
        }

        // Min stars slider
        const minStarsSlider = document.getElementById('min-stars');
        if (minStarsSlider) {
            minStarsSlider.addEventListener('change', (e) => {
                this.currentFilters.minStars = parseInt(e.target.value);
                document.getElementById('min-stars-value').textContent = e.target.value;
                this.loadData();
            });
        }

        // Limit select
        const limitSelect = document.getElementById('results-limit');
        if (limitSelect) {
            limitSelect.addEventListener('change', (e) => {
                this.currentFilters.limit = parseInt(e.target.value);
                this.loadData();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAllData());
        }

        // Real-time toggle
        const realtimeToggle = document.getElementById('realtime-updates');
        if (realtimeToggle) {
            realtimeToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }
    }

    async loadData() {
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (value !== null && value !== '') {
                params.append(key, value);
            }
        });

        try {
            this.showLoading();
            const response = await fetch(`/api/leaderboard/?${params}`);
            const data = await response.json();

            if (data.success) {
                this.renderLeaderboard(data.data);
                this.updateCharts(data.data);
            } else {
                this.showError('Failed to load leaderboard data');
            }
        } catch (error) {
            console.error('Error loading leaderboard:', error);
            this.showError('Network error loading data');
        } finally {
            this.hideLoading();
        }
    }

    renderLeaderboard(projects) {
        const container = document.getElementById('leaderboard-results');
        if (!container) return;

        if (projects.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <div class="text-gray-400 text-lg">
                        <i class="fas fa-search mb-4 text-4xl"></i>
                        <p>No projects found matching your criteria</p>
                    </div>
                </div>
            `;
            return;
        }

        const html = projects.map((project, index) => {
            const rank = index + 1;
            const rankClass = rank <= 3 ? 'top-rank' : '';
            const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';

            return `
                <div class="leaderboard-item ${rankClass} bg-white dark:bg-gray-800 rounded-lg p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1" data-rank="${rank}">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-4 flex-1">
                            <div class="rank-badge text-2xl font-bold ${rankClass ? 'text-yellow-500' : 'text-gray-400'}">
                                ${medal || `#${rank}`}
                            </div>
                            <div class="flex-1">
                                <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-1">
                                    <a href="/project/${project.slug}/" class="hover:text-red-500 transition-colors">
                                        ${project.name}
                                    </a>
                                </h3>
                                <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${project.description || 'OWASP Project'}</p>
                                
                                <div class="flex flex-wrap gap-4 text-sm">
                                    <div class="stat-item" title="Stars">
                                        <i class="fas fa-star text-yellow-500"></i>
                                        <span class="font-semibold">${project.stats.stars.toLocaleString()}</span>
                                    </div>
                                    <div class="stat-item" title="Forks">
                                        <i class="fas fa-code-branch text-blue-500"></i>
                                        <span class="font-semibold">${project.stats.forks.toLocaleString()}</span>
                                    </div>
                                    <div class="stat-item" title="Issues">
                                        <i class="fas fa-exclamation-circle text-red-500"></i>
                                        <span class="font-semibold">${project.stats.open_issues.toLocaleString()}</span>
                                    </div>
                                    <div class="stat-item" title="Contributors">
                                        <i class="fas fa-users text-green-500"></i>
                                        <span class="font-semibold">${project.stats.contributors.toLocaleString()}</span>
                                    </div>
                                    <div class="stat-item" title="Commits">
                                        <i class="fas fa-code-commit text-purple-500"></i>
                                        <span class="font-semibold">${project.stats.commits.toLocaleString()}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex flex-col items-end space-y-2">
                            <a href="${project.repo_url}" target="_blank" class="text-gray-500 hover:text-red-500 transition-colors">
                                <i class="fab fa-github text-2xl"></i>
                            </a>
                            <button class="refresh-project-btn text-xs text-gray-500 hover:text-red-500" data-project-id="${project.id}" title="Refresh stats">
                                <i class="fas fa-sync-alt"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Progress bars for visual comparison -->
                    <div class="mt-4 space-y-2">
                        <div class="relative">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill bg-yellow-500" style="width: ${this.calculatePercentage(project.stats.stars, 'stars')}%"></div>
                            </div>
                            <span class="text-xs text-gray-500">Stars</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;

        // Attach refresh buttons
        document.querySelectorAll('.refresh-project-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projectId = e.currentTarget.dataset.projectId;
                this.refreshProjectStats(projectId);
            });
        });

        // Animate items
        this.animateItems();
    }

    calculatePercentage(value, metric) {
        // Calculate percentage based on max value in current dataset
        const maxValues = {
            stars: 31000,
            forks: 15900,
            commits: 21432
        };
        return Math.min((value / maxValues[metric]) * 100, 100);
    }

    updateCharts(projects) {
        // Update Chart.js charts if they exist
        if (typeof initializeCharts === 'function') {
            // Will trigger chart updates
            window.dispatchEvent(new CustomEvent('leaderboardDataUpdated', { detail: projects }));
        }
    }

    async refreshProjectStats(projectId) {
        const btn = document.querySelector(`[data-project-id="${projectId}"]`);
        if (btn) {
            btn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
            btn.disabled = true;
        }

        try {
            const response = await fetch(`/api/project/${projectId}/refresh/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                }
            });

            const data = await response.json();
            if (data.success) {
                this.showNotification('Stats refreshed successfully!', 'success');
                this.loadData(); // Reload all data
            } else {
                this.showNotification('Failed to refresh stats', 'error');
            }
        } catch (error) {
            console.error('Error refreshing stats:', error);
            this.showNotification('Network error', 'error');
        } finally {
            if (btn) {
                btn.innerHTML = '<i class="fas fa-sync-alt"></i>';
                btn.disabled = false;
            }
        }
    }

    async refreshAllData() {
        const btn = document.getElementById('refresh-data');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-sync-alt fa-spin mr-2"></i>Refreshing...';
            btn.disabled = true;
        }

        await this.loadData();

        if (btn) {
            btn.innerHTML = '<i class="fas fa-sync-alt mr-2"></i>Refresh Data';
            btn.disabled = false;
        }

        this.showNotification('Data refreshed!', 'success');
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.loadData();
        }, 60000); // Refresh every minute
        this.showNotification('Auto-refresh enabled', 'info');
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
        this.showNotification('Auto-refresh disabled', 'info');
    }

    animateItems() {
        const items = document.querySelectorAll('.leaderboard-item');
        items.forEach((item, index) => {
            setTimeout(() => {
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    item.style.transition = 'all 0.5s ease';
                    item.style.opacity = '1';
                    item.style.transform = 'translateY(0)';
                }, 50);
            }, index * 50);
        });
    }

    showLoading() {
        const container = document.getElementById('leaderboard-results');
        if (container) {
            container.innerHTML = `
                <div class="flex justify-center items-center py-12">
                    <div class="text-center">
                        <i class="fas fa-spinner fa-spin text-4xl text-red-500 mb-4"></i>
                        <p class="text-gray-600 dark:text-gray-400">Loading leaderboard data...</p>
                    </div>
                </div>
            `;
        }
    }

    hideLoading() {
        // Loading will be replaced by actual content
    }

    showError(message) {
        const container = document.getElementById('leaderboard-results');
        if (container) {
            container.innerHTML = `
                <div class="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-200 px-4 py-3 rounded">
                    <p><i class="fas fa-exclamation-triangle mr-2"></i>${message}</p>
                </div>
            `;
        }
    }

    showNotification(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg transition-all duration-300 z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            type === 'info' ? 'bg-blue-500' : 'bg-gray-500'
        } text-white`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    getCookie(name) {
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
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.leaderboardFilters = new LeaderboardFilters();
});
