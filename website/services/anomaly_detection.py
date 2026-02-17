import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from website.models import UserBehaviorAnomaly, UserLoginEvent

logger = logging.getLogger(__name__)

# Default thresholds (read live from settings inside functions for @override_settings support)
_DEFAULTS = {
    "ANOMALY_IP_LOOKBACK_DAYS": 30,
    "ANOMALY_UNUSUAL_HOUR_START": 1,
    "ANOMALY_UNUSUAL_HOUR_END": 5,
    "ANOMALY_RAPID_FAILURE_COUNT": 5,
    "ANOMALY_RAPID_FAILURE_WINDOW_MINUTES": 15,
}


def _setting(name):
    return getattr(settings, name, _DEFAULTS[name])


def check_login_anomalies(user, login_event):
    """Run anomaly checks after a successful login."""
    if user is None:
        return

    cutoff = timezone.now() - timedelta(days=_setting("ANOMALY_IP_LOOKBACK_DAYS"))
    prior_events = UserLoginEvent.objects.filter(
        user=user,
        event_type=UserLoginEvent.EventType.LOGIN,
        timestamp__gte=cutoff,
    ).exclude(pk=login_event.pk)

    # Only run checks if the user has prior login history
    if not prior_events.exists():
        return

    _check_new_ip(user, login_event, prior_events)
    _check_new_user_agent(user, login_event, prior_events)
    _check_unusual_time(user, login_event)


def check_failed_login_anomalies(user, failed_event):
    """Run anomaly checks after a failed login attempt."""
    if user is None:
        return

    _check_rapid_failures(user, failed_event)


def _check_new_ip(user, login_event, prior_events):
    """Flag logins from an IP address not seen in the lookback window."""
    if not login_event.ip_address:
        return

    known_ips = set(prior_events.exclude(ip_address__isnull=True).values_list("ip_address", flat=True).distinct())

    if login_event.ip_address not in known_ips:
        UserBehaviorAnomaly.objects.create(
            user=user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description=f"Login from new IP address: {login_event.ip_address}",
            details={
                "new_ip": login_event.ip_address,
                "known_ips": list(known_ips)[:10],
            },
            login_event=login_event,
        )


def _check_new_user_agent(user, login_event, prior_events):
    """Flag logins from a user agent string not seen before."""
    if not login_event.user_agent:
        return

    known_uas = set(prior_events.exclude(user_agent="").values_list("user_agent", flat=True).distinct())

    if login_event.user_agent not in known_uas:
        UserBehaviorAnomaly.objects.create(
            user=user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_UA,
            severity=UserBehaviorAnomaly.Severity.LOW,
            description="Login from new device or browser",
            details={
                "new_ua": login_event.user_agent[:200],
            },
            login_event=login_event,
        )


def _check_unusual_time(user, login_event):
    """Flag logins during unusual hours (UTC)."""
    hour = login_event.timestamp.hour
    start = _setting("ANOMALY_UNUSUAL_HOUR_START")
    end = _setting("ANOMALY_UNUSUAL_HOUR_END")
    if start <= hour < end:
        UserBehaviorAnomaly.objects.create(
            user=user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.UNUSUAL_TIME,
            severity=UserBehaviorAnomaly.Severity.LOW,
            description=f"Login at unusual hour: {hour}:00 UTC",
            details={
                "login_hour_utc": hour,
            },
            login_event=login_event,
        )


def _check_rapid_failures(user, failed_event):
    """Flag accounts with many failed login attempts in a short window."""
    window_minutes = _setting("ANOMALY_RAPID_FAILURE_WINDOW_MINUTES")
    failure_threshold = _setting("ANOMALY_RAPID_FAILURE_COUNT")
    window_start = timezone.now() - timedelta(minutes=window_minutes)

    recent_failures = UserLoginEvent.objects.filter(
        user=user,
        event_type=UserLoginEvent.EventType.FAILED,
        timestamp__gte=window_start,
    ).count()

    if recent_failures < failure_threshold:
        return

    # Deduplicate: don't create another alert if one already exists in this window
    existing = UserBehaviorAnomaly.objects.filter(
        user=user,
        anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
        created_at__gte=window_start,
    ).exists()

    if existing:
        return

    UserBehaviorAnomaly.objects.create(
        user=user,
        anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
        severity=UserBehaviorAnomaly.Severity.HIGH,
        description=f"{recent_failures} failed login attempts in {window_minutes} minutes",
        details={
            "failure_count": recent_failures,
            "window_minutes": window_minutes,
            "ip_address": failed_event.ip_address,
        },
        login_event=failed_event,
    )
