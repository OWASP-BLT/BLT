/**
 * This should be loaded only on pages that actually have notification containers
 */
document.addEventListener('DOMContentLoaded', function() {
    // Only fetch notifications if we're on a page that has the container
    const notificationsContainer = document.getElementById('notifications-container');
    
    if (!notificationsContainer) {
        return;
    }
    
    try {
        fetch('/api/notifications/')
            .then(response => {
                if (!response.ok) {
                    if (response.redirected) {
                        throw new Error('Login required');
                    }
                    throw new Error('Network response was not ok');
                }
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Invalid response format');
                }
                return response.json();
            })
            .then(data => {
                const container = document.getElementById('notifications-container');
                if (!container) return;
                
                container.innerHTML = '';
                
                if (!data || data.length === 0) {
                    container.innerHTML = '<p class="text-gray-500 p-4">No notifications</p>';
                } else {
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'p-3 border-b';
                        div.textContent = item.message || 'Notification';
                        container.appendChild(div);
                    });
                }
            })
            .catch(error => {
                console.log('Notifications error (handled):', error.message);
                const container = document.getElementById('notifications-container');
                if (container) {
                    container.innerHTML = '<p class="text-gray-500 p-4">Unable to load notifications</p>';
                }
            });
    } catch (e) {
        console.log('Fatal error in notifications (handled):', e.message);
    }
}); 