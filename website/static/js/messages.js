/**
 * Message handling functionality for BLT
 * Handles dismissal of error and success messages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle message dismissal
    const messageContainer = document.getElementById('messages-container');
    
    if (messageContainer) {
        // Handle close button clicks
        messageContainer.addEventListener('click', function(e) {
            if (e.target && (e.target.classList.contains('close-message') || e.target.closest('.close-message'))) {
                const messageAlert = e.target.closest('.message-alert');
                if (messageAlert) {
                    messageAlert.style.opacity = '0';
                    setTimeout(() => {
                        if (messageAlert.parentNode) {
                            messageAlert.remove();
                        }
                    }, 300);
                }
            }
        });

        // Auto-dismiss messages after 5 seconds
        const messages = messageContainer.querySelectorAll('.message-alert');
        messages.forEach(function(message) {
            setTimeout(function() {
                if (message && message.parentNode) {
                    message.style.opacity = '0';
                    setTimeout(() => {
                        if (message.parentNode) {
                            message.remove();
                        }
                    }, 300);
                }
            }, 5000);
        });
    }

    // Legacy support for organization dashboard template
    const legacyMessages = document.querySelectorAll('.popup-errors');
    if (legacyMessages.length > 0) {
        legacyMessages.forEach(function(message) {
            const closeBtn = message.querySelector('.close-message');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    message.style.opacity = '0';
                    setTimeout(() => {
                        if (message.parentNode) {
                            message.remove();
                        }
                    }, 300);
                });
            }
        });
    }
});

// Global function for removing errors (legacy support)
function removeErrors() {
    const errors = document.querySelectorAll('.popup-errors, .message-alert');
    errors.forEach(function(error) {
        error.style.opacity = '0';
        setTimeout(() => {
            if (error.parentNode) {
                error.remove();
            }
        }, 300);
    });
}

// Function to create new messages programmatically
window.createMessage = function(content, type = 'info', duration = 5000) {
    const messageContainer = document.getElementById('messages-container');
    if (!messageContainer) return;

    const messageAlert = document.createElement('div');
    messageAlert.className = `message-alert mb-3 p-4 rounded-lg flex items-center justify-between shadow-lg transition-opacity duration-300 ${
        type === 'success' ? 'bg-green-100 text-green-700 border-l-4 border-green-500' :
        type === 'error' ? 'bg-red-100 text-red-700 border-l-4 border-red-500' :
        type === 'warning' ? 'bg-yellow-100 text-yellow-700 border-l-4 border-yellow-500' :
        'bg-blue-100 text-blue-700 border-l-4 border-blue-500'
    }`;
    
    const textDiv = document.createElement('div');
    textDiv.className = 'flex-grow mr-3';
    textDiv.textContent = content;
    
    const closeButton = document.createElement('button');
    closeButton.className = 'text-gray-500 hover:text-gray-700 focus:outline-none close-message';
    closeButton.innerHTML = '×';
    
    messageAlert.appendChild(textDiv);
    messageAlert.appendChild(closeButton);
    messageContainer.appendChild(messageAlert);
    
    if (duration > 0) {
        setTimeout(function() {
            messageAlert.style.opacity = '0';
            setTimeout(() => {
                if (messageAlert.parentNode) {
                    messageAlert.remove();
                }
            }, 300);
        }, duration);
    }
    
    return messageAlert;
}; 
