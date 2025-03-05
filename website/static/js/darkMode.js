// Check for saved dark mode preference or use system preference
if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
} else {
    document.documentElement.classList.remove('dark')
}

// Function to update icons
function updateIcons() {
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    const isDark = document.documentElement.classList.contains('dark');
    
    if (sunIcon && moonIcon) {
        if (isDark) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        } else {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    }
}

// Function to toggle dark mode
function toggleDarkMode() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark')
        localStorage.theme = 'light'
    } else {
        document.documentElement.classList.add('dark')
        localStorage.theme = 'dark'
    }
    updateIcons()
}

// Listen for system dark mode changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    if (!('theme' in localStorage)) {
        if (event.matches) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
        updateIcons()
    }
})

// Initialize icons on page load
document.addEventListener('DOMContentLoaded', () => {
    updateIcons()
    
    // Add click event listener to the toggle button
    const darkModeToggle = document.getElementById('dark-mode-toggle')
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode)
    }
})

document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const sunIcon = darkModeToggle.querySelector('.sun-icon');
    const moonIcon = darkModeToggle.querySelector('.moon-icon');
    const html = document.documentElement;
    
    // Function to set dark mode
    function setDarkMode(isDark) {
        if (isDark) {
            html.classList.add('dark');
            localStorage.setItem('darkMode', 'true');
        } else {
            html.classList.remove('dark');
            localStorage.setItem('darkMode', 'false');
        }
        updateIcons();
        fixDarkModeInconsistencies();
    }

    // Function to fix any inconsistencies in dark mode
    function fixDarkModeInconsistencies() {
        const isDark = html.classList.contains('dark');
        console.log('Fixing dark mode inconsistencies. Dark mode is:', isDark);
        
        // Common elements that need fixing
        const elementsToFix = [
            '.chatbot',
            '.chat-header',
            '.chat-log',
            '.nav-link',
            '.sidebar',
            '.dropdown-menu',
            'input',
            'textarea',
            '.card'
        ];

        elementsToFix.forEach(selector => {
            document.querySelectorAll(selector).forEach(element => {
                if (isDark) {
                    element.classList.add('dark-mode-fixed');
                    element.style.backgroundColor = '';
                    element.style.color = '';
                } else {
                    element.classList.remove('dark-mode-fixed');
                    element.style.backgroundColor = '';
                    element.style.color = '';
                }
            });
        });

        // Fix red buttons to maintain their color
        document.querySelectorAll('.btn-primary').forEach(button => {
            if (isDark) {
                button.style.backgroundColor = '#e74c3c';
            }
        });
    }

    // Initialize dark mode based on localStorage
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    setDarkMode(savedDarkMode);

    // Handle window resize to recheck inconsistencies
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(fixDarkModeInconsistencies, 250);
    });

    // Add debugging
    console.log('Dark mode script loaded');
    window.toggleDarkMode = setDarkMode;
    window.fixDarkMode = fixDarkModeInconsistencies;

    // Chatbot functionality
    const chatIcon = document.getElementById('chatIcon');
    const chatbot = document.getElementById('chatbot');
    const closeChatbot = document.getElementById('closeChatbot');

    if (chatIcon && chatbot && closeChatbot) {
        chatIcon.addEventListener('click', function() {
            chatbot.classList.remove('hidden');
            chatIcon.classList.add('hidden');
        });

        closeChatbot.addEventListener('click', function() {
            chatbot.classList.add('hidden');
            chatIcon.classList.remove('hidden');
        });
    }
});