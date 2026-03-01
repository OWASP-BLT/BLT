"""
Seed sample OWASP project data for testing the leaderboard
"""
import random

from django.core.management.base import BaseCommand

from website.models import Project, Repo


class Command(BaseCommand):
    help = "Seeds sample OWASP project data for leaderboard testing"

    def handle(self, *args, **kwargs):
        self.stdout.write("Creating sample projects...")

        # Sample OWASP projects with realistic data
        sample_projects = [
            {
                "name": "OWASP ZAP",
                "slug": "zap",
                "description": "The world's most widely used web app scanner",
                "status": "flagship",
                "repos": [
                    {
                        "name": "zaproxy",
                        "stars": 12453,
                        "forks": 2234,
                        "open_issues": 89,
                        "commits": 15234,
                        "contributors": 234,
                    },
                ],
            },
            {
                "name": "OWASP Juice Shop",
                "slug": "juice-shop",
                "description": "Probably the most modern and sophisticated insecure web application",
                "status": "flagship",
                "repos": [
                    {
                        "name": "juice-shop",
                        "stars": 9876,
                        "forks": 7890,
                        "open_issues": 45,
                        "commits": 8765,
                        "contributors": 156,
                    },
                ],
            },
            {
                "name": "OWASP ModSecurity",
                "slug": "modsecurity",
                "description": "Open source web application firewall",
                "status": "flagship",
                "repos": [
                    {
                        "name": "ModSecurity",
                        "stars": 7654,
                        "forks": 1543,
                        "open_issues": 123,
                        "commits": 12345,
                        "contributors": 98,
                    },
                ],
            },
            {
                "name": "OWASP Dependency-Check",
                "slug": "dependency-check",
                "description": "Software Composition Analysis tool",
                "status": "production",
                "repos": [
                    {
                        "name": "DependencyCheck",
                        "stars": 5432,
                        "forks": 987,
                        "open_issues": 67,
                        "commits": 6789,
                        "contributors": 87,
                    },
                ],
            },
            {
                "name": "OWASP Top 10",
                "slug": "top-10",
                "description": "Standard awareness document for developers and web application security",
                "status": "flagship",
                "repos": [
                    {
                        "name": "Top10",
                        "stars": 4321,
                        "forks": 1234,
                        "open_issues": 12,
                        "commits": 543,
                        "contributors": 45,
                    },
                ],
            },
            {
                "name": "OWASP ASVS",
                "slug": "asvs",
                "description": "Application Security Verification Standard",
                "status": "flagship",
                "repos": [
                    {
                        "name": "ASVS",
                        "stars": 3456,
                        "forks": 876,
                        "open_issues": 23,
                        "commits": 2345,
                        "contributors": 67,
                    },
                ],
            },
            {
                "name": "OWASP Security Shepherd",
                "slug": "security-shepherd",
                "description": "Web and mobile application security training platform",
                "status": "production",
                "repos": [
                    {
                        "name": "SecurityShepherd",
                        "stars": 2987,
                        "forks": 654,
                        "open_issues": 34,
                        "commits": 4567,
                        "contributors": 54,
                    },
                ],
            },
            {
                "name": "OWASP Amass",
                "slug": "amass",
                "description": "In-depth attack surface mapping and asset discovery",
                "status": "production",
                "repos": [
                    {
                        "name": "Amass",
                        "stars": 8765,
                        "forks": 1432,
                        "open_issues": 56,
                        "commits": 3456,
                        "contributors": 76,
                    },
                ],
            },
            {
                "name": "OWASP Cheat Sheet Series",
                "slug": "cheat-sheet-series",
                "description": "Concise collection of high value information on specific application security topics",
                "status": "production",
                "repos": [
                    {
                        "name": "CheatSheetSeries",
                        "stars": 23456,
                        "forks": 4567,
                        "open_issues": 78,
                        "commits": 7890,
                        "contributors": 234,
                    },
                ],
            },
            {
                "name": "OWASP WebGoat",
                "slug": "webgoat",
                "description": "Deliberately insecure application for teaching web application security",
                "status": "production",
                "repos": [
                    {
                        "name": "WebGoat",
                        "stars": 6543,
                        "forks": 3456,
                        "open_issues": 45,
                        "commits": 5678,
                        "contributors": 123,
                    },
                ],
            },
        ]

        created_count = 0
        for proj_data in sample_projects:
            repos_data = proj_data.pop("repos")

            project, created = Project.objects.get_or_create(slug=proj_data["slug"], defaults=proj_data)

            if created:
                created_count += 1
                self.stdout.write(f"  Created project: {project.name}")

                # Create repos for this project
                for repo_data in repos_data:
                    Repo.objects.create(
                        project=project,
                        name=repo_data["name"],
                        repo_url=f'https://github.com/OWASP/{repo_data["name"]}',
                        stars=repo_data["stars"],
                        forks=repo_data["forks"],
                        open_issues=repo_data["open_issues"],
                        commit_count=repo_data["commits"],
                        contributor_count=repo_data["contributors"],
                        watchers=random.randint(100, 500),
                        open_pull_requests=random.randint(5, 20),
                        closed_pull_requests=random.randint(100, 500),
                    )

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created {created_count} projects with repos"))
        self.stdout.write(f"Total projects: {Project.objects.count()}")
        self.stdout.write(f"Total repos: {Repo.objects.count()}")
