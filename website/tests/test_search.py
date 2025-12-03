from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from website.models import Domain, Issue, Organization, Project, Repo, SearchHistory
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

    def test_search_logs_history_for_authenticated_user(self):
        """Test that search queries are logged for authenticated users"""
        request = self.factory.get(reverse("search") + "?query=test&type=all")
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)

        # Check that search history was created
        search_history = SearchHistory.objects.filter(user=self.user, query="test", search_type="all")
        self.assertEqual(search_history.count(), 1)
        self.assertEqual(search_history.first().query, "test")
        self.assertEqual(search_history.first().search_type, "all")

    def test_search_does_not_log_duplicate_consecutive_searches(self):
        """Test that duplicate consecutive searches are not logged"""
        request1 = self.factory.get(reverse("search") + "?query=test&type=all")
        request1.user = self.user
        search(request1)

        request2 = self.factory.get(reverse("search") + "?query=test&type=all")
        request2.user = self.user
        search(request2)

        # Should only have one entry
        search_history = SearchHistory.objects.filter(user=self.user, query="test", search_type="all")
        self.assertEqual(search_history.count(), 1)

    def test_search_logs_different_queries(self):
        """Test that different queries are logged separately"""
        request1 = self.factory.get(reverse("search") + "?query=test1&type=all")
        request1.user = self.user
        search(request1)

        request2 = self.factory.get(reverse("search") + "?query=test2&type=all")
        request2.user = self.user
        search(request2)

        # Should have two entries
        search_history = SearchHistory.objects.filter(user=self.user)
        self.assertEqual(search_history.count(), 2)

    def test_search_logs_different_search_types(self):
        """Test that different search types are logged separately"""
        request1 = self.factory.get(reverse("search") + "?query=test&type=all")
        request1.user = self.user
        search(request1)

        request2 = self.factory.get(reverse("search") + "?query=test&type=issues")
        request2.user = self.user
        search(request2)

        # Should have two entries
        search_history = SearchHistory.objects.filter(user=self.user, query="test")
        self.assertEqual(search_history.count(), 2)

    def test_search_history_limit_per_user(self):
        """Test that only last 50 searches are kept per user"""
        # Create 55 searches
        for i in range(55):
            request = self.factory.get(reverse("search") + f"?query=test{i}&type=all")
            request.user = self.user
            search(request)

        # Should only have 50 entries
        search_history = SearchHistory.objects.filter(user=self.user)
        self.assertEqual(search_history.count(), 50)

    def test_recent_searches_in_context(self):
        """Test that recent_searches is included in context for authenticated users"""
        # Create some search history
        SearchHistory.objects.create(user=self.user, query="test1", search_type="all")
        SearchHistory.objects.create(user=self.user, query="test2", search_type="issues")

        request = self.factory.get(reverse("search") + "?query=new&type=all")
        request.user = self.user
        response = search(request)
        self.assertEqual(response.status_code, 200)

        # Check that recent_searches is in context
        self.assertIn("recent_searches", response.context)
        recent_searches = response.context["recent_searches"]
        self.assertGreaterEqual(len(recent_searches), 2)

    def test_search_does_not_log_for_anonymous_user(self):
        """Test that search history is not logged for anonymous users"""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get(reverse("search") + "?query=test&type=all")
        request.user = AnonymousUser()
        response = search(request)
        self.assertEqual(response.status_code, 200)

        # Should not have any search history (no user to filter by)
        search_history = SearchHistory.objects.all()
        self.assertEqual(search_history.count(), 0)
