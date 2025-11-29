"""Newsletter view for the BLT platform."""

import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from website.models import (
    Domain,
    GitHubIssue,
    GitHubReview,
    Hunt,
    Issue,
    Organization,
    Project,
    Repo,
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)


class NewsletterView(TemplateView):
    """Monthly digest showing platform activity, contributors, and releases."""

    template_name = "newsletter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_6_months = now - relativedelta(months=6)

        # Stats overview
        context["total_bugs"] = Issue.objects.count()
        context["bugs_this_month"] = Issue.objects.filter(created__gte=last_30_days).count()
        context["open_bugs"] = Issue.objects.filter(status="open").count()
        context["closed_bugs"] = Issue.objects.filter(status="closed").count()
        context["total_users"] = User.objects.count()
        context["total_domains"] = Domain.objects.count()
        context["total_organizations"] = Organization.objects.count()
        context["active_hunts_count"] = Hunt.objects.filter(is_published=True, end_on__gte=now).count()

        # Recent bug reports
        context["recent_bugs"] = (
            Issue.objects.select_related("user", "domain").filter(is_hidden=False).order_by("-created")[:10]
        )

        # All-time points leaderboard
        context["leaderboard"] = (
            User.objects.annotate(total_score=Sum("points__score"))
            .filter(total_score__gt=0, username__isnull=False)
            .exclude(username="")
            .order_by("-total_score")[:10]
        )

        # This month's top scorers
        context["monthly_leaderboard"] = (
            User.objects.filter(points__created__gte=last_30_days)
            .annotate(monthly_score=Sum("points__score"))
            .filter(monthly_score__gt=0, username__isnull=False)
            .exclude(username="")
            .order_by("-monthly_score")[:5]
        )

        # PR contributors (excluding bots)
        context["pr_leaderboard"] = (
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
            .exclude(contributor__name__icontains="[bot]")
            .exclude(contributor__name__icontains="copilot")
            .exclude(contributor__name__icontains="dependabot")
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

        # Code reviewers (excluding bots)
        context["code_review_leaderboard"] = (
            GitHubReview.objects.filter(
                reviewer_contributor__isnull=False,
                pull_request__merged_at__gte=last_6_months,
            )
            .filter(
                Q(pull_request__repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(pull_request__repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(reviewer_contributor__name__icontains="[bot]")
            .exclude(reviewer_contributor__name__icontains="copilot")
            .exclude(reviewer_contributor__name__icontains="dependabot")
            .values(
                "reviewer_contributor__name",
                "reviewer_contributor__github_url",
                "reviewer_contributor__avatar_url",
            )
            .annotate(total_reviews=Count("id"))
            .order_by("-total_reviews")[:5]
        )

        # Users with active streaks
        context["top_streakers"] = UserProfile.objects.filter(current_streak__gt=0).order_by("-current_streak")[:5]

        # Latest releases from tracked repos
        context["recent_releases"] = (
            Repo.objects.filter(release_name__isnull=False, release_datetime__isnull=False)
            .select_related("project")
            .order_by("-release_datetime")[:10]
        )

        # Currently running bug hunts
        context["active_hunts"] = (
            Hunt.objects.filter(is_published=True, end_on__gte=now).select_related("domain").order_by("end_on")[:5]
        )

        # Recent projects
        context["recent_projects"] = Project.objects.order_by("-created")[:5]

        # Bug type breakdown for this month
        bug_categories = (
            Issue.objects.filter(created__gte=last_30_days)
            .values("label")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        label_map = dict(Issue.labels)
        context["bug_categories"] = [
            {"name": label_map.get(item["label"], "Unknown"), "count": item["count"]} for item in bug_categories
        ]

        return context
