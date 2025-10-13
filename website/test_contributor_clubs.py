from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from website.models import UserProfile, GitHubIssue, Repo, Organization


class ContributorClubsTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.userprofile = UserProfile.objects.get(user=self.user)
        self.userprofile.github_url = 'https://github.com/testuser'
        self.userprofile.save()
        
        # Create test organization and repo
        self.org = Organization.objects.create(name='test-org')
        self.repo = Repo.objects.create(
            name='test-repo',
            url='https://github.com/test-org/test-repo',
            organization=self.org
        )
        
    def test_milestone_clubs_calculation(self):
        """Test milestone club membership calculation"""
        # Test 10 club
        self.userprofile.merged_pr_count = 15
        self.userprofile.calculate_club_memberships()
        self.assertTrue(self.userprofile.ten_club_member)
        self.assertFalse(self.userprofile.fifty_club_member)
        self.assertFalse(self.userprofile.hundred_club_member)
        
        # Test 50 club
        self.userprofile.merged_pr_count = 75
        self.userprofile.calculate_club_memberships()
        self.assertTrue(self.userprofile.ten_club_member)
        self.assertTrue(self.userprofile.fifty_club_member)
        self.assertFalse(self.userprofile.hundred_club_member)
        
        # Test 100 club
        self.userprofile.merged_pr_count = 150
        self.userprofile.calculate_club_memberships()
        self.assertTrue(self.userprofile.ten_club_member)
        self.assertTrue(self.userprofile.fifty_club_member)
        self.assertTrue(self.userprofile.hundred_club_member)
        
    def test_weekly_club_calculation(self):
        """Test weekly club membership calculation"""
        now = timezone.now()
        
        # Create a merged PR from 3 days ago (should qualify for weekly club)
        GitHubIssue.objects.create(
            issue_id=1,
            title='Test PR',
            state='closed',
            type='pull_request',
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
            merged_at=now - timedelta(days=3),
            is_merged=True,
            url='https://github.com/test-org/test-repo/pull/1',
            repo=self.repo,
            user_profile=self.userprofile
        )
        
        self.userprofile.calculate_club_memberships()
        self.assertTrue(self.userprofile.weekly_club_member)
        
    def test_monthly_club_calculation(self):
        """Test monthly club membership calculation"""
        now = timezone.now()
        
        # Create a merged PR from 20 days ago (should qualify for monthly club but not weekly)
        GitHubIssue.objects.create(
            issue_id=2,
            title='Test PR 2',
            state='closed',
            type='pull_request',
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20),
            merged_at=now - timedelta(days=20),
            is_merged=True,
            url='https://github.com/test-org/test-repo/pull/2',
            repo=self.repo,
            user_profile=self.userprofile
        )
        
        self.userprofile.calculate_club_memberships()
        self.assertFalse(self.userprofile.weekly_club_member)
        self.assertTrue(self.userprofile.monthly_club_member)
        
    def test_no_clubs_for_old_prs(self):
        """Test that old PRs don't qualify for activity clubs"""
        now = timezone.now()
        
        # Create a merged PR from 40 days ago (should not qualify for any activity club)
        GitHubIssue.objects.create(
            issue_id=3,
            title='Test PR 3',
            state='closed',
            type='pull_request',
            created_at=now - timedelta(days=40),
            updated_at=now - timedelta(days=40),
            merged_at=now - timedelta(days=40),
            is_merged=True,
            url='https://github.com/test-org/test-repo/pull/3',
            repo=self.repo,
            user_profile=self.userprofile
        )
        
        self.userprofile.calculate_club_memberships()
        self.assertFalse(self.userprofile.weekly_club_member)
        self.assertFalse(self.userprofile.monthly_club_member)
        
    def test_no_clubs_without_github_url(self):
        """Test that users without GitHub URL don't get activity clubs"""
        self.userprofile.github_url = None
        self.userprofile.save()
        
        self.userprofile.calculate_club_memberships()
        self.assertFalse(self.userprofile.weekly_club_member)
        self.assertFalse(self.userprofile.monthly_club_member)