"""
Custom middleware for BLT application.
"""

from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class BaconRewardMessageMiddleware(MiddlewareMixin):
    """
    Middleware to show BACON reward messages after social auth redirect.
    
    Since allauth redirects after social login/signup, we store flags in the session
    and show the messages on the next request.
    """

    def process_request(self, request):
        """
        Check for pending BACON reward messages and display them.
        
        Messages are stored in cache by signal handlers because Django messages
        don't persist reliably across OAuth redirects. This middleware checks
        the cache and displays the appropriate success message.
        """
        from django.core.cache import cache
        
        if not request.user.is_authenticated:
            return None

        # Check cache for message flag (set by signal handlers)
        message_cache_key = f"show_bacon_message_{request.user.id}"
        message_data = cache.get(message_cache_key)
        
        if message_data:
            provider = message_data.get('provider', 'GitHub')
            is_signup = message_data.get('is_signup', False)
            
            if is_signup:
                messages.success(
                    request,
                    f"Welcome to BLT! You earned 10 BACON tokens for signing up with {provider.capitalize()}."
                )
            else:
                messages.success(
                    request,
                    f"Successfully connected {provider.capitalize()}! You earned 10 BACON tokens."
                )
            
            # Clear the cache flag after displaying message
            cache.delete(message_cache_key)

        return None
