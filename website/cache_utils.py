import json
import os
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse
import requests

# Default cache timeout (12 hours)
DEFAULT_CACHE_TIMEOUT = 12 * 60 * 60

# Create cache directory if it doesn't exist
CACHE_DIR = getattr(settings, 'API_CACHE_DIR', os.path.join(settings.MEDIA_ROOT, 'api_cache'))
IMAGE_CACHE_DIR = os.path.join(CACHE_DIR, 'images')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Flag to track network availability
network_available = True

def check_network_status():
    """
    Check if network is available by making a request to a reliable domain
    """
    global network_available
    try:
        # Use a reliable service to check internet connectivity
        response = requests.get('https://www.google.com', timeout=2)
        network_available = response.status_code == 200
    except:
        network_available = False
    return network_available

def cache_api_response(timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Decorator to cache API responses
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            global network_available
            
            # Only cache GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)

            # Generate cache key based on the full URL path and query params
            cache_key = f"api_cache:{request.get_full_path()}"
            
            # Periodically check network status (don't do this on every request)
            if getattr(request, '_network_checked', False) is False:
                check_network_status()
                request._network_checked = True
            
            # Try to get the response from cache
            cached_response = cache.get(cache_key)
            
            # If the network is not available, try to serve from cache immediately
            if not network_available:
                # Try in-memory cache first
                if cached_response is not None:
                    return HttpResponse(
                        content=cached_response.get('content'),
                        status=cached_response.get('status_code', 200),
                        content_type=cached_response.get('content_type', 'application/json')
                    )
                
                # Then try file cache
                cache_file_path = os.path.join(CACHE_DIR, f"{cache_key.replace(':', '_').replace('/', '_')}.json")
                if os.path.exists(cache_file_path):
                    with open(cache_file_path, 'rb') as f:
                        content = f.read()
                        return HttpResponse(
                            content=content,
                            status=200,
                            content_type='application/json'
                        )
            
            # If we have a cached response and it's not expired, use it
            if cached_response is not None:
                # Return cached response
                return HttpResponse(
                    content=cached_response.get('content'),
                    status=cached_response.get('status_code', 200),
                    content_type=cached_response.get('content_type', 'application/json')
                )
            
            try:
                # Get the actual response
                response = view_func(request, *args, **kwargs)
                
                # Only cache successful responses
                if 200 <= response.status_code < 300:
                    cache_data = {
                        'content': response.content,
                        'status_code': response.status_code,
                        'content_type': response.get('Content-Type', 'application/json'),
                        'cached_at': datetime.now().isoformat()
                    }
                    
                    # Cache the response
                    cache.set(cache_key, cache_data, timeout)
                    
                    # Also save to file system for persistent caching
                    cache_file_path = os.path.join(CACHE_DIR, f"{cache_key.replace(':', '_').replace('/', '_')}.json")
                    with open(cache_file_path, 'wb') as f:
                        f.write(response.content)
                
                return response
            except Exception as e:
                # Network error occurred - mark network as unavailable
                network_available = False
                
                # Try to load from memory cache
                cached_response = cache.get(cache_key)
                if cached_response is not None:
                    return HttpResponse(
                        content=cached_response.get('content'),
                        status=cached_response.get('status_code', 200),
                        content_type=cached_response.get('content_type', 'application/json')
                    )
                
                # Try to load from file cache
                cache_file_path = os.path.join(CACHE_DIR, f"{cache_key.replace(':', '_').replace('/', '_')}.json")
                if os.path.exists(cache_file_path):
                    with open(cache_file_path, 'rb') as f:
                        content = f.read()
                        return HttpResponse(
                            content=content,
                            status=200,
                            content_type='application/json'
                        )
                        
                # If all else fails, raise the exception
                raise e
                
        return _wrapped_view
    return decorator


def get_cached_image(url, max_age=DEFAULT_CACHE_TIMEOUT, force_cache=False):
    """
    Fetch and cache an image from a URL.
    Returns the local cached path or the original URL if caching fails.
    
    Parameters:
    - url: The image URL to fetch
    - max_age: Maximum age of the cached image in seconds
    - force_cache: Force using cache even if it's expired (useful for offline mode)
    """
    global network_available
    
    if not url:
        return url
    
    try:
        # Parse URL to get filename
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        if not filename:
            # Generate a filename if URL doesn't have one
            filename = f"{hash(url)}.jpg"
        
        # Create cache path
        cache_path = os.path.join(IMAGE_CACHE_DIR, filename)
        local_url = default_storage.url(os.path.join('api_cache/images', filename))
        
        # Check if we should use the network
        if not network_available or force_cache:
            # If network is unavailable, use cached image if it exists
            if os.path.exists(cache_path):
                return local_url
            # If no cached version exists, return the original URL and hope for the best
            return url
        
        # Check if file exists and is not expired
        if os.path.exists(cache_path):
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age < max_age:
                # Return the cached file URL
                return local_url
        
        # Fetch the image
        response = requests.get(url, stream=True, timeout=5)
        if response.status_code == 200:
            # Save to cache
            path = default_storage.save(
                os.path.join('api_cache/images', filename),
                ContentFile(response.content)
            )
            return default_storage.url(path)
    
    except Exception as e:
        # Network error occurred - mark network as unavailable
        network_available = False
        
        # If any error occurs during caching, check if we have a cached version
        cache_path = os.path.join(IMAGE_CACHE_DIR, filename)
        if os.path.exists(cache_path):
            return default_storage.url(os.path.join('api_cache/images', filename))
    
    return url


def cache_images_in_response(data, force_cache=False):
    """
    Recursively processes API response data and caches any image URLs found
    
    Parameters:
    - data: The API response data
    - force_cache: Force using cache even if it's expired (useful for offline mode)
    """
    global network_available
    
    # Check if we're in offline mode
    force_cache = force_cache or not network_available
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Check if the field might contain an image URL
            if isinstance(value, str) and any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                data[key] = get_cached_image(value, force_cache=force_cache)
            elif isinstance(value, (dict, list)):
                cache_images_in_response(value, force_cache=force_cache)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                cache_images_in_response(item, force_cache=force_cache)
    
    return data

def is_network_available():
    """
    Public function to check if network is available
    """
    global network_available
    
    # Don't check too frequently - only check if it's been a while
    if hasattr(is_network_available, 'last_check'):
        if time.time() - is_network_available.last_check < 60:  # Only check once per minute
            return network_available
    
    is_network_available.last_check = time.time()
    return check_network_status() 