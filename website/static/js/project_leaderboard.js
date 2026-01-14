/**
 * Project Leaderboard - Tab switching and chart rendering
 * Uses red color scheme throughout
 */

// Red color palette for consistency
const RED_COLORS = {
    primary: '#e74c3c',
    dark: '#c0392b',
    light: '#f39c12',
    shades: [
        '#e74c3c',
        '#c0392b',
        '#dc2626',
        '#ef4444',
        '#f87171',
        '#fca5a5',
        '#fecaca',
        '#fee2e2',
        '#991b1b',
        '#7f1d1d'
    ]
};

/**
 * Tab switching functionality
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');
            
            // Update button states
            tabButtons.forEach(btn => {
                if (btn.getAttribute('data-tab') === targetTab) {
                    btn.classList.add('active', 'text-[#e74c3c]', 'border-[#e74c3c]');
                    btn.classList.remove('text-gray-500', 'border-transparent');
                } else {
                    btn.classList.remove('active', 'text-[#e74c3c]', 'border-[#e74c3c]');
                    btn.classList.add('text-gray-500', 'border-transparent');
                }
            });
            
            // Update content visibility
            tabContents.forEach(content => {
                if (content.id === `tab-${targetTab}`) {
                    content.classList.remove('hidden');
                } else {
                    content.classList.add('hidden');
                }
            });
        });
    });
}

/**
 * Create horizontal bar chart with red colors
 */
function createBarChart(ctx, labels, data, label) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: RED_COLORS.primary,
                borderColor: RED_COLORS.dark,
                borderWidth: 1,
                barThickness: 40,
                maxBarThickness: 50
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            },
            layout: {
                padding: {
                    left: 10,
                    right: 10,
                    top: 10,
                    bottom: 10
                }
            }
        }
    });
}

/**
 * Create pie chart with red color gradients
 */
function createPieChart(ctx, labels, data) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: RED_COLORS.shades.slice(0, labels.length),
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

/**
 * Initialize all charts
 */
function initializeCharts(topProjects, statusDistribution) {
    // Stars Chart (Dashboard Tab) - Top 5
    const starsCtx = document.getElementById('starsChart');
    if (starsCtx && topProjects && topProjects.length > 0) {
        const top5 = topProjects.slice(0, 5);
        const starsLabels = top5.map(p => p.name);
        const starsData = top5.map(p => p.stars || 0);
        createBarChart(starsCtx, starsLabels, starsData, 'Stars');
    }
    
    // Status Distribution Chart (Dashboard Tab)
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx && statusDistribution) {
        const statusLabels = Object.keys(statusDistribution);
        const statusData = Object.values(statusDistribution);
        createPieChart(statusCtx, statusLabels, statusData);
    }
    
    // Contributors Chart (Statistics Tab) - Top 5
    const contributorsCtx = document.getElementById('contributorsChart');
    if (contributorsCtx && topProjects && topProjects.length > 0) {
        const sortedByContributors = [...topProjects].sort((a, b) => 
            (b.contributors || 0) - (a.contributors || 0)
        ).slice(0, 5);
        const contributorsLabels = sortedByContributors.map(p => p.name);
        const contributorsData = sortedByContributors.map(p => p.contributors || 0);
        createBarChart(contributorsCtx, contributorsLabels, contributorsData, 'Contributors');
    }
    
    // Forks Chart (Statistics Tab) - Top 5
    const forksCtx = document.getElementById('forksChart');
    if (forksCtx && topProjects && topProjects.length > 0) {
        const sortedByForks = [...topProjects].sort((a, b) => 
            (b.forks || 0) - (a.forks || 0)
        ).slice(0, 5);
        const forksLabels = sortedByForks.map(p => p.name);
        const forksData = sortedByForks.map(p => p.forks || 0);
        createBarChart(forksCtx, forksLabels, forksData, 'Forks');
    }
    
    // Commits Chart (Activity Tab) - Top 5
    const commitsCtx = document.getElementById('commitsChart');
    if (commitsCtx && topProjects && topProjects.length > 0) {
        const sortedByCommits = [...topProjects].sort((a, b) => 
            (b.commits || 0) - (a.commits || 0)
        ).slice(0, 5);
        const commitsLabels = sortedByCommits.map(p => p.name);
        const commitsData = sortedByCommits.map(p => p.commits || 0);
        createBarChart(commitsCtx, commitsLabels, commitsData, 'Commits');
    }
    
    // Activity Score Chart (Activity Tab) - Top 5
    const activityCtx = document.getElementById('activityChart');
    if (activityCtx && topProjects && topProjects.length > 0) {
        const sortedByActivity = [...topProjects].sort((a, b) => 
            (b.activity_score || 0) - (a.activity_score || 0)
        ).slice(0, 5);
        const activityLabels = sortedByActivity.map(p => p.name);
        const activityData = sortedByActivity.map(p => Math.round(p.activity_score || 0));
        createBarChart(activityCtx, activityLabels, activityData, 'Activity Score');
    }
}

// Initialize tabs when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTabs);
} else {
    initializeTabs();
}

// Export for use in template
window.initializeCharts = initializeCharts;
