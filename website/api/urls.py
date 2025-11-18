"""API v1 URL routing for badge and statistics endpoints."""
from django.urls import path

from website.api.views import github_issue_badge

app_name = "api"

urlpatterns = [
    # Badge endpoints
    path("badge/issue/<int:issue_number>/", github_issue_badge, name="github_issue_badge"),
]
