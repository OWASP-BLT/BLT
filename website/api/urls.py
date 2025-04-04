from django.urls import path

from . import views

urlpatterns = [
    path("stats/views", views.view_stats, name="view-stats"),
    path("github-issues/<int:issue_number>", views.github_issue, name="github-issue"),
    path("badge/issue/<int:issue_number>", views.issue_badge, name="issue-badge"),
]
