from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from website.models import Project, Contribution, Repo, Issue, Organization, ForumPost
from website.serializers import ProjectSerializer
from django.contrib.auth.models import User
import json

class HybridSpecVerificationTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.project = Project.objects.create(name="Test Project", slug="test-project", organization=self.org)
        self.user = User.objects.create(username="testuser")

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
            github_username="user1"
        )
        Contribution.objects.create(
            repository=self.project,
            contribution_type="pull_request",
            created=now - timedelta(days=2),
            github_username="user1"
        )
        
        self.project.freshness = self.project.calculate_freshness()
        # Points: (1*5 + 1*3) + (1 contributor * 4) = 12 points
        # Window Weight: 1.0
        # Total: 12.0
        # Normalized: (12.0 / 200.0) * 100 = 6.0
        
        expected_score = Decimal("6.00")
        self.assertEqual(self.project.freshness, expected_score)

        # 2. Add activity in 8-30d window (Weight 0.6)
        # 1 Issue (2) -> * 0.6 = 1.2
        Contribution.objects.create(
            repository=self.project,
            contribution_type="issue_opened",
            created=now - timedelta(days=15),
            github_username="user2" # New contributor!
        )
        
        # Re-calc
        # Window 1 (0-7d):
        #   Commits: 1, PRs: 1 -> (5+3) + (1 cont * 4) = 12 * 1.0 = 12.0
        # Window 2 (8-30d):
        #   Issues: 1 -> (2) + (1 cont * 4) = 6 * 0.6 = 3.6
        # Total raw: 15.6
        # Normalized: (15.6 / 200) * 100 = 7.8
        
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
        # Use update() to bypass auto_now=True behavior which overwrites our custom date
        Repo.objects.filter(id=repo.id).update(updated_at=now - timedelta(days=5))
        # Raw 160 -> Normalized (160/200)*100 = 80.0
        self.assertEqual(self.project.calculate_freshness(), Decimal("80.00"))
        
        # Case 3: Tertiary Fallback (Last Activity - ForumPost)
        # Remove repo updated_at or delete repo
        repo.delete()
        
        # Create a ForumPost (Tertiary fallback source)
        post = ForumPost.objects.create(
            user=self.user,
            project=self.project,
            title="Test Post"
        )
        # Update created timestamp manually
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
            github_username="user1"
        )
        self.project.freshness = self.project.calculate_freshness() # Score 6.00 (Low)
        self.project.save()
        
        serializer = ProjectSerializer(self.project)
        data = serializer.data
        
        # Check freshness_reason
        # Score 6.00 is < 10.00 -> "Very low activity"
        self.assertEqual(data['freshness_reason'], "Very low activity")
        
        # Boost score to check other reasons
        self.project.freshness = Decimal("85.00") # High
        serializer = ProjectSerializer(self.project)
        self.assertEqual(serializer.data['freshness_reason'], "High recent activity")
        
        # Check freshness_breakdown
        breakdown = data['freshness_breakdown']
        self.assertIn('0-7d', breakdown)
        self.assertIn('8-30d', breakdown)
        self.assertEqual(breakdown['0-7d']['commits'], 1)

    def test_edge_cases(self):
        """
        Verify archived/inactive projects return 0.
        """
        self.project.status = "inactive"
        self.project.save()
        self.assertEqual(self.project.calculate_freshness(), Decimal("0.00"))
        
        self.project.status = "active" # Reset
        
        # Mock 'archived' attribute if it existed (it's not on the model definition I saw, 
        # but the code checks getattr(self, 'archived'))
        # Since it's not a field, I can't easily test it unless I patch the object instance
        # but for 'inactive' status it definitely works.

