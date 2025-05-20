"""
Throttling middleware for limiting request rates to the website.
"""
import functools
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django_ratelimit.core import get_usage, is_ratelimited
from django_ratelimit.utils import _ACCESSOR_KEYS, _SIMPLE_KEYS, get_client_ip


class ThrottlingMiddleware:
    """
    Middleware to apply rate limiting to all requests.
    
    This throttles based on:
    - IP address for anonymous users
    - User ID for authenticated users
    - Different rates for staff/superusers
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Default rates if not specified in settings
        self.rate_anon = getattr(settings, 'RATELIMIT_RATE_ANON', '100/minute')
        self.rate_user = getattr(settings, 'RATELIMIT_RATE_USER', '300/minute')
        self.rate_staff = getattr(settings, 'RATELIMIT_RATE_STAFF', '1000/minute')
        self.block = getattr(settings, 'RATELIMIT_BLOCK', True)
        self.METHODS = getattr(settings, 'RATELIMIT_METHODS', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])

    def __call__(self, request):
        # Skip throttling for admin URLs
        if request.path.startswith(f'/{settings.ADMIN_URL}/'):
            return self.get_response(request)
            
        if request.method not in self.METHODS:
            return self.get_response(request)

        # Determine rate limit based on user type
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                rate = self.rate_staff
                key = f'user:{request.user.id}'
            else:
                rate = self.rate_user
                key = f'user:{request.user.id}'
        else:
            rate = self.rate_anon
            key = f'ip:{get_client_ip(request)[0]}'

        # Check rate limit
        limited = is_ratelimited(
            request=request,
            group=None,
            key=key,
            rate=rate,
            method=request.method,
            increment=True,
        )

        if limited and self.block:
            return HttpResponseTooManyRequests(_("Request was throttled. Please try again later."))

        return self.get_response(request)