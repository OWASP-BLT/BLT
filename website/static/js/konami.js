/**
 * Konami Code Easter Egg
 * Detects the classic Konami Code sequence: ↑ ↑ ↓ ↓ ← → ← → B A
 * and rewards users with a fun confetti celebration!
 */

(function() {
    'use strict';

    // Konami Code sequence
    const konamiCode = [
        'ArrowUp', 'ArrowUp',
        'ArrowDown', 'ArrowDown',
        'ArrowLeft', 'ArrowRight',
        'ArrowLeft', 'ArrowRight',
        'KeyB', 'KeyA'
    ];

    let konamiPosition = 0;
    let easterEggActivated = false;

    // Confetti configuration
    const confettiConfig = {
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
    };

    /**
     * Creates a confetti particle
     */
    function createConfettiParticle() {
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
        const particle = document.createElement('div');
        particle.style.position = 'fixed';
        particle.style.width = '10px';
        particle.style.height = '10px';
        particle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        particle.style.left = Math.random() * window.innerWidth + 'px';
        particle.style.top = '-10px';
        particle.style.borderRadius = '50%';
        particle.style.pointerEvents = 'none';
        particle.style.zIndex = '9999';
        particle.style.opacity = '1';
        
        document.body.appendChild(particle);

        // Animate the particle
        const duration = Math.random() * 3000 + 2000;
        const endY = window.innerHeight + 10;
        const startTime = Date.now();

        function animate() {
            const elapsed = Date.now() - startTime;
            const progress = elapsed / duration;

            if (progress < 1) {
                particle.style.top = (progress * endY) + 'px';
                particle.style.opacity = 1 - progress;
                requestAnimationFrame(animate);
            } else {
                particle.remove();
            }
        }

        animate();
    }

    /**
     * Triggers confetti animation
     */
    function launchConfetti() {
        for (let i = 0; i < 150; i++) {
            setTimeout(() => createConfettiParticle(), i * 30);
        }
    }

    /**
     * Shows the Easter egg message
     */
    function showEasterEggMessage() {
        const modal = document.createElement('div');
        modal.style.position = 'fixed';
        modal.style.top = '50%';
        modal.style.left = '50%';
        modal.style.transform = 'translate(-50%, -50%)';
        modal.style.backgroundColor = '#e74c3c';
        modal.style.color = 'white';
        modal.style.padding = '40px';
        modal.style.borderRadius = '15px';
        modal.style.boxShadow = '0 10px 40px rgba(0,0,0,0.3)';
        modal.style.zIndex = '10000';
        modal.style.textAlign = 'center';
        modal.style.maxWidth = '90%';
        modal.style.width = '500px';
        modal.style.animation = 'bounce 0.6s ease-out';

        modal.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 20px;">🎮</div>
            <h2 style="font-size: 28px; margin: 0 0 15px 0; font-weight: bold;">Konami Code Activated!</h2>
            <p style="font-size: 18px; margin: 0 0 20px 0;">
                You've discovered the secret! You're a true bug hunter! 🐛✨
            </p>
            <p style="font-size: 14px; margin: 0; opacity: 0.9;">
                Keep exploring OWASP BLT and finding those bugs!
            </p>
            <button id="easterEggClose" style="
                margin-top: 25px;
                padding: 12px 30px;
                background: white;
                color: #e74c3c;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
            ">Awesome!</button>
        `;

        // Add bounce animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translate(-50%, -50%); }
                40% { transform: translate(-50%, -60%); }
                60% { transform: translate(-50%, -55%); }
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(modal);

        // Add hover effect to button
        const closeBtn = document.getElementById('easterEggClose');
        closeBtn.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f8f8';
            this.style.transform = 'scale(1.05)';
        });
        closeBtn.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
            this.style.transform = 'scale(1)';
        });

        // Close modal on click
        closeBtn.addEventListener('click', function() {
            modal.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                modal.remove();
                style.remove();
            }, 300);
        });

        // Add fade out animation
        style.textContent += `
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
    }

    /**
     * Activates the Easter egg
     */
    function activateEasterEgg() {
        if (easterEggActivated) return;
        
        easterEggActivated = true;
        launchConfetti();
        showEasterEggMessage();

        // Reset after 10 seconds
        setTimeout(() => {
            easterEggActivated = false;
        }, 10000);
    }

    /**
     * Handles keydown events to detect Konami Code
     */
    function handleKeydown(event) {
        const key = event.code;
        
        // Check if the pressed key matches the expected key in the sequence
        if (key === konamiCode[konamiPosition]) {
            konamiPosition++;
            
            // If we've completed the sequence
            if (konamiPosition === konamiCode.length) {
                activateEasterEgg();
                konamiPosition = 0;
            }
        } else {
            // Reset if wrong key is pressed
            konamiPosition = 0;
        }
    }

    // Initialize the Konami Code listener
    document.addEventListener('keydown', handleKeydown);

    // Also support mobile touch gestures (optional enhancement)
    let touchStartY = null;
    let touchStartX = null;
    const touchSequence = [];

    document.addEventListener('touchstart', function(e) {
        touchStartY = e.touches[0].clientY;
        touchStartX = e.touches[0].clientX;
    });

    document.addEventListener('touchend', function(e) {
        if (!touchStartY || !touchStartX) return;

        const touchEndY = e.changedTouches[0].clientY;
        const touchEndX = e.changedTouches[0].clientX;

        const diffY = touchStartY - touchEndY;
        const diffX = touchStartX - touchEndX;

        // Determine swipe direction
        if (Math.abs(diffY) > Math.abs(diffX)) {
            // Vertical swipe
            if (diffY > 30) {
                touchSequence.push('up');
            } else if (diffY < -30) {
                touchSequence.push('down');
            }
        } else {
            // Horizontal swipe
            if (diffX > 30) {
                touchSequence.push('left');
            } else if (diffX < -30) {
                touchSequence.push('right');
            }
        }

        // Check for Konami sequence (simplified for touch: ↑ ↑ ↓ ↓ ← → ← →)
        const touchKonami = ['up', 'up', 'down', 'down', 'left', 'right', 'left', 'right'];
        if (touchSequence.length > touchKonami.length) {
            touchSequence.shift();
        }

        if (touchSequence.length === touchKonami.length &&
            touchSequence.every((val, idx) => val === touchKonami[idx])) {
            activateEasterEgg();
            touchSequence.length = 0;
        }

        touchStartY = null;
        touchStartX = null;
    });

})();
