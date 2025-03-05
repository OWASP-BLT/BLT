// Chatbot UI controls
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing chatbot UI controls');
    
    // Chat icon click handler
    const chatIcon = document.getElementById('chatIcon');
    if (chatIcon) {
        console.log('Chat icon found:', chatIcon);
        
        // Add a direct click handler
        chatIcon.onclick = function(e) {
            console.log('Chat icon clicked via onclick');
            const chatbot = document.getElementById('chatbot');
            if (chatbot) {
                chatbot.style.display = 'block';
                chatbot.classList.remove('hidden');
                this.style.display = 'none';
            }
        };
        
        // Also add an event listener as a backup
        chatIcon.addEventListener('click', function(e) {
            console.log('Chat icon clicked via addEventListener');
            const chatbot = document.getElementById('chatbot');
            if (chatbot) {
                chatbot.style.display = 'block';
                chatbot.classList.remove('hidden');
                this.style.display = 'none';
            }
        });
        
        // Make sure the element is visible and clickable
        chatIcon.style.display = 'flex';
        chatIcon.style.zIndex = '9999';
        chatIcon.style.cursor = 'pointer';
        chatIcon.style.pointerEvents = 'auto';
        
        console.log('Chat icon styles applied:', {
            display: chatIcon.style.display,
            zIndex: chatIcon.style.zIndex,
            cursor: chatIcon.style.cursor,
            pointerEvents: chatIcon.style.pointerEvents
        });
    } else {
        console.warn('Chat icon element not found');
    }
    
    // Close button click handler
    const closeBtn = document.getElementById('closeChatbot');
    if (closeBtn) {
        console.log('Close button found:', closeBtn);
        
        closeBtn.onclick = function() {
            console.log('Close button clicked');
            const chatbot = document.getElementById('chatbot');
            const chatIcon = document.getElementById('chatIcon');
            if (chatbot && chatIcon) {
                chatbot.style.display = 'none';
                chatIcon.style.display = 'flex';
            }
        };
    } else {
        console.warn('Close button element not found');
    }
    
    // Quick commands
    const quickCommands = document.querySelectorAll('.quick-command');
    console.log('Quick commands found:', quickCommands.length);
    
    quickCommands.forEach(button => {
        button.addEventListener('click', function() {
            const command = this.getAttribute('data-command');
            console.log('Quick command clicked:', command);
            
            if (command) {
                const inputField = document.getElementById('chat-message-input');
                if (inputField) {
                    inputField.value = command;
                    // Trigger submit if needed
                    const submitButton = document.getElementById('chat-message-submit');
                    if (submitButton) {
                        submitButton.click();
                    }
                }
            }
        });
    });
}); 