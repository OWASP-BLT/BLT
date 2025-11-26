from django.test import Client, TestCase
from django.urls import reverse

from website.models import Organization, Project, Repo, User


class ProjectCompactViewTestCase(TestCase):
    """Test cases for the project compact list view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass123")

        # Create test organization
        self.org = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            url="https://example.com",
            admin=self.user,
        )

        # Create test projects
        self.project1 = Project.objects.create(
            name="Test Project 1",
            slug="test-project-1",
            description="Test project description",
            organization=self.org,
            status="production",
            url="https://example.com/project1",
            slack="https://slack.com/test1",
            slack_channel="#general",
            twitter="@testproject",
        )

        self.project2 = Project.objects.create(
            name="Test Project 2",
            slug="test-project-2",
            description="Another test project",
            status="incubator",
        )

        # Create test repos
        self.repo1 = Repo.objects.create(
            name="Test Repo 1",
            slug="test-repo-1",
            repo_url="https://github.com/test/repo1",
            project=self.project1,
            stars=100,
            forks=50,
            total_issues=10,
        )

        self.repo2 = Repo.objects.create(
            name="Test Repo 2",
            slug="test-repo-2",
            repo_url="https://github.com/test/repo2",
            project=self.project1,
            stars=200,
            forks=75,
            total_issues=20,
        )

    def test_compact_view_url_exists(self):
        """Test that the compact view URL exists and is accessible"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertEqual(response.status_code, 200)

    def test_compact_view_uses_correct_template(self):
        """Test that the compact view uses the correct template"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertTemplateUsed(response, "projects/project_compact_list.html")

    def test_compact_view_displays_projects(self):
        """Test that projects are displayed in the compact view"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertContains(response, "Test Project 1")
        self.assertContains(response, "Test Project 2")

    def test_compact_view_displays_organization(self):
        """Test that organization names are displayed"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertContains(response, "Test Organization")

    def test_compact_view_displays_slack_channel(self):
        """Test that slack channels are displayed"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertContains(response, "#general")

    def test_compact_view_displays_stats(self):
        """Test that project stats are aggregated and displayed"""
        response = self.client.get(reverse("project_compact_list"))
        # Project 1 has 2 repos: 100+200 stars, 50+75 forks, 10+20 issues
        self.assertContains(response, "300")  # Total stars
        self.assertContains(response, "125")  # Total forks
        self.assertContains(response, "30")  # Total issues

    def test_compact_view_sorting_by_name(self):
        """Test sorting projects by name"""
        response = self.client.get(reverse("project_compact_list") + "?sort=name&order=asc")
        self.assertEqual(response.status_code, 200)
        # Check that projects are in the correct order
        content = response.content.decode()
        pos1 = content.find("Test Project 1")
        pos2 = content.find("Test Project 2")
        self.assertLess(pos1, pos2)

    def test_compact_view_search_functionality(self):
        """Test search functionality in compact view"""
        response = self.client.get(reverse("project_compact_list") + "?search=Test Project 1")
        self.assertContains(response, "Test Project 1")
        self.assertNotContains(response, "Test Project 2")

    def test_compact_view_organization_filter(self):
        """Test filtering by organization"""
        response = self.client.get(reverse("project_compact_list") + f"?organization={self.org.id}")
        self.assertContains(response, "Test Project 1")
        # Project 2 doesn't have an organization, so it shouldn't appear
        self.assertNotContains(response, "Test Project 2")

    def test_compact_view_pagination_exists(self):
        """Test that pagination context is provided"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertIn("projects_with_stats", response.context)
        self.assertIn("page_obj", response.context)

    def test_compact_view_has_view_switcher(self):
        """Test that view switcher links are present"""
        response = self.client.get(reverse("project_compact_list"))
        self.assertContains(response, "Card View")
        self.assertContains(response, reverse("project_list"))
