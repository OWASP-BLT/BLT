"""
Helper utilities for loading models dynamically.
This allows Sizzle to work with different Django projects that may have different model structures.
"""
import logging

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def get_slack_integration_model():
    """
    Get the SlackIntegration model configured in settings.
    Returns None if not configured or not available.
    """
    from sizzle.conf import SIZZLE_SLACK_INTEGRATION_MODEL

    if not SIZZLE_SLACK_INTEGRATION_MODEL:
        return None

    try:
        app_label, model_name = SIZZLE_SLACK_INTEGRATION_MODEL.split(".")
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError) as e:
        logger.warning(
            f"SIZZLE_SLACK_INTEGRATION_MODEL refers to model "
            f'"{SIZZLE_SLACK_INTEGRATION_MODEL}" that has not been installed. '
            f"Slack integration will be disabled. Error: {e}"
        )
        return None


def get_organization_model():
    """
    Get the Organization model configured in settings.
    Returns None if not configured or not available.
    """
    from sizzle.conf import SIZZLE_ORGANIZATION_MODEL

    if not SIZZLE_ORGANIZATION_MODEL:
        return None

    try:
        app_label, model_name = SIZZLE_ORGANIZATION_MODEL.split(".")
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError) as e:
        logger.warning(
            f"SIZZLE_ORGANIZATION_MODEL refers to model "
            f'"{SIZZLE_ORGANIZATION_MODEL}" that has not been installed. '
            f"Organization features will be limited. Error: {e}"
        )
        return None


def get_userprofile_model():
    """
    Get the UserProfile model configured in settings.
    Returns None if not configured or not available.
    """
    from sizzle.conf import SIZZLE_USERPROFILE_MODEL

    if not SIZZLE_USERPROFILE_MODEL:
        return None

    try:
        app_label, model_name = SIZZLE_USERPROFILE_MODEL.split(".")
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError) as e:
        logger.warning(
            f"SIZZLE_USERPROFILE_MODEL refers to model "
            f'"{SIZZLE_USERPROFILE_MODEL}" that has not been installed. '
            f"User profile features will be limited. Error: {e}"
        )
        return None


def get_notification_model():
    """
    Get the Notification model configured in settings.
    Returns None if not configured or not available.
    """
    from sizzle.conf import SIZZLE_NOTIFICATION_MODEL

    if not SIZZLE_NOTIFICATION_MODEL:
        return None

    try:
        app_label, model_name = SIZZLE_NOTIFICATION_MODEL.split(".")
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError) as e:
        logger.warning(
            f"SIZZLE_NOTIFICATION_MODEL refers to model "
            f'"{SIZZLE_NOTIFICATION_MODEL}" that has not been installed. '
            f"Notification features will be disabled. Error: {e}"
        )
        return None


def get_reminder_settings_model():
    """
    Get the ReminderSettings model from sizzle app.
    This is internal to sizzle and should always be available.
    """
    try:
        return apps.get_model("sizzle", "ReminderSettings")
    except LookupError as e:
        raise ImproperlyConfigured(
            f"Could not load ReminderSettings model from sizzle app. "
            f"Make sure sizzle migrations have been run. Error: {e}"
        )


def get_timelog_model():
    """
    Get the TimeLog model from sizzle app.
    This is internal to sizzle and should always be available.
    """
    try:
        return apps.get_model("sizzle", "TimeLog")
    except LookupError as e:
        raise ImproperlyConfigured(
            f"Could not load TimeLog model from sizzle app. " f"Make sure sizzle migrations have been run. Error: {e}"
        )


def check_slack_dependencies():
    """
    Check if Slack dependencies are available.
    Returns tuple (is_available, error_message)
    """
    try:
        from slack_bolt import App  # noqa
        from slack_sdk.web import WebClient  # noqa

        return True, None
    except ImportError as e:
        return False, f"slack-bolt not installed. Install with: pip install slack-bolt. Error: {e}"


def validate_model_configuration():
    """
    Validate that all required models are properly configured and available.
    Returns a dictionary with model availability status.
    """
    from sizzle.conf import SIZZLE_DAILY_CHECKINS_ENABLED, SIZZLE_EMAIL_REMINDERS_ENABLED, SIZZLE_SLACK_ENABLED

    status = {
        "slack_integration": None,
        "organization": None,
        "userprofile": None,
        "notification": None,
        "reminder_settings": None,
        "timelog": None,
        "slack_deps": None,
    }

    # Check core sizzle models
    try:
        status["reminder_settings"] = get_reminder_settings_model() is not None
        status["timelog"] = get_timelog_model() is not None
    except ImproperlyConfigured:
        status["reminder_settings"] = False
        status["timelog"] = False

    # Check optional models
    if SIZZLE_SLACK_ENABLED:
        status["slack_integration"] = get_slack_integration_model() is not None
        slack_available, _ = check_slack_dependencies()
        status["slack_deps"] = slack_available

    if SIZZLE_EMAIL_REMINDERS_ENABLED or SIZZLE_DAILY_CHECKINS_ENABLED:
        status["userprofile"] = get_userprofile_model() is not None

    if SIZZLE_DAILY_CHECKINS_ENABLED:
        status["notification"] = get_notification_model() is not None

    status["organization"] = get_organization_model() is not None

    return status
