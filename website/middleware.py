"""
Custom middleware for BLT application.
"""
import logging
import re
from datetime import timedelta

from django.contrib import messages
from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from website.models import Organization, UserActivity

logger = logging.getLogger(__name__)


def anonymize_ip(ip_address):
    """
    Anonymize IP address for GDPR compliance.
    IPv4: Masks last octet (192.168.1.100 -> 192.168.1.0)
    IPv6: Masks last 80 bits (2001:db8::1 -> 2001:db8::)
    """
    if not ip_address:
        return None

    try:
        from ipaddress import ip_address as parse_ip

        ip_obj = parse_ip(ip_address)

        if ip_obj.version == 4:
            # Mask last octet
            parts = str(ip_obj).split(".")
            parts[-1] = "0"
            return ".".join(parts)
        else:
            # Mask last 80 bits (keep first 48 bits)
            from ipaddress import IPv6Address

            masked = int(ip_obj) & ((2**48 - 1) << 80)
            return str(IPv6Address(masked))
    except Exception:
        return None


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

                    # Build unique cache key
                    org_id = organization.id if organization else "none"
                    cache_key = f"dashboard_visit:{request.user.id}:{org_id}:{request.path}"

                    # Fast path: Check cache first (works with single worker)
                    if cache.get(cache_key):
                        # Already tracked recently, skip
                        pass
                    else:
                        # Slow path: Check DB for reliability across workers
                        one_minute_ago = timezone.now() - timedelta(minutes=1)

                        dedup_filter = {
                            "user": request.user,
                            "activity_type": "dashboard_visit",
                            "timestamp__gte": one_minute_ago,
                            "metadata__path": request.path,
                        }

                        if organization is not None:
                            dedup_filter["organization"] = organization

                        recent_visit = UserActivity.objects.filter(**dedup_filter).exists()

                        if not recent_visit:
                            # Extract and anonymize IP address for GDPR compliance
                            raw_ip = self._get_client_ip(request)
                            ip_address = anonymize_ip(raw_ip)

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

                            # Set cache for 60 seconds (performance optimization)
                            cache.set(cache_key, True, 60)
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
        """Extract client IP address from request."""
        # Check if behind a trusted proxy (Django SECURE_PROXY_SSL_HEADER is configured)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Get the first IP in the chain (actual client IP)
            # X-Forwarded-For format: "client_ip, proxy1_ip, proxy2_ip"
            ip = x_forwarded_for.split(",")[0].strip()
            return ip
        # Fallback to REMOTE_ADDR if not behind proxy
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
