"""
Tests for Project freshness calculation functionality.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from website.models import Organization, Project, Repo


class ProjectFreshnessCalculationTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Organization", url="https://test.org")
        self.project = Project.objects.create(
            name="Test Project", organization=self.org, url="https://github.com/test/project"
        )
        self.now = timezone.now()

    def test_freshness_no_repos(self):
        freshness = self.project.calculate_freshness()
        self.assertEqual(freshness, 0.0)

    def test_freshness_all_archived_repos(self):
        Repo.objects.create(
            project=self.project,
            name="archived-repo",
            repo_url="https://github.com/test/archived",
            is_archived=True,
            last_commit_date=self.now - timedelta(days=1),
        )
        freshness = self.project.calculate_freshness()
        self.assertEqual(freshness, 0.0)

    def test_freshness_ignores_archived_and_counts_active(self):
        Repo.objects.create(
            project=self.project,
            name="active",
            repo_url="https://github.com/test/active",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=2),
        )
        Repo.objects.create(
            project=self.project,
            name="archived",
            repo_url="https://github.com/test/archived",
            is_archived=True,
            last_commit_date=self.now - timedelta(days=1),
        )

        freshness = self.project.calculate_freshness()
        self.assertGreater(freshness, 0.0)

    def test_freshness_exact_boundary_7_days(self):
        Repo.objects.create(
            project=self.project,
            name="boundary-7",
            repo_url="https://github.com/test/boundary-7",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=6, hours=23),
        )
        freshness = self.project.calculate_freshness()
        self.assertEqual(freshness, 5.0)

    def test_freshness_max_score_capping(self):
        for i in range(25):
            Repo.objects.create(
                project=self.project,
                name=f"repo-{i}",
                repo_url=f"https://github.com/test/repo-{i}",
                is_archived=False,
                last_commit_date=self.now - timedelta(days=1),
            )
        freshness = self.project.calculate_freshness()
        self.assertEqual(freshness, 100.0)

    def test_freshness_repo_with_null_last_commit_date(self):
        """
        Repos with last_commit_date=None should be excluded from freshness calculation.
        """
        Repo.objects.create(
            project=self.project,
            name="no-commit-data",
            repo_url="https://github.com/test/no-commit",
            is_archived=False,
            last_commit_date=None,
        )

        freshness = self.project.calculate_freshness()
        self.assertEqual(freshness, 0.0)

    def test_freshness_multiple_repos_across_time_windows(self):
        """
        Test freshness calculation with repos spanning 7/30/90 day windows.
        """
        # 2 repos in last 7 days
        Repo.objects.create(
            project=self.project,
            name="recent-1",
            repo_url="https://github.com/test/recent-1",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=2),
        )
        Repo.objects.create(
            project=self.project,
            name="recent-2",
            repo_url="https://github.com/test/recent-2",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=5),
        )

        # 1 repo in 8–30 day window
        Repo.objects.create(
            project=self.project,
            name="medium",
            repo_url="https://github.com/test/medium",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=15),
        )

        # 1 repo in 31–90 day window
        Repo.objects.create(
            project=self.project,
            name="older",
            repo_url="https://github.com/test/older",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=45),
        )

        freshness = self.project.calculate_freshness()

        # raw_score = 2*1.0 + 1*0.6 + 1*0.3 = 2.9
        # freshness = (2.9 / 20) * 100 = 14.5
        self.assertEqual(freshness, 14.5)
