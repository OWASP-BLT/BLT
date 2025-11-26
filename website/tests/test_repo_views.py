from django.test import RequestFactory, TestCase

from website.views.repo import RepoListView

from ..models import Organization, Repo


class RepoListViewTestCase(TestCase):
    """Test cases for the RepoListView."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        # Create a test organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
        )
        # Create a test repo
        self.repo = Repo.objects.create(
            name="Test Repo",
            slug="test-repo",
            repo_url="https://github.com/test/repo",
            organization=self.organization,
        )

    def test_repo_list_with_valid_organization(self):
        """Test that repo_list works with a valid organization ID."""
        request = self.factory.get("/repo_list/", {"organization": str(self.organization.id)})
        view = RepoListView()
        view.request = request
        queryset = view.get_queryset()
        self.assertIn(self.repo, queryset)

    def test_repo_list_with_empty_organization(self):
        """Test that repo_list handles empty organization parameter gracefully."""
        # Test with empty string
        request = self.factory.get("/repo_list/", {"organization": ""})
        view = RepoListView()
        view.request = request
        queryset = view.get_queryset()
        # Should show all repos when organization is empty
        self.assertIn(self.repo, queryset)

    def test_repo_list_with_whitespace_organization(self):
        """Test that repo_list handles whitespace-only organization parameter."""
        # Test with whitespace
        request = self.factory.get("/repo_list/", {"organization": "   "})
        view = RepoListView()
        view.request = request
        queryset = view.get_queryset()
        # Should show all repos when organization is whitespace
        self.assertIn(self.repo, queryset)

    def test_repo_list_with_invalid_organization(self):
        """Test that repo_list raises ValueError for invalid organization ID."""
        # Test with invalid (non-integer) organization ID
        request = self.factory.get("/repo_list/", {"organization": "invalid"})
        view = RepoListView()
        view.request = request
        with self.assertRaises(ValueError) as context:
            view.get_queryset()
        self.assertIn("Invalid organization ID", str(context.exception))

    def test_repo_list_without_organization(self):
        """Test that repo_list works without organization parameter."""
        request = self.factory.get("/repo_list/")
        view = RepoListView()
        view.request = request
        queryset = view.get_queryset()
        # Should show all repos when no organization filter is provided
        self.assertIn(self.repo, queryset)

    def test_repo_list_with_nonexistent_organization(self):
        """Test that repo_list handles non-existent organization ID gracefully."""
        # Test with non-existent organization ID
        request = self.factory.get("/repo_list/", {"organization": "9999"})
        view = RepoListView()
        view.request = request
        queryset = view.get_queryset()
        # Should filter repos but return empty result for non-existent org
        self.assertNotIn(self.repo, queryset)
