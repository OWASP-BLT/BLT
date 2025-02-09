import random
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import (
    Activity,
    Badge,
    Domain,
    Hunt,
    Issue,
    Organization,
    Points,
    Project,
    Repo,
    Tag,
    UserBadge,
    UserProfile,
)


def random_string(length=10):
    """Generate a random string of fixed length"""
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))


def random_sentence(word_count=6):
    """Generate a random sentence"""
    words = [
        "bug",
        "security",
        "issue",
        "vulnerability",
        "patch",
        "fix",
        "error",
        "problem",
        "solution",
        "update",
        "critical",
        "important",
        "minor",
        "major",
        "urgent",
        "low",
        "medium",
        "high",
        "severe",
    ]
    return " ".join(random.choice(words) for _ in range(word_count))


class Command(BaseCommand):
    help = "Generates sample data for all models"

    def create_users(self, count=10):
        users = []
        for i in range(count):
            username = f"user_{i+1}"
            email = f"user{i+1}@example.com"
            user = User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
                first_name=f"First{i+1}",
                last_name=f"Last{i+1}",
            )
            UserProfile.objects.create(user=user, follows=random.sample(users, min(len(users), 3)))
            users.append(user)
        return users

    def create_organizations(self, count=5):
        orgs = []
        for i in range(count):
            org = Organization.objects.create(
                name=f"Organization {i+1}",
                description=random_sentence(),
                email=f"org{i+1}@example.com",
                website=f"https://org{i+1}.example.com",
                is_active=random.choice([True, True, False]),
            )
            orgs.append(org)
        return orgs

    def create_domains(self, organizations, count=20):
        domains = []
        for i in range(count):
            domain = Domain.objects.create(
                name=f"domain{i+1}.example.com",
                url=f"https://domain{i+1}.example.com",
                organization=random.choice(organizations),
                created=timezone.now() - timedelta(days=random.randint(1, 365)),
            )
            domains.append(domain)
        return domains

    def create_issues(self, users, domains, count=50):
        status_choices = ["open", "closed", "in_review"]
        issues = []
        for i in range(count):
            issue = Issue.objects.create(
                user=random.choice(users),
                domain=random.choice(domains),
                url=f"https://example.com/issue/{i+1}",
                description=random_sentence(10),
                status=random.choice(status_choices),
                created=timezone.now() - timedelta(days=random.randint(1, 180)),
            )
            issues.append(issue)
        return issues

    def create_hunts(self, users, count=10):
        hunts = []
        for i in range(count):
            hunt = Hunt.objects.create(
                name=f"Bug Hunt {i+1}",
                description=random_sentence(15),
                prize=random.randint(100, 1000),
                created=timezone.now() - timedelta(days=random.randint(1, 90)),
                end_date=timezone.now() + timedelta(days=random.randint(1, 30)),
            )
            hunt.participants.set(random.sample(users, random.randint(1, 5)))
            hunts.append(hunt)
        return hunts

    def create_projects(self, organizations, count=15):
        projects = []
        for i in range(count):
            project = Project.objects.create(
                name=f"Project {i+1}",
                description=random_sentence(12),
                organization=random.choice(organizations),
                created=timezone.now() - timedelta(days=random.randint(1, 180)),
            )
            projects.append(project)
        return projects

    def create_points(self, users, count=100):
        for _ in range(count):
            Points.objects.create(
                user=random.choice(users),
                score=random.randint(1, 100),
                created=timezone.now() - timedelta(days=random.randint(1, 365)),
            )

    def create_activities(self, users, count=200):
        activity_types = [
            "reported_issue",
            "closed_issue",
            "received_points",
            "joined_hunt",
        ]
        for _ in range(count):
            Activity.objects.create(
                user=random.choice(users),
                activity_type=random.choice(activity_types),
                description=random_sentence(),
                created=timezone.now() - timedelta(days=random.randint(1, 90)),
            )

    def create_badges(self, count=10):
        badges = []
        for i in range(count):
            badge = Badge.objects.create(name=f"Badge {i+1}", description=random_sentence())
            badges.append(badge)
        return badges

    def assign_badges(self, users, badges):
        for user in users:
            user_badges = random.sample(badges, random.randint(1, len(badges)))
            for badge in user_badges:
                days = random.randint(1, 180)
                UserBadge.objects.create(
                    user=user,
                    badge=badge,
                    created=timezone.now() - timedelta(days=days),
                )

    def create_tags(self, count=20):
        tags = []
        for i in range(count):
            tag = Tag.objects.create(name=f"tag_{i+1}", description=random_sentence())
            tags.append(tag)
        return tags

    def create_repos(self, organizations, count=30):
        repos = []
        for i in range(count):
            repo = Repo.objects.create(
                name=f"repo_{i+1}",
                url=f"https://github.com/org/repo_{i+1}",
                organization=random.choice(organizations),
            )
            repos.append(repo)
        return repos

    def handle(self, *args, **kwargs):
        self.stdout.write("Generating sample data...")

        self.stdout.write("Creating users...")
        users = self.create_users(10)

        self.stdout.write("Creating organizations...")
        organizations = self.create_organizations(5)

        self.stdout.write("Creating domains...")
        domains = self.create_domains(organizations, 20)

        self.stdout.write("Creating issues...")
        self.create_issues(users, domains, 50)

        self.stdout.write("Creating hunts...")
        self.create_hunts(users, 10)

        self.stdout.write("Creating projects...")
        self.create_projects(organizations, 15)

        self.stdout.write("Creating points...")
        self.create_points(users, 100)

        self.stdout.write("Creating activities...")
        self.create_activities(users, 200)

        self.stdout.write("Creating badges...")
        badges = self.create_badges(10)

        self.stdout.write("Assigning badges to users...")
        self.assign_badges(users, badges)

        self.stdout.write("Creating tags...")
        self.create_tags(20)

        self.stdout.write("Creating repos...")
        self.create_repos(organizations, 30)

        self.stdout.write(self.style.SUCCESS("Done!"))
