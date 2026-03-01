import ipaddress
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from website.models import Organization, UserLoginEvent
from website.services.anomaly_detection import check_failed_login_anomalies, check_login_anomalies

logger = logging.getLogger(__name__)


def _normalize_ip(value):
    """Validate and normalize an IP address string, returning None for invalid values."""
    try:
        return str(ipaddress.ip_address((value or "").strip()))
    except ValueError:
        return None


def _get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For only behind trusted proxies."""
    if request is None:
        return None
    if getattr(settings, "USE_X_FORWARDED_FOR", False):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return _normalize_ip(forwarded_for.split(",")[0])
    return _normalize_ip(request.META.get("REMOTE_ADDR"))


def _get_user_agent(request):
    """Extract user agent string from the request (truncated to 512 chars)."""
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT", "") or "")[:512]


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
    ip = _get_client_ip(request)
    ua = _get_user_agent(request)
    orgs = _get_user_orgs_with_monitoring(user)

    for org in orgs:
        try:
            event = UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=user.username,
                event_type=UserLoginEvent.EventType.LOGIN,
                ip_address=ip,
                user_agent=ua,
            )
            check_login_anomalies(user, event, organization=org)
        except Exception:
            logger.exception("Error recording login event for org %s", org.id)

    try:
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
        logger.exception("Error recording global login event")


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Record logout event."""
    if user is None:
        return
    ip = _get_client_ip(request)
    ua = _get_user_agent(request)
    orgs = _get_user_orgs_with_monitoring(user)

    for org in orgs:
        try:
            UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=user.username,
                event_type=UserLoginEvent.EventType.LOGOUT,
                ip_address=ip,
                user_agent=ua,
            )
        except Exception:
            logger.exception("Error recording logout event for org %s", org.id)

    try:
        UserLoginEvent.objects.create(
            user=user,
            username_attempted=user.username,
            event_type=UserLoginEvent.EventType.LOGOUT,
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        logger.exception("Error recording global logout event")


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Record failed login attempt and run anomaly checks."""
    username = str((credentials or {}).get("username", "") or "")
    User = get_user_model()
    user = User.objects.filter(username=username).first()

    ip = _get_client_ip(request)
    ua = _get_user_agent(request)
    orgs = _get_user_orgs_with_monitoring(user)

    for org in orgs:
        try:
            event = UserLoginEvent.objects.create(
                user=user,
                organization=org,
                username_attempted=username[:150],
                event_type=UserLoginEvent.EventType.FAILED,
                ip_address=ip,
                user_agent=ua,
            )
            check_failed_login_anomalies(user, event, organization=org)
        except Exception:
            logger.exception("Error recording failed login event for org %s", org.id)

    try:
        event = UserLoginEvent.objects.create(
            user=user,
            username_attempted=username[:150],
            event_type=UserLoginEvent.EventType.FAILED,
            ip_address=ip,
            user_agent=ua,
        )
        check_failed_login_anomalies(user, event)
    except Exception:
        logger.exception("Error recording global failed login event")


def anonymize_login_events_on_user_delete(sender, instance, **kwargs):
    """Anonymize PII in login events when a user is deleted (GDPR compliance)."""
    UserLoginEvent.objects.filter(user=instance).update(
        username_attempted="[deleted]",
        ip_address=None,
        user_agent="",
    )


# Connect pre_delete to the User model.
# Safe because this module is imported during AppConfig.ready().
pre_delete.connect(anonymize_login_events_on_user_delete, sender=get_user_model())
