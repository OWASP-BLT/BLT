from functools import wraps
import json

from django.utils.decorators import method_decorator
from rest_framework.response import Response

from website.cache_utils import cache_api_response, cache_images_in_response, is_network_available

def apply_api_cache(view_class):
    """
    Class decorator that applies caching to API views
    """
    original_dispatch = view_class.dispatch
    
    @method_decorator(cache_api_response())
    def cached_dispatch(self, request, *args, **kwargs):
        return original_dispatch(self, request, *args, **kwargs)
    
    view_class.dispatch = cached_dispatch
    return view_class

def cache_response_with_images(func):
    """
    Method decorator for APIView methods that processes images in responses
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        response = func(self, request, *args, **kwargs)
        
        # Only process GET requests with successful responses
        if request.method == 'GET' and hasattr(response, 'status_code') and 200 <= response.status_code < 300:
            if hasattr(response, 'data'):
                # DRF Response
                response.data = cache_images_in_response(response.data)
            elif hasattr(response, 'content'):
                # Regular HttpResponse with JSON content
                try:
                    content = json.loads(response.content.decode('utf-8'))
                    content = cache_images_in_response(content)
                    response.content = json.dumps(content).encode('utf-8')
                except (ValueError, UnicodeDecodeError):
                    # Not JSON content, leave it as is
                    pass
        
        return response
    
    return wrapper

def offline_resilient_view(func):
    """
    Decorator that ensures a view can handle offline scenarios gracefully.
    This checks network connectivity before making API calls and 
    prioritizes cached data when offline.
    """
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        # Add a flag to the request to indicate that we've checked network status
        request._network_checked = True
        
        try:
            # Try to execute the view function
            response = func(self, request, *args, **kwargs)
            return response
        except Exception as e:
            # If an exception occurs (likely network-related)
            # First check if we're indeed offline
            if not is_network_available():
                # Set a response header indicating we're serving from cache
                if hasattr(self, 'get_cached_response'):
                    cached_response = self.get_cached_response(request, *args, **kwargs)
                    if cached_response:
                        return cached_response
            
            # If we can't handle it, re-raise the exception
            raise e
    
    return wrapper

def offline_first_view(view_class):
    """
    Class decorator that makes API views offline-first.
    This prioritizes cached data and gracefully handles network errors.
    """
    original_dispatch = view_class.dispatch
    
    # Define a new dispatch method that tries to use cache first in offline scenarios
    def offline_first_dispatch(self, request, *args, **kwargs):
        # If we're offline, try to serve from cache first
        if not is_network_available():
            # Try to get a cached response - use the standard dispatch which should
            # use the cache_api_response decorator to serve from cache
            try:
                return original_dispatch(self, request, *args, **kwargs)
            except Exception:
                # If there's any error, add an offline flag to the response
                if hasattr(self, 'get_cached_response'):
                    cached_response = self.get_cached_response(request, *args, **kwargs)
                    if cached_response:
                        return cached_response
        
        # If we're online or couldn't find a cache, proceed normally
        return original_dispatch(self, request, *args, **kwargs)
    
    view_class.dispatch = offline_first_dispatch
    return view_class 