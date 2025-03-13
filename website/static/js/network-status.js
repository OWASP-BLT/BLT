/**
 * network-status.js - Handles network connectivity detection and UI updates
 * 
 * This script provides:
 * 1. Network status detection
 * 2. UI notifications for offline/online status
 * 3. Event listeners for network changes
 */

(function() {
    // Current network status
    let isOnline = navigator.onLine;
    
    // DOM elements for status indicators
    let statusIndicator = null;
    let offlineNotification = null;
    
    /**
     * Check if the browser is online
     * @returns {boolean} True if online, false if offline
     */
    function checkOnlineStatus() {
        return navigator.onLine;
    }
    
    /**
     * Create and show an offline notification
     */
    function showOfflineNotification() {
        if (!offlineNotification) {
            offlineNotification = document.createElement('div');
            offlineNotification.className = 'offline-notification';
            offlineNotification.innerHTML = `
                <div class="offline-notification-content">
                    <i class="fa fa-wifi"></i> You are currently offline. Some content may be stale.
                    <button class="offline-close-btn">&times;</button>
                </div>
            `;
            document.body.appendChild(offlineNotification);
            
            // Add event listener to close button
            offlineNotification.querySelector('.offline-close-btn').addEventListener('click', function() {
                offlineNotification.style.display = 'none';
            });
        } else {
            offlineNotification.style.display = 'block';
        }
    }
    
    /**
     * Hide the offline notification
     */
    function hideOfflineNotification() {
        if (offlineNotification) {
            offlineNotification.style.display = 'none';
        }
    }
    
    /**
     * Create a network status indicator in the UI
     */
    function createStatusIndicator() {
        if (!statusIndicator) {
            statusIndicator = document.createElement('div');
            statusIndicator.className = 'network-status-indicator';
            statusIndicator.innerHTML = '<i class="fa fa-wifi"></i>';
            document.body.appendChild(statusIndicator);
        }
        
        updateStatusIndicator();
    }
    
    /**
     * Update the status indicator based on current network status
     */
    function updateStatusIndicator() {
        if (!statusIndicator) return;
        
        if (isOnline) {
            statusIndicator.classList.remove('offline');
            statusIndicator.classList.add('online');
            statusIndicator.title = 'Online';
        } else {
            statusIndicator.classList.remove('online');
            statusIndicator.classList.add('offline');
            statusIndicator.title = 'Offline - Showing cached content';
        }
    }
    
    /**
     * Called when the browser goes online
     */
    function handleOnline() {
        isOnline = true;
        updateStatusIndicator();
        hideOfflineNotification();
        
        // Dispatch a custom event
        document.dispatchEvent(new CustomEvent('networkStatusChange', { 
            detail: { online: true } 
        }));
    }
    
    /**
     * Called when the browser goes offline
     */
    function handleOffline() {
        isOnline = false;
        updateStatusIndicator();
        showOfflineNotification();
        
        // Dispatch a custom event
        document.dispatchEvent(new CustomEvent('networkStatusChange', { 
            detail: { online: false } 
        }));
    }
    
    /**
     * Check if a response indicates it was served from cache due to network issues
     */
    function isResponseFromCache(response) {
        return response.headers && 
               (response.headers.get('X-Served-From-Cache') === 'true' || 
                response.headers.get('X-Network-Status') === 'offline');
    }
    
    /**
     * Initialize network status tracking
     */
    function init() {
        // Add event listeners for online/offline events
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        
        // Create the status indicator in the UI
        createStatusIndicator();
        
        // Check initial status
        isOnline = checkOnlineStatus();
        
        // Check server-reported status by looking at headers
        fetch('/api/stats/', { method: 'HEAD' })
            .then(response => {
                if (isResponseFromCache(response) || response.headers.get('X-Network-Status') === 'offline') {
                    // Server thinks we're offline
                    handleOffline();
                }
            })
            .catch(() => {
                // If fetch fails, we're definitely offline
                handleOffline();
            });
            
        // If offline, show notification
        if (!isOnline) {
            showOfflineNotification();
        }
        
        // Add CSS for the network status indicator and notifications
        addStyles();
    }
    
    /**
     * Add CSS styles for the network status UI
     */
    function addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .network-status-indicator {
                position: fixed;
                bottom: 10px;
                right: 10px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: #f8f9fa;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                z-index: 9999;
                cursor: pointer;
            }
            
            .network-status-indicator.online {
                color: green;
            }
            
            .network-status-indicator.offline {
                color: red;
            }
            
            .offline-notification {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background-color: #f8d7da;
                color: #721c24;
                padding: 10px;
                text-align: center;
                z-index: 10000;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }
            
            .offline-notification-content {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            
            .offline-close-btn {
                background: none;
                border: none;
                color: #721c24;
                font-size: 18px;
                cursor: pointer;
                margin-left: auto;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Expose API for other scripts to use
    window.NetworkStatus = {
        isOnline: function() {
            return isOnline;
        },
        checkConnection: function() {
            return fetch('/api/stats/', { method: 'HEAD' })
                .then(() => true)
                .catch(() => false);
        }
    };
})(); 