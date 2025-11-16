import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

logger = logging.getLogger("throttling_middleware")


class ThrottlingMiddleware:
    THROTTLE_LIMITS = getattr(
        settings,
        "THROTTLE_LIMITS",
        {
            "GET": 100,
            "POST": 50,
            "OTHER": 30,
        },
    )
    THROTTLE_WINDOW = getattr(settings, "THROTTLE_WINDOW", 60)
    EXEMPT_PATHS = getattr(settings, "THROTTLE_EXEMPT_PATHS", ["/admin/", "/static/", "/media/"])

    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("ThrottlingMiddleware initialized with limits: %s", self.THROTTLE_LIMITS)

    def __call__(self, request):
        ip = self.get_client_ip(request)
        method = request.method
        path = request.path
        logger.debug("Processing request: %s %s from IP: %s", method, path, ip)

        if self.should_skip_throttle(request):
            logger.debug("Skipping throttling for %s %s (exempt path or DRF view)", method, path)
            return self.get_response(request)

        if self.is_throttled(request):
            logger.warning("Request throttled: %s %s from IP: %s (limit exceeded)", method, path, ip)
            response = HttpResponse("Too many requests. Please try again later.", status=429)
            response["Retry-After"] = str(self.THROTTLE_WINDOW)
            return response

        logger.debug("Request allowed: %s %s from IP: %s", method, path, ip)
        return self.get_response(request)

    def should_skip_throttle(self, request):
        """Check if request should be exempt from throttling."""
        # Skip throttling during tests
        if getattr(settings, "IS_TEST", False) or getattr(settings, "TESTING", False):
            logger.debug("Skipping throttling for test mode")
            return True
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            logger.debug("Skipping exempt path: %s", request.path)
            return True

        if not hasattr(request, "resolver_match") or request.resolver_match is None:
            logger.debug("No resolver_match for path: %s", request.path)
            return False

        try:
            callback = request.resolver_match.func
            view_class = getattr(callback, "cls", None)

            # DRF class-based view
            if view_class and (issubclass(view_class, APIView) or issubclass(view_class, ViewSet)):
                logger.debug("Skipping DRF APIView: %s", request.path)
                return True

            # DRF function-based @api_view
            if hasattr(callback, "cls") and getattr(callback.cls, "is_api_view", False):
                logger.debug("Skipping DRF @api_view: %s", request.path)
                return True

        except Exception as e:
            logger.debug("View detection error for %s: %s", request.path, str(e))

        return False

    def is_throttled(self, request):
        """Check if the request should be throttled (sliding window)."""
        ip = self.get_client_ip(request)
        method = request.method
        limit = self.THROTTLE_LIMITS.get(method, self.THROTTLE_LIMITS["OTHER"])

        cache_key = f"throttle_{ip}_{method}"
        current_count = cache.get(cache_key, 0)

        logger.debug(
            "Throttle check for %s %s from IP: %s - Current: %d/%d", method, request.path, ip, current_count, limit
        )

        if current_count >= limit:
            logger.warning(
                "Rate limit exceeded for %s requests from IP: %s - Count: %d/%d", method, ip, current_count, limit
            )
            return True

        # Use get_or_set for atomic initialization
        cache.get_or_set(cache_key, 0, timeout=self.THROTTLE_WINDOW)

        try:
            new_count = cache.incr(cache_key)
            logger.debug(
                "Incremented throttle counter for %s from IP: %s - New count: %d/%d", method, ip, new_count, limit
            )
        except ValueError:
            # Handle case where key expired between get_or_set and incr
            cache.set(cache_key, 1, timeout=self.THROTTLE_WINDOW)
            new_count = 1
            logger.debug("Re-initialized throttle counter for %s from IP: %s after expiration", method, ip)

        return False

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
            # Handle empty string after strip
            if not ip:
                ip = request.META.get("REMOTE_ADDR")
        else:
            ip = request.META.get("REMOTE_ADDR")

        # Log IP extraction for debugging
        if x_forwarded_for:
            logger.debug("Extracted IP from X-Forwarded-For: %s (original: %s)", ip, x_forwarded_for)
        else:
            logger.debug("Using REMOTE_ADDR for IP: %s", ip)

        return ip
