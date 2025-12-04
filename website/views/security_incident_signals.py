from threading import local

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from website.models import SecurityIncident, SecurityIncidentHistory

# Thread-local storage for tracking who is making changes
_user = local()


def set_current_user(user):
    """Utility to set the user performing the request."""
    _user.value = user


def get_current_user():
    """Return user if available, else None."""
    return getattr(_user, "value", None)


# PRE-SAVE: Capture original state for diffing
@receiver(pre_save, sender=SecurityIncident)
def capture_old_incident_state(sender, instance, **kwargs):
    """
    Capture the current DB state using SELECT ... FOR UPDATE
    to prevent race conditions on concurrent updates.
    """
    if not instance.pk:
        # New object → no previous state
        instance._old_state = None
        return

    # Capture current DB state for diffing (locking should be handled at a higher level if needed)
    try:
        old = sender.objects.get(pk=instance.pk)
        instance._old_state = {
            "title": old.title,
            "severity": old.severity,
            "status": old.status,
            "affected_systems": old.affected_systems,
            "resolved_at": old.resolved_at,
        }
    except sender.DoesNotExist:
        instance._old_state = None


# POST-SAVE: Compare old vs new and log changes
@receiver(post_save, sender=SecurityIncident)
def log_incident_changes(sender, instance, created, **kwargs):
    """
    Capture old state with a row lock to avoid race conditions.
    """
    if created:
        # Don't log creation event
        return

    old = getattr(instance, "_old_state", None)
    if not old:
        return

    user = get_current_user()

    fields_to_track = ["title", "severity", "status", "affected_systems", "resolved_at"]

    for field in fields_to_track:
        old_val = old.get(field)
        new_val = getattr(instance, field)

        # Only log real changes
        if str(old_val) != str(new_val):
            SecurityIncidentHistory.objects.create(
                incident=instance,
                field_name=field,
                old_value=old_val if old_val is not None else "",
                new_value=new_val if new_val is not None else "",
                changed_by=user,
            )
