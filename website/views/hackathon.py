import json
import logging
import time
from datetime import timedelta

import pytz
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from website.forms import HackathonForm, HackathonPrizeForm, HackathonSponsorForm
from website.models import (
    IP,
    Contributor,
    GitHubIssue,
    Hackathon,
    HackathonPrize,
    HackathonSponsor,
    Organization,
    Repo,
    UserProfile,
)

logger = logging.getLogger(__name__)
REPO_REFRESH_DELAY_SECONDS = getattr(settings, "HACKATHON_REPO_REFRESH_DELAY", 1.0)


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

    def _get_base_pr_query(self, hackathon, repo_ids, is_merged=None):
        """Helper method to create a base query for pull requests."""
        query = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            type="pull_request",
        )

        if is_merged is not None:
            query = query.filter(is_merged=is_merged)
            if is_merged:
                # For merged PRs, only include those merged during the hackathon
                query = query.filter(
                    merged_at__gte=hackathon.start_time,
                    merged_at__lte=hackathon.end_time,
                )
        else:
            # For all PRs (merged or not), include those created during the hackathon
            query = query.filter(
                created_at__gte=hackathon.start_time,
                created_at__lte=hackathon.end_time,
            )

        # Exclude bot accounts from contributors
        # Filter by contributor_type field (primary check) and name patterns (fallback)
        query = query.exclude(
            Q(contributor__contributor_type="Bot")
            | Q(contributor__name__endswith="[bot]")
            | Q(contributor__name__icontains="bot")
        )

        return query

    def _get_date_range_data(self, start_date, end_date, data_dict, default_value=0):
        """Helper method to fill in date ranges with data."""
        result_dates = []
        result_values = []

        current_date = start_date
        while current_date <= end_date:
            result_dates.append(current_date.strftime("%Y-%m-%d"))
            result_values.append(data_dict.get(current_date, default_value))
            current_date += timedelta(days=1)

        return result_dates, result_values

    def _get_participant_count(self, prs):
        """Helper method to count unique participants from PRs."""
        # Count unique user profiles (users registered on the platform)
        user_profile_count = prs.exclude(user_profile=None).values("user_profile").distinct().count()

        # Count unique contributors (GitHub users not registered on the platform)
        # Exclude bot accounts using contributor_type field (primary) and name patterns (fallback)
        contributor_count = (
            prs.filter(user_profile=None)
            .exclude(contributor=None)
            .exclude(
                Q(contributor__contributor_type="Bot")
                | Q(contributor__name__endswith="[bot]")
                | Q(contributor__name__icontains="bot")
            )
            .values("contributor")
            .distinct()
            .count()
        )

        # Total participant count is the sum of both
        return user_profile_count + contributor_count

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
        repo_ids = repositories.values_list("id", flat=True)
        repos_with_pr_counts = []

        for repo in repositories:
            # Count merged PRs for this repository (excluding bots)
            merged_pr_count = (
                GitHubIssue.objects.filter(
                    repo=repo,
                    type="pull_request",
                    is_merged=True,
                    merged_at__gte=hackathon.start_time,
                    merged_at__lte=hackathon.end_time,
                )
                .exclude(
                    Q(contributor__contributor_type="Bot")
                    | Q(contributor__name__endswith="[bot]")
                    | Q(contributor__name__icontains="bot")
                )
                .count()
            )

            repos_with_pr_counts.append({"repo": repo, "merged_pr_count": merged_pr_count})

        context["repositories"] = repos_with_pr_counts

        # Get PR data per day for chart
        # Get all pull requests during the hackathon period
        pr_data = (
            self._get_base_pr_query(hackathon, repo_ids)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Get merged PR data
        merged_pr_data = (
            self._get_base_pr_query(hackathon, repo_ids, is_merged=True)
            .annotate(date=TruncDate("merged_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Create dictionaries for lookup
        date_pr_counts = {item["date"]: item["count"] for item in pr_data}
        date_merged_pr_counts = {item["date"]: item["count"] for item in merged_pr_data}

        # Fill in all dates in the range
        pr_dates, pr_counts = self._get_date_range_data(
            hackathon.start_time.date(), hackathon.end_time.date(), date_pr_counts
        )

        _, merged_pr_counts = self._get_date_range_data(
            hackathon.start_time.date(), hackathon.end_time.date(), date_merged_pr_counts
        )

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

        # Get all merged pull requests during the hackathon period for participant count
        merged_prs = self._get_base_pr_query(hackathon, repo_ids, is_merged=True)
        context["participant_count"] = self._get_participant_count(merged_prs)

        # Count pull requests
        context["pr_count"] = self._get_base_pr_query(hackathon, repo_ids).count()

        # Count merged pull requests
        context["merged_pr_count"] = self._get_base_pr_query(hackathon, repo_ids, is_merged=True).count()

        # Get view data for sparkline chart
        # Get the path for this hackathon
        hackathon_path = f"/hackathons/{hackathon.slug}/"

        # Calculate views during the hackathon timeframe
        hackathon_start_date = hackathon.start_time.date()
        hackathon_end_date = hackathon.end_time.date()
        today = timezone.now().date()

        # Use the end date or today, whichever is earlier for the chart
        chart_end_date = min(hackathon_end_date, today)

        # Query IP table for view counts during hackathon period
        # Use path__contains to match the widget's behavior
        hackathon_view_data = (
            IP.objects.filter(
                path__contains=hackathon_path,
                created__date__gte=hackathon_start_date,
                created__date__lte=chart_end_date,
            )
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(count=Sum("count"))
            .order_by("date")
        )

        # Prepare data for the sparkline chart (hackathon timeframe)
        date_counts = {item["date"]: item["count"] for item in hackathon_view_data}
        dates, counts = self._get_date_range_data(hackathon_start_date, chart_end_date, date_counts)

        context["view_dates"] = json.dumps(dates)
        context["view_counts"] = json.dumps(counts)
        context["hackathon_views"] = sum(counts)

        # Calculate all-time views (from the beginning)
        all_time_views = IP.objects.filter(path__contains=hackathon_path).aggregate(total=Sum("count"))["total"] or 0
        context["all_time_views"] = all_time_views

        return context


class HackathonFormMixin:
    """Mixin for common functionality between hackathon create and update views."""

    form_class = HackathonForm
    template_name = "hackathons/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.object.slug})


class HackathonCreateView(LoginRequiredMixin, HackathonFormMixin, CreateView):
    """View for creating a new hackathon."""

    model = Hackathon
    success_message = "Hackathon created successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Hackathon"
        context["submit_text"] = "Create Hackathon"
        return context


class HackathonUpdateView(LoginRequiredMixin, UserPassesTestMixin, HackathonFormMixin, UpdateView):
    """View for updating an existing hackathon."""

    model = Hackathon
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_message = "Hackathon updated successfully!"

    def test_func(self):
        hackathon = self.get_object()
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Hackathon: {self.object.name}"
        context["submit_text"] = "Update Hackathon"
        return context


class HackathonItemCreateMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for common functionality between hackathon item create views."""

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
        context["title"] = f"{self.item_type_name} to {hackathon.name}"
        context["submit_text"] = f"Add {self.item_type_name}"
        return context

    def form_valid(self, form):
        form.instance.hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        messages.success(self.request, f"{self.item_type_name} added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.kwargs["slug"]})


class HackathonSponsorCreateView(HackathonItemCreateMixin, CreateView):
    """View for adding a sponsor to a hackathon."""

    model = HackathonSponsor
    form_class = HackathonSponsorForm
    template_name = "hackathons/sponsor_form.html"
    item_type_name = "Sponsor"


class HackathonPrizeCreateView(HackathonItemCreateMixin, CreateView):
    """View for adding a prize to a hackathon."""

    model = HackathonPrize
    form_class = HackathonPrizeForm
    template_name = "hackathons/prize_form.html"
    item_type_name = "Prize"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["hackathon"] = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        return kwargs


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
        pr_count = _refresh_repository_pull_requests(hackathon, repo)
        messages.success(request, f"Successfully refreshed data for {repo.name}. Found {pr_count} new pull requests.")
    except Exception as e:
        messages.error(request, f"Error refreshing repository data: {str(e)}")

    return redirect("hackathon_detail", slug=hackathon_slug)


@login_required
def refresh_all_hackathon_repositories(request, slug):
    """Refresh pull request data for all repositories linked to a hackathon."""
    hackathon = get_object_or_404(Hackathon, slug=slug)

    user = request.user
    if not (user.is_superuser or hackathon.organization.is_admin(user) or hackathon.organization.is_manager(user)):
        messages.error(request, "You don't have permission to refresh repository data.")
        return redirect("hackathon_detail", slug=slug)

    repositories = list(hackathon.repositories.all())
    if not repositories:
        messages.info(request, f"No repositories are linked to {hackathon.name}.")
        return redirect("hackathon_detail", slug=slug)

    refreshed_count = 0
    total_new_prs = 0
    failed_repos = []

    for index, repo in enumerate(repositories, start=1):
        try:
            new_prs = _refresh_repository_pull_requests(hackathon, repo)
            total_new_prs += new_prs
            refreshed_count += 1
        except requests.exceptions.RequestException as exc:
            failed_repos.append(repo.name)
            logger.warning(
                "GitHub API request failed while refreshing repo '%s' for hackathon '%s': %s",
                repo.name,
                hackathon.slug,
                exc,
                exc_info=True,
            )
        except Exception:
            failed_repos.append(repo.name)
            logger.exception(
                "Unexpected error while refreshing repo '%s' for hackathon '%s'",
                repo.name,
                hackathon.slug,
            )

        if index < len(repositories) and REPO_REFRESH_DELAY_SECONDS > 0:
            # Sleep briefly to avoid tripping GitHub's secondary rate limits across repositories.
            time.sleep(REPO_REFRESH_DELAY_SECONDS)

    if refreshed_count:
        messages.success(
            request,
            f"Successfully refreshed {refreshed_count} repositories. Found {total_new_prs} new pull requests.",
        )

    if failed_repos:
        repo_list = ", ".join(failed_repos)
        messages.error(
            request,
            f"Unable to refresh the following repositories: {repo_list}. Please try again later.",
        )

    return redirect("hackathon_detail", slug=slug)


def _refresh_repository_pull_requests(hackathon, repo):
    """Helper function to refresh pull request data from GitHub API."""
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
        if _process_pull_request(pr_data, hackathon, repo):
            pr_count += 1

    return pr_count


def _process_pull_request(pr_data, hackathon, repo):
    """Process a single pull request from GitHub API data."""
    # Parse dates
    created_at = timezone.datetime.strptime(pr_data["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

    # Determine if PR is merged
    is_merged = pr_data["merged_at"] is not None
    merged_at = None
    if is_merged:
        merged_at = timezone.datetime.strptime(pr_data["merged_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

    # Check if PR is relevant to the hackathon
    is_relevant = False

    # If PR was merged during the hackathon timeframe
    if is_merged and merged_at and hackathon.start_time <= merged_at <= hackathon.end_time:
        is_relevant = True
    # Or if PR was created during the hackathon timeframe (for non-merged PRs)
    elif not is_merged and hackathon.start_time <= created_at <= hackathon.end_time:
        is_relevant = True

    if not is_relevant:
        return False  # Skip PRs not relevant to the hackathon

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
        existing_pr.updated_at = timezone.datetime.strptime(pr_data["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.UTC
        )

        # Link to contributor if not already linked
        if not existing_pr.contributor:
            existing_pr.contributor = contributor

        existing_pr.save()
        return False  # Not a new PR
    else:
        # Create new PR
        new_pr = GitHubIssue(
            issue_id=pr_data["number"],
            title=pr_data["title"],
            body=pr_data["body"] or "",
            state=pr_data["state"],
            type="pull_request",
            created_at=created_at,
            updated_at=timezone.datetime.strptime(pr_data["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC),
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
        return True  # New PR added


@login_required
def add_org_repos_to_hackathon(request, slug):
    """View to add all organization repositories to a hackathon."""
    hackathon = get_object_or_404(Hackathon, slug=slug)

    # Check if user has permission to manage this hackathon
    user = request.user
    if not (user.is_superuser or hackathon.organization.is_admin(user) or hackathon.organization.is_manager(user)):
        messages.error(request, "You don't have permission to manage this hackathon.")
        return redirect("hackathons")

    try:
        # Get all repos from the hackathon's organization
        org_repos = Repo.objects.filter(organization=hackathon.organization)

        if not org_repos.exists():
            messages.warning(
                request,
                f"No repositories found for organization {hackathon.organization.name}. "
                "Please sync the organization's repositories first.",
            )
            return redirect("hackathons")

        # Add all org repos to the hackathon
        added_count = 0
        already_added_count = 0

        for repo in org_repos:
            if hackathon.repositories.filter(id=repo.id).exists():
                already_added_count += 1
            else:
                hackathon.repositories.add(repo)
                added_count += 1

        if added_count > 0:
            messages.success(
                request,
                f"Successfully added {added_count} repositories to {hackathon.name}. "
                f"({already_added_count} were already added)",
            )
        else:
            messages.info(
                request,
                f"All {already_added_count} repositories from {hackathon.organization.name} "
                "are already part of this hackathon.",
            )
    except Exception:
        messages.error(request, "An error occurred while adding repositories to the hackathon.")

    return redirect("hackathons")
