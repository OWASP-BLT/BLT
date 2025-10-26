from datetime import datetime

import pytz
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Contributor, GitHubComment, Repo, UserProfile


class GitHubCommentLeaderboardTest(TestCase):
    def setUp(self):
        """Set up test data for GitHub comment leaderboard tests."""
        self.client = Client()

        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", email="user1@example.com", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", email="user2@example.com", password="testpass123")

        # UserProfiles are created automatically by signal
        self.profile1 = UserProfile.objects.get(user=self.user1)
        self.profile2 = UserProfile.objects.get(user=self.user2)

        # Create test contributor
        self.contributor = Contributor.objects.create(
            name="testcontributor",
            github_id=12345,
            github_url="https://github.com/testcontributor",
            avatar_url="https://github.com/testcontributor.png",
            contributor_type="User",
            contributions=10,
        )

        # Create test repository
        self.repo = Repo.objects.create(name="BLT", repo_url="https://github.com/OWASP-BLT/BLT")

        # Create test comments
        now = datetime.now(pytz.UTC)

        # User 1 has 3 comments
        for i in range(3):
            GitHubComment.objects.create(
                comment_id=1000 + i,
                user_profile=self.profile1,
                body=f"Test comment {i} by user1",
                comment_type="issue",
                created_at=now,
                updated_at=now,
                url=f"https://github.com/OWASP-BLT/BLT/issues/1#comment-{1000+i}",
                repo=self.repo,
            )

        # User 2 has 5 comments
        for i in range(5):
            GitHubComment.objects.create(
                comment_id=2000 + i,
                user_profile=self.profile2,
                body=f"Test comment {i} by user2",
                comment_type="pull_request",
                created_at=now,
                updated_at=now,
                url=f"https://github.com/OWASP-BLT/BLT/pull/1#comment-{2000+i}",
                repo=self.repo,
            )

        # Contributor has 2 comments
        for i in range(2):
            GitHubComment.objects.create(
                comment_id=3000 + i,
                contributor=self.contributor,
                body=f"Test comment {i} by contributor",
                comment_type="issue",
                created_at=now,
                updated_at=now,
                url=f"https://github.com/OWASP-BLT/BLT/issues/2#comment-{3000+i}",
                repo=self.repo,
            )

    def test_github_comment_model_creation(self):
        """Test that GitHub comment model can be created successfully."""
        comment_count = GitHubComment.objects.count()
        self.assertEqual(comment_count, 10)  # 3 + 5 + 2

    def test_github_comment_model_user_profile_relationship(self):
        """Test that comments are properly associated with user profiles."""
        user1_comments = GitHubComment.objects.filter(user_profile=self.profile1).count()
        user2_comments = GitHubComment.objects.filter(user_profile=self.profile2).count()

        self.assertEqual(user1_comments, 3)
        self.assertEqual(user2_comments, 5)

    def test_github_comment_model_contributor_relationship(self):
        """Test that comments are properly associated with contributors."""
        contributor_comments = GitHubComment.objects.filter(contributor=self.contributor).count()
        self.assertEqual(contributor_comments, 2)

    def test_leaderboard_includes_github_comments(self):
        """Test that the leaderboard page includes GitHub comment leaderboard."""
        url = reverse("leaderboard_global")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")

        # Check that github_comment_leaderboard is in context
        self.assertIn("github_comment_leaderboard", response.context)

        # Verify the leaderboard has data
        leaderboard = response.context["github_comment_leaderboard"]
        self.assertGreater(len(leaderboard), 0)

    def test_leaderboard_comment_counts(self):
        """Test that the leaderboard correctly counts comments per user."""
        url = reverse("leaderboard_global")
        response = self.client.get(url)

        leaderboard = list(response.context["github_comment_leaderboard"])

        # Find user2 in leaderboard (should have most comments)
        user2_entry = None
        for entry in leaderboard:
            if entry["user_profile__user__username"] == "testuser2":
                user2_entry = entry
                break

        self.assertIsNotNone(user2_entry)
        self.assertEqual(user2_entry["total_comments"], 5)

    def test_leaderboard_ordering(self):
        """Test that the leaderboard is ordered by comment count."""
        url = reverse("leaderboard_global")
        response = self.client.get(url)

        leaderboard = list(response.context["github_comment_leaderboard"])

        # Check that leaderboard is ordered by total_comments descending
        if len(leaderboard) > 1:
            for i in range(len(leaderboard) - 1):
                self.assertGreaterEqual(leaderboard[i]["total_comments"], leaderboard[i + 1]["total_comments"])

    def test_github_comment_str_method(self):
        """Test the string representation of GitHubComment."""
        comment = GitHubComment.objects.filter(user_profile=self.profile1).first()
        expected_str = f"Comment #{comment.comment_id} by {self.user1.username}"
        self.assertEqual(str(comment), expected_str)
