from django.db import models
from django.contrib.auth.models import User

class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    achievements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    members = models.ManyToManyField(User, related_name="team_members", blank=True)
    leader = models.ForeignKey(User, related_name="team_leader", on_delete=models.CASCADE, null=True, blank=True, default=1)
    fresh_points = models.IntegerField(default=0)  # Add fresh_points field

    def __str__(self):
        return self.name

class JoinRequest(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

class Challenge(models.Model):
    CHALLENGE_TYPE_CHOICES = [
        ('single', 'Single User'),
        ('team', 'Team'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    challenge_type = models.CharField(max_length=10, choices=CHALLENGE_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    participants = models.ManyToManyField(User, related_name="user_challenges", blank=True)
    teams = models.ManyToManyField(Team, related_name="team_challenges", blank=True)
    fresh_points = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)  # Progress in percentage

    def __str__(self):
        return self.title