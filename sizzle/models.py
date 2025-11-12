import logging
from datetime import datetime

import pytz
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class TimeLog(models.Model):
    """Time tracking model for sizzle functionality"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sizzle_time_logs")
    organization = models.ForeignKey(
        getattr(settings, 'SIZZLE_ORGANIZATION_MODEL', 'website.Organization'),
        on_delete=models.CASCADE,
        related_name="sizzle_time_logs",
        null=True,
        blank=True,
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    github_issue_url = models.URLField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time <= self.end_time:
            self.duration = self.end_time - self.start_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"TimeLog by {self.user.username} from {self.start_time} to {self.end_time}"


class DailyStatusReport(models.Model):
    """Daily status report for team check-ins"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sizzle_daily_status_reports")
    date = models.DateField()
    previous_work = models.TextField()
    next_plan = models.TextField()
    blockers = models.TextField()
    goal_accomplished = models.BooleanField(default=False)
    current_mood = models.CharField(max_length=50, default="Happy 😊")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"Daily Status Report by {self.user.username} on {self.date}"


class ReminderSettings(models.Model):
    """User settings for daily reminder notifications"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sizzle_reminder_settings")
    reminder_time = models.TimeField(help_text="Time to send daily reminders (in user's timezone)")
    reminder_time_utc = models.TimeField(help_text="Time to send daily reminders (in UTC)", null=True, blank=True)
    timezone = models.CharField(max_length=50, default="UTC")
    is_active = models.BooleanField(default=True, help_text="Enable/disable daily reminders")
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reminder Settings"
        verbose_name_plural = "Reminder Settings"
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["reminder_time_utc"]),
        ]

    def __str__(self):
        return f"Reminder Settings for {self.user.username}"

    def save(self, *args, **kwargs):
        if self.reminder_time and self.timezone:
            user_tz = pytz.timezone(self.timezone)
            # Create a datetime with today's date and the reminder time
            today = timezone.now().date()
            local_dt = user_tz.localize(datetime.combine(today, self.reminder_time))
            # Convert to UTC
            utc_dt = local_dt.astimezone(pytz.UTC)
            # Extract just the time part
            self.reminder_time_utc = utc_dt.time()
        super().save(*args, **kwargs)

    @classmethod
    def get_timezone_choices(cls):
        if not hasattr(cls, "_timezone_choices"):
            cls._timezone_choices = [(tz, tz) for tz in pytz.common_timezones]
        return cls._timezone_choices
