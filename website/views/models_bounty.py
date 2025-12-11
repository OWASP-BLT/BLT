from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Bounty(models.Model):
    # Issue identification (we store repo owner/name + issue number + full url)
    repo_full_name = models.CharField(max_length=200)  # e.g. "org/repo"
    issue_number = models.PositiveIntegerField()
    issue_url = models.URLField()

    # Sponsor info (store GitHub login and optionally a foreign key if you have users)
    sponsor_github = models.CharField(max_length=200, blank=True, null=True)
    sponsor_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    # Money fields
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # currency in USD (or store cents)
    currency = models.CharField(max_length=10, default="USD")

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Optional: reference to GitHub comment that created this bounty (if from GH comment)
    origin_comment_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["repo_full_name", "issue_number"]),
            models.Index(fields=["sponsor_github"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.repo_full_name}#{self.issue_number} ${self.amount} by {self.sponsor_github}"
