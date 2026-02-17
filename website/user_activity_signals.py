import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from website.models import UserLoginEvent
from website.services.anomaly_detection import check_failed_login_anomalies, check_login_anomalies

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For for proxied requests."""
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request):
    """Extract user agent string from the request."""
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Record successful login and run anomaly checks."""
    try:
        event = UserLoginEvent.objects.create(
            user=user,
            username_attempted=user.username,
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
        check_login_anomalies(user, event)
    except Exception:
        logger.exception("Error recording login event")


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Record logout event."""
    try:
        if user is None:
            return
        UserLoginEvent.objects.create(
            user=user,
            username_attempted=user.username,
            event_type=UserLoginEvent.EventType.LOGOUT,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
    except Exception:
        logger.exception("Error recording logout event")


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Record failed login attempt and run anomaly checks."""
    try:
        username = credentials.get("username", "")
        # Try to find the user for anomaly tracking
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(username=username).first()

        event = UserLoginEvent.objects.create(
            user=user,
            username_attempted=username[:150],
            event_type=UserLoginEvent.EventType.FAILED,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
        )
        check_failed_login_anomalies(user, event)
    except Exception:
        logger.exception("Error recording failed login event")
