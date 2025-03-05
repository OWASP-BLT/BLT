// Dark Mode Toggle Logic
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const sunIcon = darkModeToggle.querySelector('.sun-icon');
    const moonIcon = darkModeToggle.querySelector('.moon-icon');
    const html = document.documentElement;
    
    // Function to toggle icons
    function toggleIcons(isDark) {
        if (isDark) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        } else {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    }

    // Function to set dark mode
    function setDarkMode(isDark) {
        if (isDark) {
            html.classList.add('dark');
            localStorage.setItem('darkMode', 'true');
        } else {
            html.classList.remove('dark');
            localStorage.setItem('darkMode', 'false');
        }
        toggleIcons(isDark);
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

    // Toggle dark mode on button click
    darkModeToggle.addEventListener('click', function() {
        const isDark = html.classList.contains('dark');
        setDarkMode(!isDark);
    });

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
}); 