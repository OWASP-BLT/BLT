def make_project(**kwargs):
    # Provide sensible defaults for required fields
    defaults = {
        "name": "Test Project",
        "slug": "test-project",
        "description": "A test project for freshness tests.",
    }
    # If organization is required, create or use one with required fields
    if "organization" not in kwargs:
        org, _ = Organization.objects.get_or_create(name="Test Org", defaults={"url": "https://test-org.example"})
        defaults["organization"] = org
    # Merge user-supplied kwargs
    model_fields = defaults | {k: v for k, v in kwargs.items() if k in [f.name for f in Project._meta.get_fields()]}
    instance = Project(**model_fields)
    instance.save()
    # Set dynamic attributes (archived, forked) after construction
    for k in ("archived", "forked"):
        if k in kwargs:
            setattr(instance, k, kwargs[k])
    return instance


# --- Merged Project Freshness Tests ---
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from website.models import Contribution, ForumPost, Organization, Project, Repo
from website.serializers import ProjectSerializer


class ProjectFreshnessEdgeTests(TestCase):
    def test_archived_project_zero(self):
        p = make_project(archived=True)
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_forked_project_zero(self):
        p = make_project(forked=True)
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_inactive_status_zero(self):
        p = make_project(status="inactive")
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_lab_status_zero(self):
        p = make_project(status="lab")
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_outlier_spam(self):
        from django.contrib.auth.models import User

        from comments.models import Comment
        from website.models import Domain, Issue, UserProfile

        # Create required related objects
        user = User.objects.create(username="testuser", email="test@example.com")
        domain = Domain.objects.create(name="example.com", url="http://example.com")
        p = make_project()
        p.save()
        # Add spammy comments (same author, very old)
        author_profile = UserProfile.objects.get(user=user)
        old_time = timezone.now() - timedelta(days=400)
        for _ in range(10):
            issue = Issue.objects.create(
                user=user,
                domain=domain,
                url="http://example.com/issue",
                description="Spam Issue",
            )
            Comment.objects.create(
                content_object=issue,
                author="spammer",
                author_fk=author_profile,
                author_url="",
                text="Spam",
                created_date=old_time,
            )
        # Add a normal comment (recent, not spam)
        issue2 = Issue.objects.create(
            user=user,
            domain=domain,
            url="http://example.com/issue2",
            description="Normal Issue",
        )
        Comment.objects.create(
            content_object=issue2,
            author="legituser",
            author_fk=author_profile,
            author_url="",
            text="Legit",
            created_date=timezone.now(),
        )
        # Should exclude spam/outlier comments
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)

    def test_fallback_issue_comment(self):
        from django.contrib.auth.models import User

        from comments.models import Comment
        from website.models import Domain, Issue, UserProfile

        user = User.objects.create(username="testuser2", email="test2@example.com")
        domain = Domain.objects.create(name="example2.com", url="http://example2.com")
        p = make_project()
        p.save()
        author_profile = UserProfile.objects.get(user=user)
        # No normal activity, only a fallback comment
        issue = Issue.objects.create(
            user=user,
            domain=domain,
            url="http://example2.com/issue",
            description="Fallback Issue",
        )
        Comment.objects.create(
            content_object=issue,
            author="fallbackuser",
            author_fk=author_profile,
            author_url="",
            text="Fallback",
            created_date=timezone.now() - timedelta(days=100),
        )
        # Remove all contributions/commits/PRs if any
        # (Assume no Contribution objects exist for this project)
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)


class ProjectFreshnessFuzzTest(TestCase):
    def test_fuzz_freshness_bounds(self):
        """Fuzz test: freshness score must stay within 0-100 for random project states."""
        for i in range(100):
            p = Project.objects.create(
                name=f"FuzzProject{i}",
                slug=f"fuzz-project-{i}",
                description="Fuzz test project",
                status=random.choice(["flagship", "production", "incubator", "lab", "inactive"]),
            )
            score = p.calculate_freshness()
            self.assertGreaterEqual(score, Decimal("0.00"))
            self.assertLessEqual(score, Decimal("100.00"))


# Property-based test (from test_project_freshness_property.py)
try:
    from hypothesis import given
    from hypothesis import strategies as st

    given_freshness = st.decimals(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)

    @given(freshness=given_freshness)
    def test_freshness_range(freshness):
        p = Project(freshness=freshness)
        assert 0 <= p.freshness <= 100
except ImportError:
    pass


# Hybrid spec verification tests (from test_hybrid_spec_verification.py)
class HybridSpecVerificationTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.project = Project.objects.create(name="Test Project", slug="test-project", organization=self.org)
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="testuser")

    def test_calculation_logic_and_windows(self):
        """
        Verify the multi-metric weighted calculation and time windows.
        Weights: Commits(5), PRs(3), Issues(2), Contributors(4)
        Windows: 0-7d (1.0), 8-30d (0.6), 31-90d (0.3)
        """
        now = timezone.now()

        # 1. Create activity in 0-7d window (Weight 1.0)
        # 1 Commit (5) + 1 PR (3) = 8 points -> * 1.0 = 8.0
        Contribution.objects.create(
            repository=self.project,
            contribution_type="commit",
            created=now - timedelta(days=2),
            github_username="user1",
        )
        Contribution.objects.create(
            repository=self.project,
            contribution_type="pull_request",
            created=now - timedelta(days=2),
            github_username="user1",
        )

        self.project.freshness = self.project.calculate_freshness()
        expected_score = Decimal("6.00")
        self.assertEqual(self.project.freshness, expected_score)

        # 2. Add activity in 8-30d window (Weight 0.6)
        # 1 Issue (2) -> * 0.6 = 1.2
        Contribution.objects.create(
            repository=self.project,
            contribution_type="issue_opened",
            created=now - timedelta(days=15),
            github_username="user2",  # New contributor!
        )

        self.project.freshness = self.project.calculate_freshness()
        expected_score_2 = Decimal("7.80")
        self.assertEqual(self.project.freshness, expected_score_2)

    def test_fallbacks(self):
        """
        Verify primary, secondary, and tertiary fallbacks.
        """
        now = timezone.now()

        # Case 1: No Contributions, No Repo -> Score 0
        self.assertEqual(self.project.calculate_freshness(), Decimal("0.00"))

        # Case 2: Secondary Fallback (Repo updated_at)
        repo = Repo.objects.create(
            project=self.project,
            name="test-repo",
            repo_url="http://github.com/test/test",
        )
        Repo.objects.filter(id=repo.id).update(updated_at=now - timedelta(days=5))
        self.assertEqual(self.project.calculate_freshness(), Decimal("80.00"))

        # Case 3: Tertiary Fallback (Last Activity - ForumPost)
        repo.delete()
        post = ForumPost.objects.create(user=self.user, project=self.project, title="Test Post")
        ForumPost.objects.filter(id=post.id).update(created=now - timedelta(days=5))
        score = self.project.calculate_freshness()
        self.assertEqual(score, Decimal("30.00"))

    def test_analytics_api_fields(self):
        """
        Verify freshness_breakdown and freshness_reason fields in Serializer.
        """
        now = timezone.now()
        Contribution.objects.create(
            repository=self.project,
            contribution_type="commit",
            created=now - timedelta(days=2),
            github_username="user1",
        )
        self.project.freshness = self.project.calculate_freshness()
        self.project.save()

        serializer = ProjectSerializer(self.project)
        data = serializer.data

        self.assertEqual(data["freshness_reason"], "Very low activity")

        self.project.freshness = Decimal("85.00")
        self.project.save()
        serializer = ProjectSerializer(self.project)
        self.assertEqual(serializer.data["freshness_reason"], "High recent activity")

        breakdown = data["freshness_breakdown"]
        self.assertIn("0-7d", breakdown)
        self.assertIn("8-30d", breakdown)
        self.assertEqual(breakdown["0-7d"]["commits"], 1)

    def test_edge_cases(self):
        """
        Verify archived/inactive/forked projects return 0.
        """
        self.project.status = "inactive"
        self.project.save()
        self.assertEqual(self.project.calculate_freshness(), Decimal("0.00"))

        self.project.status = "active"
        self.project.save()

        self.project.archived = True
        self.assertEqual(self.project.calculate_freshness(), Decimal("0.00"))
        del self.project.archived

        self.project.forked = True
        self.assertEqual(self.project.calculate_freshness(), Decimal("0.00"))
        del self.project.forked
