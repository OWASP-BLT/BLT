// Dark mode functionality
function updateDarkModeIcon(isDarkMode) {
    const icon = document.querySelector('#darkModeToggle i');
    if (icon) {
        icon.className = isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
        icon.style.transform = 'rotate(360deg)';
        setTimeout(() => {
            icon.style.transform = '';
        }, 300);
    }
}

function toggleDarkMode() {
    const isDarkMode = document.documentElement.dataset.theme === 'dark';
    const newTheme = isDarkMode ? 'light' : 'dark';
    
    document.documentElement.dataset.theme = newTheme;
    localStorage.setItem('theme', newTheme);
    updateDarkModeIcon(!isDarkMode);

    // Update aria-pressed on the dark mode toggle button to reflect new state
    const toggleBtn = document.getElementById('darkModeToggle');
    if (toggleBtn) {
        toggleBtn.setAttribute('aria-pressed', newTheme === 'dark' ? 'true' : 'false');
    }
}

// Initialize dark mode based on user's preference
function initializeDarkMode() {
    const savedTheme = localStorage.getItem('theme') || 
                      (globalThis.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = savedTheme;
    updateDarkModeIcon(savedTheme === 'dark');

    // Ensure aria-pressed reflects the actual theme state on load
    const toggleBtn = document.getElementById('darkModeToggle');
    if (toggleBtn) {
        toggleBtn.setAttribute('aria-pressed', savedTheme === 'dark' ? 'true' : 'false');
    }

    // Add transition styles after initial load to prevent transition on page load
    setTimeout(() => {
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    }, 100);
}

// Listen for system theme changes
globalThis.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        const newTheme = e.matches ? 'dark' : 'light';
        document.documentElement.dataset.theme = newTheme;
        updateDarkModeIcon(e.matches);
    }
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeDarkMode);