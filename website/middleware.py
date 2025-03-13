import time
from django.utils.deprecation import MiddlewareMixin
from website.cache_utils import check_network_status, is_network_available
import asyncio

class NetworkStatusMiddleware:
    """
    Middleware to track network status and inject appropriate headers.
    
    This middleware will:
    1. Periodically check network connectivity
    2. Add response headers to indicate network status
    3. Trigger offline mode behavior when network is unavailable
    """
    
    # Set to 'both' to indicate this middleware supports both sync and async requests
    async_mode = 'both'
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_check_time = 0
        self.check_interval = 60  # Check network status every 60 seconds
    
    def __call__(self, request):
        """Handle synchronous requests"""
        # Check network status periodically
        self._check_network_if_needed()
            
        # Add a flag to the request indicating if we're offline
        request.is_offline = not is_network_available()
        
        # Get response from the next middleware/view
        response = self.get_response(request)
        
        # Add a header to indicate network status
        if hasattr(response, 'headers'):
            response.headers['X-Network-Status'] = 'offline' if not is_network_available() else 'online'
        
        return response
    
    async def __acall__(self, request):
        """Handle asynchronous requests"""
        # Check network status periodically
        self._check_network_if_needed()
        
        # Add a flag to the request indicating if we're offline
        request.is_offline = not is_network_available()
        
        # Get response from the next middleware/view
        response = await self.get_response(request)
        
        # Add a header to indicate network status
        if hasattr(response, 'headers'):
            response.headers['X-Network-Status'] = 'offline' if not is_network_available() else 'online'
        
        return response
    
    def _check_network_if_needed(self):
        """Check network status if enough time has passed since last check"""
        current_time = time.time()
        if current_time - self.last_check_time > self.check_interval:
            check_network_status()
            self.last_check_time = current_time 