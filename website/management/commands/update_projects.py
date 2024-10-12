import os
import requests
from django.core.management.base import BaseCommand
from django.utils import timezone
from website.models import Project
from apscheduler.schedulers.blocking import BlockingScheduler

class Command(BaseCommand):
    help = "Update projects with their contributors from GitHub and fetch additional data"

    def handle(self, *args, **kwargs):
        scheduler = BlockingScheduler()
        scheduler.add_job(self.update_projects, 'interval', hours=24)
        scheduler.start()

    def update_projects(self):
        projects = Project.objects.prefetch_related("contributors").all()
        for project in projects:
            contributors = Project.get_contributors(None, github_url=project.github_url)
            project.contributors.set(contributors)
            
            # Fetch and update stars, forks, and external links
            stars, forks = project.fetch_stars_and_forks()
            project.stars = stars
            project.forks = forks
            project.external_links = project.fetch_external_links()
            
            # Fetch README, documentation, commit messages, and issue trackers
            readme = self.fetch_readme(project.github_url)
            documentation = self.fetch_documentation(project.github_url)
            commit_messages = self.fetch_commit_messages(project.github_url)
            issue_trackers = self.fetch_issue_trackers(project.github_url)
            
            # Store fetched data in a suitable format for AI analysis
            project.readme = readme
            project.documentation = documentation
            project.commit_messages = commit_messages
            project.issue_trackers = issue_trackers
            
            project.save()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(projects)} projects"))

    def fetch_readme(self, github_url):
        owner_repo = github_url.rstrip("/").split("/")[-2:]
        repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
        url = f"https://api.github.com/repos/{repo_name}/readme"
        response = requests.get(url, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            readme_data = response.json()
            return readme_data.get("content", "")
        return ""

    def fetch_documentation(self, github_url):
        # Placeholder for fetching documentation logic
        return ""

    def fetch_commit_messages(self, github_url):
        owner_repo = github_url.rstrip("/").split("/")[-2:]
        repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
        url = f"https://api.github.com/repos/{repo_name}/commits"
        response = requests.get(url, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            commits_data = response.json()
            commit_messages = [commit["commit"]["message"] for commit in commits_data]
            return commit_messages
        return []

    def fetch_issue_trackers(self, github_url):
        owner_repo = github_url.rstrip("/").split("/")[-2:]
        repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
        url = f"https://api.github.com/repos/{repo_name}/issues"
        response = requests.get(url, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            issues_data = response.json()
            issue_trackers = [issue["title"] for issue in issues_data]
            return issue_trackers
        return []
