from collections import defaultdict
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import ContributorStats  # Adjust this to your actual model path


class Command(BaseCommand):
    help = "Fetches and updates contributor statistics from GitHub"

    def handle(self, *args, **options):
        # Clear existing records
        ContributorStats.objects.all().delete()

        # Prepare the time range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        since = start_date.isoformat()

        # GitHub repository details
        owner = "OWASP-BLT"
        repo = "BLT"

        # Authentication headers
        headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"}
        # Initialize data structure
        user_stats = defaultdict(
            lambda: {
                "commits": 0,
                "issues_opened": 0,
                "issues_closed": 0,
                "prs": 0,
                "comments": 0,
                "assigned_issues": 0,
            }
        )

        # Fetch and process data
        self.fetch_and_update_data("pulls", user_stats, headers, owner, repo, since, start_date)
        self.fetch_and_update_data(
            "issuesopen", user_stats, headers, owner, repo, since, start_date
        )
        self.fetch_and_update_data(
            "issuesclosed", user_stats, headers, owner, repo, since, start_date
        )
        self.fetch_and_update_data("commits", user_stats, headers, owner, repo, since, start_date)
        self.fetch_and_update_data("comments", user_stats, headers, owner, repo, since, start_date)

        # Save the updated data to the database
        for username, stats in user_stats.items():
            ContributorStats.objects.create(
                username=username,
                commits=stats["commits"],
                issues_opened=stats["issues_opened"],
                issues_closed=stats["issues_closed"],
                prs=stats["prs"],
                comments=stats["comments"],
                assigned_issues=stats["assigned_issues"],
            )

        self.stdout.write(self.style.SUCCESS("Successfully updated contributor stats"))

    def fetch_and_update_data(self, data_type, user_stats, headers, owner, repo, since, start_date):
        # Define URL based on data_type
        if data_type == "pulls":
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&since={since}&per_page=500"
        elif data_type == "issuesopen":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&since={since}&per_page=500"
        elif data_type == "issuesclosed":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=closed&since={since}&per_page=500"
        elif data_type == "commits":
            url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}&per_page=500"
        elif data_type == "comments":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments?since={since}&per_page=200"

        response = requests.get(url, headers=headers)
        items = response.json()

        # Check for errors in response
        if isinstance(items, dict) and items.get("message"):
            raise ValueError(f"Error fetching data from GitHub: {items['message']}")

        # Process each item based on its type
        for item in items:
            if data_type == "pulls":
                user = item["user"]["login"]
                created_at = datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                if created_at >= start_date:
                    user_stats[user]["prs"] += 1
            elif data_type == "issuesopen":
                user = item["user"]["login"]
                if "pull_request" in item:
                    continue
                if item["state"] == "open":
                    user_stats[user]["issues_opened"] += 1
                if item.get("assignee"):
                    user = item["assignee"]["login"]
                    user_stats[user]["assigned_issues"] += 1
            elif data_type == "issuesclosed":
                user = item["user"]["login"]
                if "pull_request" in item:
                    continue
                if item["state"] == "closed":
                    user_stats[user]["issues_closed"] += 1
                if item.get("assignee"):
                    user = item["assignee"]["login"]
                    user_stats[user]["assigned_issues"] += 1
            elif data_type == "commits":
                user = item["author"]["login"]
                user_stats[user]["commits"] += 1
            elif data_type == "comments":
                user = item["user"]["login"]
                user_stats[user]["comments"] += 1
