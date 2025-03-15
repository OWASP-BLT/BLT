import random
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
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

    def clear_existing_data(self):
        """Clear all existing data from the models we're generating"""
        self.stdout.write("Clearing existing data...")

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

        # Delete users (cascades to profiles)
        User.objects.all().delete()

        # Finally delete organizations
        Organization.objects.all().delete()

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

    def create_repos(self, organizations, count=30):
        repos = []
        projects = []

        # First create projects
        for i in range(count // 2):  # Create half as many projects as repos
            project = Project.objects.create(
                name=f"Project {i+1}",
                description=random_sentence(),
                organization=random.choice(organizations),
                url=f"https://project-{i+1}.example.com",
            )
            projects.append(project)

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

        self.clear_existing_data()

        self.stdout.write("Creating sample users...")
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
        repos = self.create_repos(organizations, 30)

        self.stdout.write("Creating PRs...")
        pull_requests = self.create_pull_requests(users, repos, 30)

        self.stdout.write("Creating Reviews...")
        self.create_reviews(users, pull_requests, 90)

        self.stdout.write(self.style.SUCCESS("Done!"))
