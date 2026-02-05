import random
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import (
    Activity,
    Badge,
    Domain,
    GitHubIssue,
    GitHubReview,
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


def random_name():
    """Generate a random name"""
    return f"User_{random_string(8)}"


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


class Command(LoggedBaseCommand):
    help = "Generate sample data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--preserve-superusers",
            action="store_true",
            help="Preserve existing superuser accounts.",
        )
        parser.add_argument(
            "--preserve-user-id",
            action="append",
            type=int,
            default=None,
            help="User ID to preserve (can be provided multiple times).",
        )

    def clear_existing_data(self, preserve_user_ids=None, preserve_superusers=False):
        """Clear all existing data from the models we're generating"""
        self.stdout.write("Clearing existing data...")

        preserve_user_ids = {user_id for user_id in (preserve_user_ids or []) if user_id}
        if preserve_superusers:
            preserve_user_ids.update(User.objects.filter(is_superuser=True).values_list("id", flat=True))

        if preserve_user_ids:
            preserved_users = User.objects.filter(id__in=preserve_user_ids)
            preserved_profiles = UserProfile.objects.filter(user__in=preserved_users)
            preserved_orgs = Organization.objects.filter(
                models.Q(admin__in=preserved_users) | models.Q(managers__in=preserved_users)
            ).distinct()
            preserved_domains = Domain.objects.filter(
                models.Q(organization__in=preserved_orgs) | models.Q(managers__in=preserved_users)
            ).distinct()
            preserved_hunts = Hunt.objects.filter(domain__in=preserved_domains)
            preserved_projects = Project.objects.filter(organization__in=preserved_orgs)
            preserved_repos = Repo.objects.filter(
                models.Q(organization__in=preserved_orgs) | models.Q(project__in=preserved_projects)
            ).distinct()
            preserved_issues = Issue.objects.filter(
                models.Q(user__in=preserved_users)
                | models.Q(team_members__in=preserved_users)
                | models.Q(domain__in=preserved_domains)
                | models.Q(hunt__in=preserved_hunts)
            ).distinct()
            preserved_gh_issues = GitHubIssue.objects.filter(
                models.Q(user_profile__in=preserved_profiles) | models.Q(repo__in=preserved_repos)
            ).distinct()
            preserved_reviews = GitHubReview.objects.filter(
                models.Q(reviewer__in=preserved_profiles) | models.Q(pull_request__in=preserved_gh_issues)
            ).distinct()

            Activity.objects.exclude(user__in=preserved_users).delete()
            Points.objects.exclude(
                models.Q(user__in=preserved_users)
                | models.Q(issue__in=preserved_issues)
                | models.Q(domain__in=preserved_domains)
            ).delete()
            Issue.objects.exclude(id__in=preserved_issues).delete()
            Hunt.objects.exclude(id__in=preserved_hunts).delete()
            Repo.objects.exclude(id__in=preserved_repos).delete()
            Project.objects.exclude(id__in=preserved_projects).delete()
            GitHubIssue.objects.exclude(id__in=preserved_gh_issues).delete()
            GitHubReview.objects.exclude(id__in=preserved_reviews).delete()
            Domain.objects.exclude(id__in=preserved_domains).delete()
            UserBadge.objects.exclude(user__in=preserved_users).delete()
            Organization.objects.exclude(id__in=preserved_orgs).delete()
            return

        # First delete models that depend on other models
        Activity.objects.all().delete()
        Points.objects.all().delete()
        Issue.objects.all().delete()
        Hunt.objects.all().delete()
        Repo.objects.all().delete()
        Project.objects.all().delete()
        GitHubIssue.objects.all().delete()
        GitHubReview.objects.all().delete()
        Domain.objects.all().delete()
        UserBadge.objects.all().delete()
        Badge.objects.all().delete()
        Tag.objects.all().delete()

        # Delete organizations before users to avoid redundant cascades
        Organization.objects.all().delete()

        # Delete users (cascades to profiles), but preserve selected users
        if preserve_user_ids:
            User.objects.exclude(id__in=preserve_user_ids).delete()
        else:
            User.objects.all().delete()

    def create_users(self, count):
        users = []
        used_usernames = set()
        used_emails = set()

        for _ in range(count):
            while True:
                username = f"user_{random_string(8)}"
                email = f"{username}@example.com"
                if username not in used_usernames and email not in used_emails:
                    break

            used_usernames.add(username)
            used_emails.add(email)

            user = User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
                first_name=f"First{random_string(5)}",
                last_name=f"Last{random_string(5)}",
            )
            users.append(user)

        # After all users are created, randomly assign follows
        for user in users:
            other_profiles = [u.userprofile.id for u in users if u.userprofile.id != user.userprofile.id]
            follow_count = random.randint(0, min(5, len(other_profiles)))
            follow_ids = random.sample(other_profiles, k=follow_count)
            user.userprofile.follows.set(follow_ids)

        return users

    def create_organizations(self, count=5):
        orgs = []
        used_names = set()
        used_urls = set()

        for i in range(count):
            while True:
                name = f"Organization {random_string(5)}"
                url = f"https://org-{random_string(8)}.example.com"

                if name not in used_names and url not in used_urls:
                    break

            used_names.add(name)
            used_urls.add(url)

            org = Organization.objects.create(
                name=name,
                description=random_sentence(),
                url=url,  # Using url instead of website field
                email=f"org-{random_string(5)}@example.com",
                # 2/3 chance of being active
                is_active=random.choice([True, True, False]),
                team_points=random.randint(0, 1000),
            )
            orgs.append(org)
        return orgs

    def create_domains(self, organizations, count=20):
        domains = []
        for i in range(count):
            created_date = timezone.now() - timedelta(days=random.randint(1, 365))
            domain = Domain.objects.create(
                name=f"domain{i+1}.example.com",
                url=f"https://domain{i+1}.example.com",
                organization=random.choice(organizations),
                created=created_date,
            )
            domains.append(domain)
        return domains

    def create_issues(self, users, domains, count=50):
        status_choices = ["open", "closed", "in_review"]
        issues = []
        for i in range(count):
            created_date = timezone.now() - timedelta(days=random.randint(1, 180))
            issue = Issue.objects.create(
                user=random.choice(users),
                domain=random.choice(domains),
                url=f"https://example.com/issue/{i+1}",
                description=random_sentence(10),
                status=random.choice(status_choices),
                created=created_date,
            )
            issues.append(issue)
        return issues

    def create_pull_requests(self, users, repos, count=20):
        pull_requests = []
        for i in range(count):
            userProfile = random.choice(users)
            created_date = timezone.now() - timedelta(days=random.randint(1, 180))
            pull_request = GitHubIssue.objects.create(
                issue_id=random.randint(1000000, 9000000),
                title=random_sentence(5),
                url=f"https://example.com/pr/{i+1}",
                created_at=created_date,
                updated_at=created_date + timedelta(days=random.randint(1, 180)),
                repo=random.choice(repos),
                user_profile=userProfile.userprofile,
                is_merged=random.choice([True, False]),
                type="pull_request",
            )
            pull_requests.append(pull_request)
        return pull_requests

    def create_reviews(self, users, pull_requests, count=50):
        reviews = []
        for i in range(count):
            reviewer = random.choice(users)
            created_date = timezone.now() - timedelta(days=random.randint(1, 180))
            review = GitHubReview.objects.create(
                review_id=random.randint(1000000000, 9000000000),
                pull_request=random.choice(pull_requests),
                reviewer=reviewer.userprofile,
                state=random.choice(["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]),
                submitted_at=created_date,
                body=random_sentence(5),
                url=f"https://example.com/review/{i+1}",
            )
            reviews.append(review)
        return reviews

    def create_hunts(self, users, count=10):
        hunts = []
        for i in range(count):
            created_date = timezone.now() - timedelta(days=random.randint(1, 90))
            starts_on = timezone.now() + timedelta(days=random.randint(1, 30))
            end_on = starts_on + timedelta(days=random.randint(30, 90))
            hunt = Hunt.objects.create(
                name=f"Bug Hunt {i+1}",
                description=random_sentence(15),
                prize=random.randint(100, 1000),
                created=created_date,
                starts_on=starts_on,
                end_on=end_on,
                url=f"https://hunt-{i+1}.example.com",
                domain=random.choice(Domain.objects.all()),
                plan="free",
                is_published=True,
            )
            hunts.append(hunt)
        return hunts

    def create_projects(self, organizations, count=15):
        projects = []
        used_names = set()
        used_urls = set()
        statuses = ["flagship", "production", "incubator", "lab", "inactive"]

        for i in range(count):
            while True:
                name = f"Project {random_string(5)}"
                url = f"https://project-{random_string(8)}.example.com"

                if name not in used_names and url not in used_urls:
                    break

            used_names.add(name)
            used_urls.add(url)

            created_date = timezone.now() - timedelta(days=random.randint(1, 180))
            project = Project.objects.create(
                name=name,
                description=random_sentence(12),
                organization=random.choice(organizations),
                url=url,
                created=created_date,
                status=random.choice(statuses),
            )
            projects.append(project)
        return projects

    def create_points(self, users, count=100):
        for _ in range(count):
            created_date = timezone.now() - timedelta(days=random.randint(1, 365))
            Points.objects.create(
                user=random.choice(users),
                score=random.randint(1, 100),
                created=created_date,
            )

    def create_activities(self, users, count=200):
        action_types = ["create", "update", "delete", "signup"]
        content_type = ContentType.objects.get_for_model(Issue)
        issues = Issue.objects.all()

        for _ in range(count):
            issue = random.choice(issues)
            Activity.objects.create(
                user=random.choice(users),
                action_type=random.choice(action_types),
                title=f"Issue {issue.id}",
                description=random_sentence(),
                content_type=content_type,
                object_id=issue.id,
                url=issue.url,
            )

    def create_badges(self, count=10):
        badges = []
        for i in range(count):
            badge = Badge.objects.create(title=f"Badge {i+1}", description=random_sentence(), type="automatic")
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
                    awarded_at=timezone.now() - timedelta(days=days),
                )

    def create_tags(self, count=20):
        tags = []
        for i in range(count):
            tag = Tag.objects.create(name=f"tag_{i+1}")
            tags.append(tag)
        return tags

    def create_repos(self, projects, count=30):
        repos = []

        # Then create repos
        for i in range(count):
            repo = Repo.objects.create(
                name=f"repo_{i+1}",
                description=random_sentence(),
                repo_url=f"https://github.com/org/repo_{i+1}",
                project=random.choice(projects),
                slug=f"repo-{i+1}",
                is_main=random.choice([True, False]),
                is_wiki=random.choice([True, False]),
                stars=random.randint(0, 1000),
                forks=random.randint(0, 500),
                open_issues=random.randint(0, 100),
                total_issues=random.randint(100, 200),
                watchers=random.randint(0, 1000),
                open_pull_requests=random.randint(0, 50),
                primary_language=random.choice(["Python", "JavaScript", "Java", "Go", "Ruby"]),
                license=random.choice(["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"]),
                size=random.randint(1000, 100000),
                commit_count=random.randint(100, 1000),
                contributor_count=random.randint(1, 50),
            )
            repos.append(repo)
        return repos

    def handle(self, *args, **options):
        self.stdout.write("Generating sample data...")

        preserve_user_ids = {user_id for user_id in (options.get("preserve_user_id") or []) if user_id}
        preserve_superusers = bool(options.get("preserve_superusers"))

        self.clear_existing_data(
            preserve_user_ids=preserve_user_ids,
            preserve_superusers=preserve_superusers,
        )

        self.stdout.write("Creating sample users...")
        users = self.create_users(10)
        if preserve_user_ids:
            preserved_users = list(User.objects.filter(id__in=preserve_user_ids))
            users.extend([user for user in preserved_users if user not in users])

        self.stdout.write("Creating organizations...")
        organizations = self.create_organizations(5)

        self.stdout.write("Creating domains...")
        domains = self.create_domains(organizations, 20)

        self.stdout.write("Creating issues...")
        self.create_issues(users, domains, 50)

        self.stdout.write("Creating hunts...")
        self.create_hunts(users, 10)

        self.stdout.write("Creating projects...")
        projects = self.create_projects(organizations, 15)

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
        repos = self.create_repos(projects, 30)

        self.stdout.write("Creating PRs...")
        pull_requests = self.create_pull_requests(users, repos, 30)

        self.stdout.write("Creating Reviews...")
        self.create_reviews(users, pull_requests, 90)

        self.stdout.write(self.style.SUCCESS("Done!"))
