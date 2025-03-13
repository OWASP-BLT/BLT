import os
import json
import traceback
import logging
from django.http import HttpResponse
from django.conf import settings
from website.cache_utils import CACHE_DIR

logger = logging.getLogger(__name__)

class ApiCacheFallbackMiddleware:
    """
    Middleware to catch exceptions in API requests and serve cached content
    when possible.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process the request
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # Only attempt to serve cached content for API endpoints
            if not (request.path.startswith('/api/') or 
                    request.path.startswith('/auth/') or
                    'format=json' in request.get_full_path() or
                    '/rest-auth/' in request.path):
                # Re-raise the exception for non-API routes
                raise
            
            logger.warning(f"API error occurred: {str(e)}. Attempting to serve cached content.")
            return self.serve_cached_content(request, e)
    
    def serve_cached_content(self, request, exception):
        """
        Attempt to serve cached content for the request
        """
        cache_key = f"api_cache:{request.get_full_path()}"
        cache_file_path = os.path.join(CACHE_DIR, f"{cache_key.replace(':', '_').replace('/', '_')}.json")
        
        if os.path.exists(cache_file_path):
            try:
                with open(cache_file_path, 'rb') as f:
                    content = f.read()
                    logger.info(f"Serving cached content for {request.get_full_path()}")
                    return HttpResponse(
                        content=content,
                        status=200,
                        content_type='application/json',
                        headers={
                            'X-Served-From-Cache': 'true',
                            'X-Cache-Reason': 'network_error'
                        }
                    )
            except Exception as cache_error:
                logger.error(f"Failed to serve cached content: {str(cache_error)}")
        
        # If we couldn't serve cached content, return an error response
        error_data = {
            'error': 'Network Error',
            'message': 'Unable to process request due to a network error. No cached data available.',
            'status': 503
        }
        
        return HttpResponse(
            content=json.dumps(error_data),
            status=503,
            content_type='application/json'
        ) 