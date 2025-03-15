import time

import pytz
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from website.forms import HackathonForm, HackathonPrizeForm, HackathonSponsorForm
from website.models import (
    Contributor,
    GitHubIssue,
    Hackathon,
    HackathonPrize,
    HackathonSponsor,
    Organization,
    Repo,
    UserProfile,
)


class HackathonListView(ListView):
    """View for listing all hackathons."""

    model = Hackathon
    template_name = "hackathons/list.html"
    context_object_name = "hackathons"
    paginate_by = 10

    def get_queryset(self):
        queryset = Hackathon.objects.all()

        # Filter by active status
        status = self.request.GET.get("status")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        # Filter by time (upcoming, ongoing, past)
        time_filter = self.request.GET.get("time")
        now = timezone.now()
        if time_filter == "upcoming":
            queryset = queryset.filter(start_time__gt=now)
        elif time_filter == "ongoing":
            queryset = queryset.filter(start_time__lte=now, end_time__gte=now)
        elif time_filter == "past":
            queryset = queryset.filter(end_time__lt=now)

        # Filter by organization
        org_id = self.request.GET.get("organization")
        if org_id and org_id.isdigit():
            queryset = queryset.filter(organization_id=int(org_id))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        # Add counts for quick stats
        context["upcoming_count"] = Hackathon.objects.filter(start_time__gt=now).count()
        context["ongoing_count"] = Hackathon.objects.filter(start_time__lte=now, end_time__gte=now).count()
        context["past_count"] = Hackathon.objects.filter(end_time__lt=now).count()

        # Add organizations for filter
        context["organizations"] = Organization.objects.all()

        # Add current filter values
        context["current_status"] = self.request.GET.get("status", "")
        context["current_time"] = self.request.GET.get("time", "")
        context["current_org"] = self.request.GET.get("organization", "")

        return context


class HackathonDetailView(DetailView):
    """View for displaying a single hackathon."""

    model = Hackathon
    template_name = "hackathons/detail.html"
    context_object_name = "hackathon"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = self.get_object()

        # Add breadcrumbs
        context["breadcrumbs"] = [
            {"title": "Hackathons", "url": reverse("hackathons")},
            {"title": hackathon.name, "url": None},
        ]

        # Get the leaderboard
        context["leaderboard"] = hackathon.get_leaderboard()

        # Get repositories with merged PR counts
        repositories = hackathon.repositories.all()
        repos_with_pr_counts = []

        for repo in repositories:
            # Count merged PRs for this repository
            merged_pr_count = GitHubIssue.objects.filter(
                repo=repo,
                type="pull_request",
                is_merged=True,
                merged_at__gte=hackathon.start_time,
                merged_at__lte=hackathon.end_time,
            ).count()

            repos_with_pr_counts.append({"repo": repo, "merged_pr_count": merged_pr_count})

        context["repositories"] = repos_with_pr_counts

        # Get PR data per day for chart
        import json
        from datetime import timedelta

        from django.db.models import Count
        from django.db.models.functions import TruncDate

        # Get participant count (users who have contributed to the repositories)
        repo_ids = hackathon.repositories.values_list("id", flat=True)

        # Get all pull requests during the hackathon period
        pr_data = (
            GitHubIssue.objects.filter(
                repo__in=repo_ids,
                created_at__gte=hackathon.start_time,
                created_at__lte=hackathon.end_time,
                type="pull_request",
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Prepare data for the chart
        pr_dates = []
        pr_counts = []
        merged_pr_counts = []

        # Fill in all dates in the range
        current_date = hackathon.start_time.date()
        end_date = hackathon.end_time.date()

        # Create dictionaries for lookup
        date_pr_counts = {item["date"]: item["count"] for item in pr_data}

        # Get merged PR data
        merged_pr_data = (
            GitHubIssue.objects.filter(
                repo__in=repo_ids,
                created_at__gte=hackathon.start_time,
                created_at__lte=hackathon.end_time,
                type="pull_request",
                is_merged=True,
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        date_merged_pr_counts = {item["date"]: item["count"] for item in merged_pr_data}

        # Fill in all dates in the range
        while current_date <= end_date:
            pr_dates.append(current_date.strftime("%Y-%m-%d"))
            pr_counts.append(date_pr_counts.get(current_date, 0))
            merged_pr_counts.append(date_merged_pr_counts.get(current_date, 0))
            current_date += timedelta(days=1)

        context["pr_dates"] = json.dumps(pr_dates)
        context["pr_counts"] = json.dumps(pr_counts)
        context["merged_pr_counts"] = json.dumps(merged_pr_counts)

        # Get sponsors by level
        sponsors = hackathon.sponsors.all()
        sponsors_by_level = {"platinum": [], "gold": [], "silver": [], "bronze": [], "partner": []}
        for sponsor in sponsors:
            sponsors_by_level[sponsor.sponsor_level].append(sponsor)
        context["sponsors_by_level"] = sponsors_by_level

        # Get prizes
        context["prizes"] = hackathon.prizes.all()

        # Check if user can manage this hackathon
        user = self.request.user
        can_manage = False
        if user.is_authenticated:
            if user.is_superuser:
                can_manage = True
            else:
                # Check if user is admin or manager of the organization
                org = hackathon.organization
                can_manage = org.is_admin(user) or org.is_manager(user)
        context["can_manage"] = can_manage

        # Count unique users who have created pull requests to the hackathon repositories
        # during the hackathon period
        from django.db.models import Count

        # Get all pull requests during the hackathon period
        prs = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            created_at__gte=hackathon.start_time,
            created_at__lte=hackathon.end_time,
            type="pull_request",
        )

        # Count unique user profiles (users registered on the platform)
        user_profile_count = prs.exclude(user_profile=None).values("user_profile").distinct().count()

        # Count unique contributors (GitHub users not registered on the platform)
        # Exclude bot accounts
        contributor_count = (
            prs.filter(user_profile=None)
            .exclude(contributor=None)
            .exclude(contributor__name__endswith="[bot]")
            .values("contributor")
            .distinct()
            .count()
        )

        # Total participant count is the sum of both
        participant_count = user_profile_count + contributor_count

        context["participant_count"] = participant_count

        # Count pull requests
        pr_count = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            created_at__gte=hackathon.start_time,
            created_at__lte=hackathon.end_time,
            type="pull_request",
        ).count()

        context["pr_count"] = pr_count

        # Count merged pull requests
        merged_pr_count = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            created_at__gte=hackathon.start_time,
            created_at__lte=hackathon.end_time,
            type="pull_request",
            is_merged=True,
        ).count()

        context["merged_pr_count"] = merged_pr_count

        # Get view data for sparkline chart
        import json
        from datetime import timedelta

        from django.db.models import Sum
        from django.db.models.functions import TruncDate
        from django.utils import timezone

        from website.models import IP

        # Get the path for this hackathon
        hackathon_path = f"/hackathons/{hackathon.slug}/"

        # Get the last 14 days of view data
        today = timezone.now().date()
        fourteen_days_ago = today - timedelta(days=14)

        # Query IP table for view counts by date
        view_data = (
            IP.objects.filter(path=hackathon_path, created__date__gte=fourteen_days_ago)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(count=Sum("count"))
            .order_by("date")
        )

        # Prepare data for the sparkline chart
        dates = []
        counts = []

        # Fill in missing dates with zero counts
        current_date = fourteen_days_ago
        date_counts = {item["date"]: item["count"] for item in view_data}

        while current_date <= today:
            dates.append(current_date.strftime("%Y-%m-%d"))
            counts.append(date_counts.get(current_date, 0))
            current_date += timedelta(days=1)

        context["view_dates"] = json.dumps(dates)
        context["view_counts"] = json.dumps(counts)
        context["total_views"] = sum(counts)

        return context


class HackathonCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new hackathon."""

    model = Hackathon
    form_class = HackathonForm
    template_name = "hackathons/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Hackathon"
        context["submit_text"] = "Create Hackathon"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hackathon created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.object.slug})


class HackathonUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for updating an existing hackathon."""

    model = Hackathon
    form_class = HackathonForm
    template_name = "hackathons/form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def test_func(self):
        hackathon = self.get_object()
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Hackathon: {self.object.name}"
        context["submit_text"] = "Update Hackathon"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hackathon updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.object.slug})


class HackathonSponsorCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View for adding a sponsor to a hackathon."""

    model = HackathonSponsor
    form_class = HackathonSponsorForm
    template_name = "hackathons/sponsor_form.html"

    def test_func(self):
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        context["hackathon"] = hackathon
        context["title"] = f"Add Sponsor to {hackathon.name}"
        context["submit_text"] = "Add Sponsor"
        return context

    def form_valid(self, form):
        form.instance.hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        messages.success(self.request, "Sponsor added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.kwargs["slug"]})


class HackathonPrizeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View for adding a prize to a hackathon."""

    model = HackathonPrize
    form_class = HackathonPrizeForm
    template_name = "hackathons/prize_form.html"

    def test_func(self):
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["hackathon"] = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        context["hackathon"] = hackathon
        context["title"] = f"Add Prize to {hackathon.name}"
        context["submit_text"] = "Add Prize"
        return context

    def form_valid(self, form):
        form.instance.hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        messages.success(self.request, "Prize added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.kwargs["slug"]})


@login_required
def refresh_repository_data(request, hackathon_slug, repo_id):
    """View to refresh repository data from GitHub API."""
    hackathon = get_object_or_404(Hackathon, slug=hackathon_slug)
    repo = get_object_or_404(Repo, id=repo_id)

    # Check if user has permission to refresh data
    user = request.user
    if not (user.is_superuser or hackathon.organization.is_admin(user) or hackathon.organization.is_manager(user)):
        messages.error(request, "You don't have permission to refresh repository data.")
        return redirect("hackathon_detail", slug=hackathon_slug)

    try:
        # Extract owner and repo name from repo URL
        # URL format: https://github.com/owner/repo
        parts = repo.repo_url.split("/")
        owner = parts[-2]
        repo_name = parts[-1]

        # GitHub API endpoint for pull requests
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        headers = {}

        # Add GitHub token if available
        if hasattr(settings, "GITHUB_TOKEN") and settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        # Add accept header for GitHub API
        headers["Accept"] = "application/vnd.github.v3+json"

        # Get pull requests from GitHub API
        params = {
            "state": "all",  # Get all PRs (open, closed, merged)
            "sort": "updated",  # Sort by last updated to get both recently created and recently merged
            "direction": "desc",
            "per_page": 100,  # Maximum per page
        }

        # If the hackathon started more than 3 months ago, we need to make multiple requests
        # to get all PRs that might be relevant
        all_prs_data = []
        page = 1
        max_pages = 5  # Limit to 5 pages (500 PRs) to avoid excessive API calls

        while page <= max_pages:
            params["page"] = page
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()  # Raise exception for HTTP errors

            page_data = response.json()
            if not page_data:  # No more results
                break

            all_prs_data.extend(page_data)

            # Check if the oldest PR on this page is older than the hackathon start time
            # If so, we can stop fetching more pages
            oldest_pr = page_data[-1]
            oldest_updated = timezone.datetime.strptime(oldest_pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=pytz.UTC
            )
            if oldest_updated < hackathon.start_time:
                break

            page += 1

            # Respect GitHub's rate limits by adding a small delay
            time.sleep(0.5)

        # Process pull requests
        pr_count = 0
        for pr_data in all_prs_data:
            # Parse dates
            created_at = timezone.datetime.strptime(pr_data["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=pytz.UTC
            )

            # Determine if PR is merged
            is_merged = pr_data["merged_at"] is not None
            merged_at = None
            if is_merged:
                merged_at = timezone.datetime.strptime(pr_data["merged_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.UTC
                )

            # Check if PR is relevant to the hackathon
            # Include PRs that were merged during the hackathon timeframe
            is_relevant = False

            # If PR was merged during the hackathon timeframe
            if is_merged and merged_at and hackathon.start_time <= merged_at <= hackathon.end_time:
                is_relevant = True
            # Or if PR was created during the hackathon timeframe
            elif hackathon.start_time <= created_at <= hackathon.end_time:
                is_relevant = True

            if not is_relevant:
                continue  # Skip PRs not relevant to the hackathon

            # Get or create contributor
            github_username = pr_data["user"]["login"]
            github_id = pr_data["user"]["id"]
            github_url = pr_data["user"]["html_url"]
            avatar_url = pr_data["user"]["avatar_url"]

            # Try to find existing contributor
            contributor, created = Contributor.objects.get_or_create(
                github_id=github_id,
                defaults={
                    "name": github_username,
                    "github_url": github_url,
                    "avatar_url": avatar_url,
                    "contributor_type": pr_data["user"]["type"],
                    "contributions": 1,
                },
            )

            if not created:
                # Update existing contributor
                contributor.name = github_username
                contributor.github_url = github_url
                contributor.avatar_url = avatar_url
                contributor.contributions += 1
                contributor.save()

            # Add contributor to repo
            repo.contributor.add(contributor)

            # Check if PR already exists in database
            existing_pr = GitHubIssue.objects.filter(issue_id=pr_data["number"], repo=repo).first()

            # Update or create PR
            if existing_pr:
                existing_pr.title = pr_data["title"]
                existing_pr.state = pr_data["state"]
                existing_pr.is_merged = is_merged
                existing_pr.merged_at = merged_at
                existing_pr.updated_at = timezone.datetime.strptime(
                    pr_data["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)

                # Link to contributor if not already linked
                if not existing_pr.contributor:
                    existing_pr.contributor = contributor

                existing_pr.save()
            else:
                # Create new PR
                new_pr = GitHubIssue(
                    issue_id=pr_data["number"],
                    title=pr_data["title"],
                    body=pr_data["body"] or "",
                    state=pr_data["state"],
                    type="pull_request",
                    created_at=created_at,
                    updated_at=timezone.datetime.strptime(pr_data["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=pytz.UTC
                    ),
                    merged_at=merged_at,
                    is_merged=is_merged,
                    url=pr_data["html_url"],
                    repo=repo,
                    contributor=contributor,  # Link to contributor
                )

                # Try to find a user profile for the PR author
                matching_profiles = UserProfile.objects.filter(github_url__icontains=github_username)
                if matching_profiles.exists():
                    new_pr.user_profile = matching_profiles.first()

                new_pr.save()
                pr_count += 1

        messages.success(request, f"Successfully refreshed data for {repo.name}. Found {pr_count} new pull requests.")
    except Exception as e:
        messages.error(request, f"Error refreshing repository data: {str(e)}")

    return redirect("hackathon_detail", slug=hackathon_slug)

