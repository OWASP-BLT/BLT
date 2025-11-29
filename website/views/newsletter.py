"""
Newsletter views for displaying project statistics, leaderboards, and updates.
"""

import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from website.models import (
    Contributor,
    Domain,
    GitHubIssue,
    GitHubReview,
    Hunt,
    Issue,
    Organization,
    Points,
    Project,
    Repo,
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)


class NewsletterView(TemplateView):
    """
    Newsletter page displaying project statistics, top contributors,
    recent bugs, and releases.
    """

    template_name = "newsletter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Time ranges for filtering
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_6_months = now - relativedelta(months=6)

        # ===== Summary Statistics =====
        context["total_bugs"] = Issue.objects.count()
        context["bugs_this_month"] = Issue.objects.filter(created__gte=last_30_days).count()
        context["open_bugs"] = Issue.objects.filter(status="open").count()
        context["closed_bugs"] = Issue.objects.filter(status="closed").count()
        context["total_users"] = User.objects.count()
        context["total_domains"] = Domain.objects.count()
        context["total_organizations"] = Organization.objects.count()
        context["active_hunts_count"] = Hunt.objects.filter(is_published=True, end_on__gte=now).count()

        # ===== Recent Bugs/Issues =====
        recent_bugs = (
            Issue.objects.select_related("user", "domain")
            .filter(is_hidden=False)
            .order_by("-created")[:10]
        )
        context["recent_bugs"] = recent_bugs

        # ===== Points Leaderboard (Top Contributors) =====
        leaderboard = (
            User.objects.annotate(total_score=Sum("points__score"))
            .filter(total_score__gt=0, username__isnull=False)
            .exclude(username="")
            .order_by("-total_score")[:10]
        )
        context["leaderboard"] = leaderboard

        # ===== Monthly Top Contributors =====
        monthly_leaderboard = (
            User.objects.filter(points__created__gte=last_30_days)
            .annotate(monthly_score=Sum("points__score"))
            .filter(monthly_score__gt=0, username__isnull=False)
            .exclude(username="")
            .order_by("-monthly_score")[:5]
        )
        context["monthly_leaderboard"] = monthly_leaderboard

        # ===== Pull Request Leaderboard =====
        pr_leaderboard = (
            GitHubIssue.objects.filter(
                type="pull_request",
                is_merged=True,
                contributor__isnull=False,
                merged_at__gte=last_6_months,
            )
            .filter(
                Q(repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(contributor__name__icontains="copilot")
            .select_related("contributor", "user_profile__user")
            .values(
                "contributor__name",
                "contributor__github_url",
                "contributor__avatar_url",
                "user_profile__user__username",
            )
            .annotate(total_prs=Count("id"))
            .order_by("-total_prs")[:5]
        )
        context["pr_leaderboard"] = pr_leaderboard

        # ===== Code Review Leaderboard =====
        code_review_leaderboard = (
            GitHubReview.objects.filter(
                reviewer_contributor__isnull=False,
                pull_request__merged_at__gte=last_6_months,
            )
            .filter(
                Q(pull_request__repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(pull_request__repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(reviewer_contributor__name__icontains="copilot")
            .values(
                "reviewer_contributor__name",
                "reviewer_contributor__github_url",
                "reviewer_contributor__avatar_url",
            )
            .annotate(total_reviews=Count("id"))
            .order_by("-total_reviews")[:5]
        )
        context["code_review_leaderboard"] = code_review_leaderboard

        # ===== Top Streakers =====
        top_streakers = UserProfile.objects.filter(current_streak__gt=0).order_by("-current_streak")[:5]
        context["top_streakers"] = top_streakers

        # ===== New Releases =====
        # Get repos with recent releases, ordered by release date
        recent_releases = (
            Repo.objects.filter(
                release_name__isnull=False,
                release_datetime__isnull=False,
            )
            .select_related("project")
            .order_by("-release_datetime")[:10]
        )
        context["recent_releases"] = recent_releases

        # ===== Active Bug Hunts =====
        active_hunts = (
            Hunt.objects.filter(is_published=True, end_on__gte=now)
            .select_related("domain")
            .order_by("end_on")[:5]
        )
        context["active_hunts"] = active_hunts

        # ===== Recent Projects =====
        recent_projects = Project.objects.order_by("-created")[:5]
        context["recent_projects"] = recent_projects

        # ===== Bug Categories Distribution =====
        bug_categories = (
            Issue.objects.filter(created__gte=last_30_days)
            .values("label")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Map label numbers to names
        label_map = dict(Issue.labels)
        context["bug_categories"] = [
            {"name": label_map.get(item["label"], "Unknown"), "count": item["count"]} for item in bug_categories
        ]

        return context
