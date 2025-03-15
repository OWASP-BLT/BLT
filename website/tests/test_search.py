from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from website.models import Domain, Issue, Organization, Project, Repo
from website.views.core import search


class SearchViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.organization = Organization.objects.create(name="Test Org", slug="test-org")

        # Update the auto-created UserProfile instead of creating a new one
        self.user.userprofile.role = "Tester"
        self.user.userprofile.team = self.organization
        self.user.userprofile.save()

        self.domain = Domain.objects.create(name="example.com", url="https://example.com")
        self.project = Project.objects.create(name="Test Project", organization=self.organization)
        self.repo = Repo.objects.create(name="Test Repo", project=self.project)
        self.issue = Issue.objects.create(
            user=self.user, url="https://example.com/issue", description="Test issue", domain=self.domain
        )

    def test_search_all(self):
        """Test search with type='all' returns results from all models"""
        request = self.factory.get(reverse("search") + "?query=test&type=all")
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Org", str(response.content))
        self.assertIn("Test Project", str(response.content))
        self.assertIn("Test Repo", str(response.content))
        self.assertIn("Test issue", str(response.content))
        self.assertIn("testuser", str(response.content))

    def test_search_issues(self):
        """Test search with type='issues' returns only issues"""
        request = self.factory.get(reverse("search") + "?query=test&type=issues")
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test issue", str(response.content))

    def test_search_no_query(self):
        """Test search with no query parameter returns empty template"""
        request = self.factory.get(reverse("search"))
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)

    def test_search_empty_query(self):
        """Test search with empty query returns empty results"""
        request = self.factory.get(reverse("search") + "?query=")
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)

