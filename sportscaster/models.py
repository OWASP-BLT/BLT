from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class MonitoredEntity(models.Model):
    """Represents a GitHub entity being monitored (repo, org, or tag)"""

    SCOPE_CHOICES = [
        ("all_github", "All GitHub"),
        ("organization", "Organization"),
        ("repository", "Repository"),
        ("tag", "Tag"),
        ("curated_list", "Curated List"),
    ]

    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    github_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "Monitored Entities"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.scope})"


class GitHubEvent(models.Model):
    """Stores GitHub events for monitoring and leaderboard"""

    EVENT_TYPES = [
        ("star", "Star"),
        ("fork", "Fork"),
        ("pull_request", "Pull Request"),
        ("commit", "Commit"),
        ("release", "Release"),
        ("issue", "Issue"),
        ("watch", "Watch"),
        ("hackathon", "Hackathon Announcement"),
    ]

    monitored_entity = models.ForeignKey(MonitoredEntity, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    event_data = models.JSONField(default=dict)
    timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    commentary_generated = models.BooleanField(default=False)
    commentary_text = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["processed"]),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.monitored_entity.name} at {self.timestamp}"


class Leaderboard(models.Model):
    """Tracks real-time leaderboard rankings"""

    monitored_entity = models.ForeignKey(MonitoredEntity, on_delete=models.CASCADE, related_name="leaderboard_entries")
    metric_type = models.CharField(max_length=50, default="stars")
    current_value = models.IntegerField(default=0)
    previous_value = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank"]
        unique_together = ["monitored_entity", "metric_type"]

    def __str__(self):
        return f"{self.monitored_entity.name} - {self.metric_type}: {self.current_value}"


class UserChannel(models.Model):
    """User-curated channels for personalized sportscasting"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sportscaster_channels")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    monitored_entities = models.ManyToManyField(MonitoredEntity, related_name="channels")
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}'s {self.name}"


class AICommentaryTemplate(models.Model):
    """Templates for AI-generated sports commentary"""

    event_type = models.CharField(max_length=20)
    template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event_type"]

    def __str__(self):
        return f"Template for {self.event_type}"
