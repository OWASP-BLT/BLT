import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction

from website.management.base import LoggedBaseCommand
from website.models import Contributor, ContributorStats, Repo


class Command(LoggedBaseCommand):
    help = "Update contributor statistics with daily and monthly granularity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo_id",
            type=int,
            help="Repository ID from the database",
        )

    def handle(self, *args, **options):
        repo_id = options.get("repo_id")

        if repo_id:
            try:
                repo = Repo.objects.get(id=repo_id)
                self.update_stats_for_repo(repo)
            except Repo.DoesNotExist:
                raise CommandError(f"Repository with ID {repo_id} not found")
        # Update all repositories
        # for repo in Repo.objects.all():
        #     self.update_stats_for_repo(repo)

    def update_stats_for_repo(self, repo):
        self.stdout.write(f"Updating stats for repository: {repo.name}")

        owner, repo_name = self.parse_github_url(repo.repo_url)

        # Calculate current month date range
        today = datetime.now().date()
        current_month_start = today.replace(day=1)  # First day of current month

        # Delete existing daily stats for current month
        self.delete_existing_daily_stats(repo, current_month_start)

        # Fetch and store daily stats for current month
        daily_stats = self.fetch_contributor_stats(owner, repo_name, current_month_start, today)
        self.store_daily_stats(repo, daily_stats)

        # Handle monthly stats
        self.update_monthly_stats(repo, current_month_start)

    def parse_github_url(self, url):
        # Remove trailing slash if present
        url = url.rstrip("/")
        # Extract owner and repo name from GitHub URL
        parts = url.split("/")
        return parts[-2], parts[-1]

    def delete_existing_daily_stats(self, repo, current_month_start):
        """Delete existing daily stats for the current month"""
        with transaction.atomic():
            ContributorStats.objects.filter(repo=repo, granularity="day", date__gte=current_month_start).delete()

    def fetch_contributor_stats(self, owner, repo_name, start_date, end_date):
        """Fetch contributor statistics using GitHub REST API"""
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        stats = {}  # {(date, login): {commits: X, issues_opened: Y, ...}}

        # Helper function to handle pagination
        def get_paginated_data(url, params=None):
            all_data = []
            while url:
                response = requests.get(url, headers=headers, params=params)

                if response.status_code == 403:  # Rate limit exceeded
                    reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                    sleep_time = max(reset_timestamp - time.time(), 0) + 1
                    self.stdout.write(f"Rate limit exceeded. Waiting {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue

                if response.status_code != 200:
                    self.stdout.write(self.style.WARNING(f"API error: {response.status_code} - {response.text}"))
                    break

                data = response.json()
                all_data.extend(data)

                # Check for next page in Link header
                if "Link" in response.headers:
                    links = requests.utils.parse_header_links(response.headers["Link"])
                    next_url = next((link["url"] for link in links if link["rel"] == "next"), None)
                    if next_url:
                        url = next_url
                        params = None  # Params are included in the next_url
                    else:
                        break
                else:
                    break

            return all_data

        try:
            # 1. Fetch commits
            commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
            commits_params = {
                "since": start_date.isoformat(),
                "until": end_date.isoformat(),
                "per_page": 100,
            }
            commits = get_paginated_data(commits_url, commits_params)

            for commit in commits:
                if commit.get("author") and commit.get("commit", {}).get("author", {}).get("date"):
                    date = datetime.strptime(commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").date()
                    login = commit["author"].get("login")
                    if login:
                        self.increment_stat(stats, date, login, "commits")

            # 2. Fetch issues
            issues_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
            issues_params = {"state": "all", "since": start_date.isoformat(), "per_page": 100}
            issues = get_paginated_data(issues_url, issues_params)

            for issue in issues:
                if not issue.get("pull_request"):  # Skip pull requests
                    if issue.get("user", {}).get("login"):
                        login = issue["user"]["login"]

                        # Handle issue creation
                        created_date = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                        if start_date <= created_date <= end_date:
                            self.increment_stat(stats, created_date, login, "issues_opened")

                        # Handle issue closure
                        if issue.get("closed_at"):
                            closed_date = datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                            if start_date <= closed_date <= end_date:
                                self.increment_stat(stats, closed_date, login, "issues_closed")

            # 3. Fetch pull requests
            pulls_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
            pulls_params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 100}
            pulls = get_paginated_data(pulls_url, pulls_params)

            for pr in pulls:
                if pr.get("user", {}).get("login"):
                    login = pr["user"]["login"]
                    created_date = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                    if start_date <= created_date <= end_date:
                        self.increment_stat(stats, created_date, login, "pull_requests")

            # 4. Fetch comments
            comments_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/comments"
            comments_params = {"since": start_date.isoformat(), "per_page": 100}
            comments = get_paginated_data(comments_url, comments_params)

            for comment in comments:
                if comment.get("user", {}).get("login"):
                    login = comment["user"]["login"]
                    comment_date = datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                    if start_date <= comment_date <= end_date:
                        self.increment_stat(stats, comment_date, login, "comments")

            return stats

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Network error: {str(e)}"))
            return {}

    def increment_stat(self, stats, date, login, stat_type):
        """Helper method to increment statistics"""
        key = (date, login)
        if key not in stats:
            stats[key] = {
                "commits": 0,
                "issues_opened": 0,
                "issues_closed": 0,
                "pull_requests": 0,
                "comments": 0,
            }
        stats[key][stat_type] += 1

    def store_daily_stats(self, repo, stats):
        """Store daily statistics in the database"""
        with transaction.atomic():
            for (date, login), day_stats in stats.items():
                contributor, _ = self.get_or_create_contributor(login)

                ContributorStats.objects.create(
                    contributor=contributor, repo=repo, date=date, granularity="day", **day_stats
                )

    def update_monthly_stats(self, repo, start_date):
        """Update monthly statistics by fetching directly from GitHub API"""
        owner, repo_name = self.parse_github_url(repo.repo_url)

        # Get the last monthly stat to know where to start from
        last_monthly_stat = ContributorStats.objects.filter(repo=repo, granularity="month").order_by("-date").first()

        if last_monthly_stat:
            # Start from the month after the last stored monthly stat
            current_month_start = (last_monthly_stat.date + relativedelta(months=1)).replace(day=1)
        else:
            # Get repo creation date from GitHub API
            try:
                headers = {
                    "Authorization": f"token {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                }
                repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                response = requests.get(repo_api_url, headers=headers)

                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Failed to fetch repo data: {response.text}"))
                    return

                repo_data = response.json()
                repo_created_at = datetime.strptime(repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching repo creation date: {str(e)}"))
                return
            # Start from repo creation date's month
            current_month_start = repo_created_at.replace(day=1)

        # Process each month until last month (not including current month)
        today = datetime.now().date()
        last_month_end = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        while current_month_start < last_month_start:
            month_end = current_month_start + relativedelta(months=1) - timedelta(days=1)

            self.stdout.write(f"Fetching stats for month: {current_month_start} to {month_end}")

            monthly_stats = self.fetch_monthly_contributor_stats(owner, repo_name, current_month_start, month_end)

            if monthly_stats:
                self.store_monthly_stats(repo, current_month_start, monthly_stats)

            current_month_start += relativedelta(months=1)

    def fetch_monthly_contributor_stats(self, owner, repo_name, month_start, month_end):
        """Fetch and aggregate monthly statistics directly from GitHub"""
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        monthly_stats = {}  # {login: {commits: X, issues_opened: Y, ...}}

        # Define pagination helper function inside this method
        def get_paginated_data(url, params=None):
            all_data = []
            while url:
                response = requests.get(url, headers=headers, params=params)

                if response.status_code == 403:  # Rate limit exceeded
                    reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                    sleep_time = max(reset_timestamp - time.time(), 0) + 1
                    self.stdout.write(f"Rate limit exceeded. Waiting {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue

                if response.status_code != 200:
                    self.stdout.write(self.style.WARNING(f"API error: {response.status_code} - {response.text}"))
                    break

                data = response.json()
                all_data.extend(data)

                # Check for next page in Link header
                if "Link" in response.headers:
                    links = requests.utils.parse_header_links(response.headers["Link"])
                    next_url = next((link["url"] for link in links if link["rel"] == "next"), None)
                    if next_url:
                        url = next_url
                        params = None  # Params are included in the next_url
                    else:
                        break
                else:
                    break

            return all_data

        try:
            # Rest of the existing fetch_monthly_contributor_stats code, but now using the local get_paginated_data function
            commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
            commits_params = {
                "since": month_start.isoformat(),
                "until": month_end.isoformat(),
                "per_page": 100,
            }
            commits = get_paginated_data(commits_url, commits_params)

            # 2. Fetch issues for the month
            issues_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
            issues_params = {"state": "all", "since": month_start.isoformat(), "per_page": 100}
            issues = get_paginated_data(issues_url, issues_params)

            # 3. Fetch PRs for the month
            pulls_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
            pulls_params = {"state": "all", "since": month_start.isoformat(), "per_page": 100}
            pulls = get_paginated_data(pulls_url, pulls_params)

            # 4. Fetch comments for the month
            comments_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/comments"
            comments_params = {"since": month_start.isoformat(), "per_page": 100}
            comments = get_paginated_data(comments_url, comments_params)

            # Process commits
            for commit in commits:
                if commit.get("author") and commit.get("commit", {}).get("author", {}).get("date"):
                    date = datetime.strptime(commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").date()
                    if month_start <= date <= month_end:
                        login = commit["author"].get("login")
                        if login:
                            self.increment_monthly_stat(monthly_stats, login, "commits")

            # Process issues
            for issue in issues:
                if not issue.get("pull_request"):  # Skip pull requests
                    login = issue.get("user", {}).get("login")
                    if not login:
                        continue

                    created_date = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                    if month_start <= created_date <= month_end:
                        self.increment_monthly_stat(monthly_stats, login, "issues_opened")

                    if issue.get("closed_at"):
                        closed_date = datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                        if month_start <= closed_date <= month_end:
                            self.increment_monthly_stat(monthly_stats, login, "issues_closed")

            # Process pull requests
            for pr in pulls:
                login = pr.get("user", {}).get("login")
                if (
                    login
                    and month_start <= datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").date() <= month_end
                ):
                    self.increment_monthly_stat(monthly_stats, login, "pull_requests")

            # Process comments
            for comment in comments:
                login = comment.get("user", {}).get("login")
                if (
                    login
                    and month_start
                    <= datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                    <= month_end
                ):
                    self.increment_monthly_stat(monthly_stats, login, "comments")

            return monthly_stats

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching monthly stats: {str(e)}"))
            return {}

    def increment_monthly_stat(self, stats, login, stat_type):
        """Helper method to increment monthly statistics"""
        if login not in stats:
            stats[login] = {
                "commits": 0,
                "issues_opened": 0,
                "issues_closed": 0,
                "pull_requests": 0,
                "comments": 0,
            }
        stats[login][stat_type] += 1

    def store_monthly_stats(self, repo, month_start, monthly_stats):
        """Store monthly statistics in the database"""
        with transaction.atomic():
            # Delete existing monthly stat for this month if exists
            ContributorStats.objects.filter(repo=repo, granularity="month", date=month_start).delete()

            # Create new monthly stats
            for login, stats in monthly_stats.items():
                # First get or create the contributor
                contributor, _ = self.get_or_create_contributor(login)

                # Create the monthly stat record with the contributor object
                ContributorStats.objects.create(
                    contributor=contributor,
                    repo=repo,
                    date=month_start,
                    granularity="month",
                    **stats,
                )

    def get_or_create_contributor(self, login):
        """Get or create a contributor record"""
        # Make a request to get contributor details from GitHub
        response = requests.get(
            f"https://api.github.com/users/{login}",
            headers={"Authorization": f"token {settings.GITHUB_TOKEN}"},
        )

        if response.status_code == 200:
            data = response.json()
            return Contributor.objects.get_or_create(
                github_id=data["id"],
                defaults={
                    "name": login,
                    "github_url": data["html_url"],
                    "avatar_url": data["avatar_url"],
                    "contributor_type": "User" if not data.get("type") == "Bot" else "Bot",
                    "contributions": 0,  # This will be updated later
                },
            )
        else:
            # Fallback to creating with minimal information
            return Contributor.objects.get_or_create(
                name=login,
                defaults={
                    "github_id": 0,
                    "github_url": f"https://github.com/{login}",
                    "avatar_url": "",
                    "contributor_type": "User",
                    "contributions": 0,
                },
            )
