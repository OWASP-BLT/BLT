"""
Custom middleware for BLT application.
"""
import logging
import re
from datetime import timedelta

from django.contrib import messages
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from website.models import Organization, UserActivity

logger = logging.getLogger(__name__)


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
            provider = message_data.get("provider", "GitHub")
            is_signup = message_data.get("is_signup", False)

            if is_signup:
                messages.success(
                    request, f"Welcome to BLT! You earned 10 BACON tokens for signing up with {provider.capitalize()}."
                )
            else:
                messages.success(
                    request, f"Successfully connected {provider.capitalize()}! You earned 10 BACON tokens."
                )

            # Clear the cache flag after displaying message
            cache.delete(message_cache_key)

        return None


class ActivityTrackingMiddleware(MiddlewareMixin):
    """Middleware to track user dashboard visits for behavior analytics."""

    def __call__(self, request):
        # Track dashboard visits for authenticated users
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                # Check if this is an organization dashboard visit
                if self._is_dashboard_visit(request.path):
                    organization = self._get_organization_from_request(request)

                    # Deduplication: Check if user visited this dashboard in the last minute
                    one_minute_ago = timezone.now() - timedelta(minutes=1)
                    recent_visit = UserActivity.objects.filter(
                        user=request.user,
                        organization=organization,
                        activity_type="dashboard_visit",
                        timestamp__gte=one_minute_ago,
                        metadata__path=request.path,
                    ).exists()

                    # Only create activity if no recent visit exists
                    if not recent_visit:
                        # Extract IP address
                        ip_address = self._get_client_ip(request)

                        # Extract user agent
                        user_agent = request.META.get("HTTP_USER_AGENT", "")

                        # Create activity record
                        UserActivity.objects.create(
                            user=request.user,
                            organization=organization,
                            activity_type="dashboard_visit",
                            ip_address=ip_address,
                            user_agent=user_agent,
                            metadata={"path": request.path},
                        )
            except Exception as e:
                # Silent failure - don't break the request
                logger.debug("Failed to track dashboard visit: %s", type(e).__name__, exc_info=True)

        response = self.get_response(request)
        return response

    def _is_dashboard_visit(self, path):
        """Check if the path is an organization dashboard URL."""
        # Match organization dashboard patterns
        dashboard_patterns = [
            r"^/organization/\d+/dashboard",
            r"^/company/\d+/dashboard",
        ]
        return any(re.match(pattern, path) for pattern in dashboard_patterns)

    def _get_client_ip(self, request):
        """Extract client IP address from request (trusted proxy only)."""
        # Only use X-Forwarded-For if behind trusted proxy
        # Otherwise use REMOTE_ADDR directly
        return request.META.get("REMOTE_ADDR")

    def _get_organization_from_request(self, request):
        """Try to extract organization from request path or session."""
        try:
            # Try to extract organization ID from URL path
            match = re.search(r"/(?:organization|company)/(\d+)/", request.path)
            if match:
                org_id = int(match.group(1))
                return Organization.objects.filter(id=org_id).first()

            # Try to get from session
            org_ref = request.session.get("org_ref")
            if org_ref:
                return Organization.objects.filter(id=org_ref).first()
        except Exception as e:
            # Silent failure - don't break the request
            logger.debug("Failed to track dashboard visit: %s", type(e).__name__, exc_info=True)

        return None
