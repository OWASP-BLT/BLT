import logging

from django.conf import settings
from django.http import HttpResponsePermanentRedirect

logger = logging.getLogger(__name__)


class DomainMiddleware:
    """
    Middleware to handle domain-related functionality, including:

    1. Redirecting from staging domain to production domain when enabled
    2. Any future domain-related processing
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle staging to production redirect
        redirect_response = self.handle_staging_redirect(request)
        if redirect_response:
            return redirect_response

        # Continue with the normal request processing
        return self.get_response(request)

    def handle_staging_redirect(self, request):
        """
        Check if the request is coming to the staging domain and redirect
        to the production domain if staging redirect is enabled.

        Returns:
            HttpResponsePermanentRedirect if redirect should happen
            None otherwise
        """
        # Get the host without port number
        host = request.get_host().split(":")[0]

        # Check if redirect is enabled and we're on the staging domain
        if settings.ENABLE_STAGING_REDIRECT and host == settings.STAGING_DOMAIN and host != settings.PRODUCTION_DOMAIN:
            # Build the full URL for the redirect
            scheme = request.META.get("wsgi.url_scheme", "https")  # Default to https if not specified
            path = request.get_full_path()
            new_url = f"{scheme}://{settings.PRODUCTION_DOMAIN}{path}"

            logger.info(f"Redirecting from staging {host} to production {settings.PRODUCTION_DOMAIN}")

            # Return a permanent redirect to the production domain
            return HttpResponsePermanentRedirect(new_url)

        return None
