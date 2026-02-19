import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models import Q
from django.dispatch import receiver

from website.models import Organization, UserLoginEvent
from website.services.anomaly_detection import check_failed_login_anomalies, check_login_anomalies

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For only behind trusted proxies."""
    if request is None:
        return None
    if getattr(settings, "USE_X_FORWARDED_FOR", False):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request):
    """Extract user agent string from the request."""
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


def _get_user_orgs_with_monitoring(user):
    """Return orgs where user is admin or manager and monitoring is enabled."""
    if user is None:
        return Organization.objects.none()
    return Organization.objects.filter(
        Q(admin=user) | Q(managers=user),
        security_monitoring_enabled=True,
    ).distinct()


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Record successful login and run anomaly checks."""
    try:
        ip = _get_client_ip(request)
        ua = _get_user_agent(request)
        orgs = _get_user_orgs_with_monitoring(user)

        for org in orgs:
            event = UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=user.username,
                event_type=UserLoginEvent.EventType.LOGIN,
                ip_address=ip,
                user_agent=ua,
            )
            check_login_anomalies(user, event, organization=org)

        # Global event (no org) for backward compat with site-wide dashboard
        event = UserLoginEvent.objects.create(
            user=user,
            username_attempted=user.username,
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address=ip,
            user_agent=ua,
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
        ip = _get_client_ip(request)
        ua = _get_user_agent(request)
        orgs = _get_user_orgs_with_monitoring(user)

        for org in orgs:
            UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=user.username,
                event_type=UserLoginEvent.EventType.LOGOUT,
                ip_address=ip,
                user_agent=ua,
            )

        UserLoginEvent.objects.create(
            user=user,
            username_attempted=user.username,
            event_type=UserLoginEvent.EventType.LOGOUT,
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        logger.exception("Error recording logout event")


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Record failed login attempt and run anomaly checks."""
    try:
        username = credentials.get("username", "")
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(username=username).first()

        ip = _get_client_ip(request)
        ua = _get_user_agent(request)
        orgs = _get_user_orgs_with_monitoring(user)

        for org in orgs:
            event = UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=username[:150],
                event_type=UserLoginEvent.EventType.FAILED,
                ip_address=ip,
                user_agent=ua,
            )
            check_failed_login_anomalies(user, event, organization=org)

        event = UserLoginEvent.objects.create(
            user=user,
            username_attempted=username[:150],
            event_type=UserLoginEvent.EventType.FAILED,
            ip_address=ip,
            user_agent=ua,
        )
        check_failed_login_anomalies(user, event)
    except Exception:
        logger.exception("Error recording failed login event")
