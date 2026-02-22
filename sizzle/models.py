from django.conf import settings
from django.db import models


class DailyStatusReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sizzle_reports")
    date = models.DateField()
    issue_title = models.CharField(max_length=255, default="General Update")
    start_time = models.TimeField(null=True, blank=True)
    duration = models.CharField(max_length=50, default="0h 0m")
    previous_work = models.TextField()
    next_plan = models.TextField()
    blockers = models.TextField()
    goal_accomplished = models.BooleanField(default=False)
    current_mood = models.CharField(max_length=50, default="Happy 😊")
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s report for {self.date}"
