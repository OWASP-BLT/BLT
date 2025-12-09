import unittest.mock as mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from website.models import Project, Repo

User = get_user_model()


class ProjectAggregationTestCase(TestCase):
    """Tests for stars/forks aggregation in Project API endpoints"""

    def setUp(self):
        # ✅ Patch freshness (already correct)
        self.freshness_patcher = mock.patch(
            "website.serializers.ProjectSerializer.get_freshness",
            return_value=None,
        )
        self.freshness_patcher.start()
        self.addCleanup(self.freshness_patcher.stop)

        # ✅ Patch prefetch_related to avoid invalid 'contributors'
        self.prefetch_patcher = mock.patch(
            "website.api.views.Project.objects.prefetch_related",
            return_value=Project.objects.all(),
        )
        self.prefetch_patcher.start()
        self.addCleanup(self.prefetch_patcher.stop)

        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        self.project_with_repos = Project.objects.create(name="Django Framework", description="Web framework")

        Repo.objects.create(
            project=self.project_with_repos,
            repo_url="https://github.com/django/django",
            stars=50000,
            forks=20000,
        )

        Repo.objects.create(
            project=self.project_with_repos,
            repo_url="https://github.com/django/channels",
            stars=5000,
            forks=1000,
        )

        self.project_no_repos = Project.objects.create(name="New Project", description="Just started")

        self.project_low_counts = Project.objects.create(name="Small Project", description="Small community")

        Repo.objects.create(
            project=self.project_low_counts,
            repo_url="https://github.com/user/small",
            stars=10,
            forks=2,
        )

    def test_filter_zero_repo_project_coalesce_behavior(self):
        """Projects with no repos should return 0 stars/forks, not NULL"""
        response = self.client.get("/api/v1/projects/", {"stars": "0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Project with no repos should be included when filtering stars >= 0
        project_names = [p["name"] for p in response.data["results"]]
        self.assertIn(self.project_no_repos.name, project_names)

    def test_filter_stars_gte_semantics(self):
        """Stars filter should use >= semantics"""
        # Filter for projects with 5000+ stars
        response = self.client.get("/api/v1/projects/", {"stars": "5000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project_names = [p["name"] for p in response.data["results"]]
        # Should include project_with_repos (55000 total stars)
        self.assertIn(self.project_with_repos.name, project_names)
        # Should NOT include project_low_counts (10 stars)
        self.assertNotIn(self.project_low_counts.name, project_names)
        # Should NOT include project_no_repos (0 stars)
        self.assertNotIn(self.project_no_repos.name, project_names)

    def test_filter_forks_gte_semantics(self):
        """Forks filter should use >= semantics"""
        response = self.client.get("/api/v1/projects/", {"forks": "1000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project_names = [p["name"] for p in response.data["results"]]
        # Should include project_with_repos (21000 total forks)
        self.assertIn(self.project_with_repos.name, project_names)
        # Should NOT include project_low_counts (2 forks)
        self.assertNotIn(self.project_low_counts.name, project_names)

    def test_filter_combined_stars_and_forks(self):
        """Can filter by both stars and forks simultaneously"""
        response = self.client.get("/api/v1/projects/", {"stars": "50000", "forks": "20000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project_names = [p["name"] for p in response.data["results"]]
        self.assertIn(self.project_with_repos.name, project_names)
        self.assertNotIn(self.project_low_counts.name, project_names)

    def test_filter_invalid_stars_negative(self):
        """Negative stars should return 400 error"""
        response = self.client.get("/api/v1/projects/", {"stars": "-100"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("non-negative", response.data["error"].lower())

    def test_filter_invalid_forks_negative(self):
        """Negative forks should return 400 error"""
        response = self.client.get("/api/v1/projects/", {"forks": "-50"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("non-negative", response.data["error"].lower())

    def test_filter_invalid_stars_non_integer(self):
        """Non-integer stars should return 400 error"""
        response = self.client.get("/api/v1/projects/", {"stars": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("integer", response.data["error"].lower())

    def test_filter_invalid_forks_non_integer(self):
        """Non-integer forks should return 400 error"""
        response = self.client.get("/api/v1/projects/", {"forks": "12.5"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_filter_edge_case_exact_match(self):
        """Filter should match projects with exactly the specified value (>= semantics)"""
        response = self.client.get("/api/v1/projects/", {"stars": "10"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project_names = [p["name"] for p in response.data["results"]]
        # Should include project_low_counts with exactly 10 stars
        self.assertIn(self.project_low_counts.name, project_names)

    def test_filter_aggregation_across_multiple_repos(self):
        """Verify stars/forks are properly aggregated from multiple repos"""
        # Create another repo for the first project
        Repo.objects.create(
            project=self.project_with_repos, repo_url="https://github.com/django/asgiref", stars=1000, forks=200
        )
        # New total: 56000 stars, 21200 forks

        response = self.client.get("/api/v1/projects/", {"stars": "56000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        project_names = [p["name"] for p in response.data["results"]]
        self.assertIn(self.project_with_repos.name, project_names)

    def test_filter_zero_values_valid(self):
        """Zero is a valid filter value"""
        response = self.client.get("/api/v1/projects/", {"stars": "0", "forks": "0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all projects (all have >= 0 stars/forks)
        self.assertEqual(len(response.data["results"]), 3)
