/**
 * Easter Eggs Handler for BLT Website
 * Handles various Easter egg interactions including keyboard shortcuts,
 * click events, and mobile-friendly touch gestures
 */

(function() {
    'use strict';

    // Easter egg state
    const state = {
        konamiSequence: [],
        konamiCode: ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'],
        secretClicks: 0,
        lastClickTime: 0,
        discovered: new Set()
    };

    // Get CSRF token from cookie
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

    // Get CSRF token for AJAX requests
    function getCSRFToken() {
        return getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Send Easter egg discovery to server
     */
    async function discoverEasterEgg(code, needsVerification = false) {
        // Check if already discovered
        if (state.discovered.has(code)) {
            showNotification('You already found this Easter egg!', 'info');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('code', code);
            formData.append('csrfmiddlewaretoken', getCSRFToken());

            // For bacon Easter egg, get verification token first
            if (needsVerification) {
                const verifyResponse = await fetch(`/easter-eggs/verify/?code=${encodeURIComponent(code)}`, {
                    credentials: 'same-origin'
                });
                const verifyData = await verifyResponse.json();
                if (verifyData.token) {
                    formData.append('verification', verifyData.token);
                }
            }

            const response = await fetch('/easter-eggs/discover/', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            const data = await response.json();

            if (response.ok && data.success) {
                state.discovered.add(code);
                showEasterEggNotification(data);
                
                // Play celebration animation
                if (data.reward_type === 'bacon') {
                    playBaconAnimation();
                }
            } else {
                if (data.already_discovered) {
                    state.discovered.add(code);
                }
                showNotification(data.error || 'Easter egg discovery failed', 'error');
            }
        } catch (error) {
            console.error('Error discovering Easter egg:', error);
            showNotification('Failed to discover Easter egg', 'error');
        }
    }

    /**
     * Show Easter egg discovery notification
     */
    function showEasterEggNotification(data) {
        const message = `🎉 ${data.message}\n${data.reward_message || ''}`;
        showNotification(message, 'success');
        
        // Show a more elaborate modal for special rewards
        if (data.reward_type === 'bacon' && data.reward_amount > 0) {
            showBaconModal(data);
        }
    }

    /**
     * Show bacon reward modal
     */
    function showBaconModal(data) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 easter-egg-modal';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-8 max-w-md mx-4 text-center animate-bounce-in">
                <div class="text-6xl mb-4">🥓</div>
                <h2 class="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Congratulations!</h2>
                <p class="text-xl mb-2 text-gray-700 dark:text-gray-300">${data.message}</p>
                <p class="text-2xl font-bold mb-4" style="color: #e74c3c;">
                    + ${data.reward_amount} BACON Tokens!
                </p>
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">${data.description}</p>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="px-6 py-3 rounded-lg font-semibold text-white transition-colors"
                        style="background-color: #e74c3c;">
                    Awesome!
                </button>
            </div>
        `;
        document.body.appendChild(modal);

        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.remove();
            }
        }, 10000);
    }

    /**
     * Show simple notification
     */
    function showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (typeof $.notify === 'function') {
            $.notify(message, type);
        } else {
            // Fallback to console
            console.log(`[${type}] ${message}`);
            // Simple toast notification
            const toast = document.createElement('div');
            toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
                type === 'success' ? 'bg-green-500' : 
                type === 'error' ? 'bg-red-500' : 'bg-blue-500'
            } text-white`;
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }
    }

    /**
     * Play bacon animation
     */
    function playBaconAnimation() {
        // Create bacon emojis falling from top
        for (let i = 0; i < 10; i++) {
            setTimeout(() => {
                const bacon = document.createElement('div');
                bacon.textContent = '🥓';
                bacon.className = 'easter-egg-bacon';
                bacon.style.cssText = `
                    position: fixed;
                    top: -50px;
                    left: ${Math.random() * 100}%;
                    font-size: 30px;
                    animation: fall 3s linear;
                    pointer-events: none;
                    z-index: 9999;
                `;
                document.body.appendChild(bacon);
                setTimeout(() => bacon.remove(), 3000);
            }, i * 200);
        }
    }

    /**
     * Konami Code Easter Egg
     */
    function initKonamiCode() {
        document.addEventListener('keydown', (e) => {
            state.konamiSequence.push(e.key);
            if (state.konamiSequence.length > state.konamiCode.length) {
                state.konamiSequence.shift();
            }

            if (JSON.stringify(state.konamiSequence) === JSON.stringify(state.konamiCode)) {
                discoverEasterEgg('konami-code');
                state.konamiSequence = [];
            }
        });
    }

    /**
     * Secret Logo Click Easter Egg (mobile friendly)
     */
    function initLogoEasterEgg() {
        const logo = document.querySelector('a[href="/"]') || document.querySelector('.navbar-brand');
        if (!logo) return;

        const handleClick = (e) => {
            const now = Date.now();
            if (now - state.lastClickTime < 500) {
                state.secretClicks++;
                if (state.secretClicks >= 7) {
                    e.preventDefault();
                    discoverEasterEgg('secret-logo');
                    state.secretClicks = 0;
                }
            } else {
                state.secretClicks = 1;
            }
            state.lastClickTime = now;
        };

        logo.addEventListener('click', handleClick);
        logo.addEventListener('touchend', handleClick);
    }

    /**
     * Footer Secret Easter Egg (mobile friendly)
     */
    function initFooterEasterEgg() {
        const footer = document.querySelector('footer') || document.querySelector('.footer');
        if (!footer) return;

        let tapCount = 0;
        let tapTimeout;

        const handleTap = () => {
            tapCount++;
            clearTimeout(tapTimeout);

            if (tapCount >= 5) {
                discoverEasterEgg('footer-tap');
                tapCount = 0;
            } else {
                tapTimeout = setTimeout(() => {
                    tapCount = 0;
                }, 2000);
            }
        };

        footer.addEventListener('click', handleTap);
        footer.addEventListener('touchend', handleTap);
    }

    /**
     * Secret Bacon Easter Egg - The one that awards BACON tokens
     * Hidden behind triple-click on specific element with special keyboard combo
     */
    function initSecretBaconEasterEgg() {
        let secretKeyCombo = [];
        const baconCombo = ['b', 'a', 'c', 'o', 'n'];

        document.addEventListener('keydown', (e) => {
            secretKeyCombo.push(e.key.toLowerCase());
            if (secretKeyCombo.length > baconCombo.length) {
                secretKeyCombo.shift();
            }

            if (JSON.stringify(secretKeyCombo) === JSON.stringify(baconCombo)) {
                // Show hint to find the bacon
                showNotification('🥓 The bacon is hidden... look for something delicious!', 'info');
                // Activate bacon clickable elements
                activateBaconElements();
                secretKeyCombo = [];
            }
        });
    }

    /**
     * Activate special bacon elements
     */
    function activateBaconElements() {
        // Add special class to bacon-related elements
        const baconElements = document.querySelectorAll('[href*="bacon"], .bacon-icon, img[src*="bacon"]');
        baconElements.forEach(el => {
            el.classList.add('bacon-active');
            el.style.animation = 'pulse 1s infinite';
            
            const handler = (e) => {
                e.preventDefault();
                e.stopPropagation();
                discoverEasterEgg('secret-bacon', true); // true = needs verification
                el.classList.remove('bacon-active');
                el.style.animation = '';
                el.removeEventListener('click', handler);
                el.removeEventListener('touchend', handler);
            };

            el.addEventListener('click', handler);
            el.addEventListener('touchend', handler);
        });

        // Auto-deactivate after 30 seconds
        setTimeout(() => {
            baconElements.forEach(el => {
                el.classList.remove('bacon-active');
                el.style.animation = '';
            });
        }, 30000);
    }

    /**
     * Double-tap anywhere Easter Egg (mobile specific)
     */
    function initDoubleTapEasterEgg() {
        let lastTap = 0;
        let tapPosition = {x: 0, y: 0};

        document.addEventListener('touchend', (e) => {
            const now = Date.now();
            const touch = e.changedTouches[0];
            const currentPos = {x: touch.clientX, y: touch.clientY};

            // Check if taps are in same location and within time window
            if (now - lastTap < 300 && 
                Math.abs(currentPos.x - tapPosition.x) < 50 &&
                Math.abs(currentPos.y - tapPosition.y) < 50) {
                // Random chance (5%) to trigger Easter egg on double-tap
                if (Math.random() < 0.05) {
                    discoverEasterEgg('lucky-tap');
                }
            }

            lastTap = now;
            tapPosition = currentPos;
        });
    }

    /**
     * Four corners Easter Egg (click all four corners)
     */
    function initFourCornersEasterEgg() {
        const corners = new Set();
        const cornerSize = 50; // pixels

        document.addEventListener('click', (e) => {
            const x = e.clientX;
            const y = e.clientY;
            const w = window.innerWidth;
            const h = window.innerHeight;

            if (x < cornerSize && y < cornerSize) corners.add('tl');
            else if (x > w - cornerSize && y < cornerSize) corners.add('tr');
            else if (x < cornerSize && y > h - cornerSize) corners.add('bl');
            else if (x > w - cornerSize && y > h - cornerSize) corners.add('br');

            if (corners.size === 4) {
                discoverEasterEgg('four-corners');
                corners.clear();
            }
        });
    }

    /**
     * Scroll Easter Egg - scroll to bottom quickly
     */
    function initScrollEasterEgg() {
        let scrollCount = 0;
        let lastScrollTime = 0;

        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = document.documentElement.clientHeight;

            // Check if scrolled near bottom
            if (scrollTop + clientHeight >= scrollHeight - 100) {
                const now = Date.now();
                if (now - lastScrollTime < 5000) {
                    scrollCount++;
                    if (scrollCount >= 3) {
                        discoverEasterEgg('speed-scroller');
                        scrollCount = 0;
                    }
                } else {
                    scrollCount = 1;
                }
                lastScrollTime = now;
            }
        });
    }

    // Add CSS animations
    function addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fall {
                to {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }

            @keyframes bounce-in {
                0% {
                    transform: scale(0.3);
                    opacity: 0;
                }
                50% {
                    transform: scale(1.05);
                }
                70% {
                    transform: scale(0.9);
                }
                100% {
                    transform: scale(1);
                    opacity: 1;
                }
            }

            @keyframes pulse {
                0%, 100% {
                    transform: scale(1);
                    filter: drop-shadow(0 0 0 rgba(231, 76, 60, 0));
                }
                50% {
                    transform: scale(1.1);
                    filter: drop-shadow(0 0 10px rgba(231, 76, 60, 0.8));
                }
            }

            .animate-bounce-in {
                animation: bounce-in 0.5s ease-out;
            }

            .bacon-active {
                cursor: pointer !important;
                position: relative;
            }

            .easter-egg-modal {
                animation: fadeIn 0.3s ease-in;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }

    // Initialize all Easter eggs when DOM is ready
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Add styles
        addStyles();

        // Initialize Easter eggs
        initKonamiCode();
        initLogoEasterEgg();
        initFooterEasterEgg();
        initSecretBaconEasterEgg();
        initDoubleTapEasterEgg();
        initFourCornersEasterEgg();
        initScrollEasterEgg();

        console.log('🥚 Easter eggs initialized! Can you find them all?');
    }

    init();
})();
