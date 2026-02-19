"""
Tests for CVE filtering and search functionality.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from website.models import Domain, Issue

User = get_user_model()


class TestIssueViewSetCveFiltering(TestCase):
    """Test CVE filtering in IssueViewSet API."""

    def setUp(self):
        """Set up test data."""
        self.api_client = APIClient()
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.test_domain = Domain.objects.create(url="https://example.com", name="example.com")
        # Issue with CVE ID and score
        self.issue1 = Issue.objects.create(
            url="https://example.com/vuln1",
            description="Critical vulnerability",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue with different CVE ID and high score
        self.issue2 = Issue.objects.create(
            url="https://example.com/vuln2",
            description="High severity issue",
            cve_id="CVE-2024-5678",
            cve_score=Decimal("8.5"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue with low CVE score
        self.issue3 = Issue.objects.create(
            url="https://example.com/vuln3",
            description="Low severity issue",
            cve_id="CVE-2024-9999",
            cve_score=Decimal("3.2"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue without CVE
        self.issue4 = Issue.objects.create(
            url="https://example.com/normal",
            description="Normal issue",
            cve_id=None,
            cve_score=None,
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )

    def test_filter_by_cve_id_exact_match(self):
        """Test filtering issues by exact CVE ID match."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_id": "CVE-2024-1234"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["cve_id"], "CVE-2024-1234")
        self.assertEqual(response.data["results"][0]["cve_score"], "9.8")

    def test_filter_by_cve_id_case_insensitive(self):
        """Test that CVE ID filtering is case-insensitive (normalized)."""
        url = "/api/v1/issues/"
        # Test lowercase
        response = self.api_client.get(url, {"cve_id": "cve-2024-1234"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        # Test with spaces
        response = self.api_client.get(url, {"cve_id": "  CVE-2024-1234  "})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_cve_id_no_match(self):
        """Test filtering by non-existent CVE ID returns empty results."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_id": "CVE-2024-0000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_filter_by_cve_id_empty_string(self):
        """Test that empty CVE ID filter is ignored."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_id": ""})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all issues (no CVE filter applied)
        self.assertGreaterEqual(response.data["count"], 4)

    def test_filter_by_cve_score_min(self):
        """Test filtering issues by minimum CVE score."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_score_min": "7.0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        scores = [float(issue["cve_score"]) for issue in response.data["results"] if issue["cve_score"]]
        self.assertTrue(all(score >= 7.0 for score in scores))

    def test_filter_by_cve_score_max(self):
        """Test filtering issues by maximum CVE score."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_score_max": "5.0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Explicitly assert that results are non-empty
        self.assertGreater(
            len(response.data["results"]), 0, "Response should contain results when filtering by max CVE score"
        )
        # Should include issue with score 3.2 and issues without CVE
        scores = [float(issue["cve_score"]) for issue in response.data["results"] if issue["cve_score"] is not None]
        # Assert that all non-null scores are <= 5.0
        self.assertTrue(
            all(score <= 5.0 for score in scores), "All CVE scores should be <= 5.0 when filtering by max score"
        )

    def test_filter_by_cve_score_range(self):
        """Test filtering issues by CVE score range."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_score_min": "5.0", "cve_score_max": "9.0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        scores = [float(issue["cve_score"]) for issue in response.data["results"] if issue["cve_score"]]
        self.assertTrue(all(5.0 <= score <= 9.0 for score in scores))
        self.assertEqual(len(scores), 1)  # Only CVE-2024-5678 with score 8.5

    def test_filter_by_cve_score_invalid_min(self):
        """Test that invalid minimum score is ignored."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_score_min": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all issues (invalid filter ignored)
        self.assertGreaterEqual(response.data["count"], 4)

    def test_filter_by_cve_score_invalid_max(self):
        """Test that invalid maximum score is ignored."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_score_max": "not_a_number"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all issues (invalid filter ignored)
        self.assertGreaterEqual(response.data["count"], 4)

    def test_filter_by_cve_score_invalid_range(self):
        """Test that invalid range (min > max) ignores both filters."""
        url = "/api/v1/issues/"
        # min=9.0, max=5.0 is invalid - both filters should be ignored
        response = self.api_client.get(url, {"cve_score_min": "9.0", "cve_score_max": "5.0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all issues (both filters ignored due to invalid range)
        self.assertGreaterEqual(response.data["count"], 4)
        # Explicitly assert that results are non-empty
        self.assertGreater(
            len(response.data["results"]), 0, "Response should contain results when invalid range is ignored"
        )
        # Verify that issues with scores outside the invalid range are still returned
        scores = [float(issue["cve_score"]) for issue in response.data["results"] if issue["cve_score"]]
        # Should include issues with scores > 5.0 (like 9.8) since filters were ignored
        self.assertGreater(len(scores), 0, "Should have at least one issue with CVE score")
        self.assertTrue(
            any(score > 5.0 for score in scores),
            "Should include issues with scores > 5.0 when invalid range is ignored",
        )

    def test_filter_combines_with_status(self):
        """Test that CVE filtering combines with other filters."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_id": "CVE-2024-1234", "status": "open"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify that filters combine correctly
        self.assertGreater(response.data["count"], 0)
        for item in response.data["results"]:
            self.assertEqual(item["cve_id"], "CVE-2024-1234")
            self.assertEqual(item["status"], "open")

    def test_filter_combines_with_domain(self):
        """Test that CVE filtering combines with domain filter."""
        url = "/api/v1/issues/"
        response = self.api_client.get(url, {"cve_id": "CVE-2024-1234", "domain": self.test_domain.url})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)


class TestWebSearchCve(TestCase):
    """Test CVE search in web search_issues view."""

    def setUp(self):
        """Set up test data."""
        self.web_client = Client()
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.test_domain = Domain.objects.create(url="https://example.com", name="example.com")
        # Issue with CVE ID and score
        self.issue1 = Issue.objects.create(
            url="https://example.com/vuln1",
            description="Critical vulnerability",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue with different CVE ID and high score
        self.issue2 = Issue.objects.create(
            url="https://example.com/vuln2",
            description="High severity issue",
            cve_id="CVE-2024-5678",
            cve_score=Decimal("8.5"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue with low CVE score
        self.issue3 = Issue.objects.create(
            url="https://example.com/vuln3",
            description="Low severity issue",
            cve_id="CVE-2024-9999",
            cve_score=Decimal("3.2"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Issue without CVE
        self.issue4 = Issue.objects.create(
            url="https://example.com/normal",
            description="Normal issue",
            cve_id=None,
            cve_score=None,
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )

    def test_search_by_cve_prefix(self):
        """Test searching issues using cve: prefix."""
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:CVE-2024-1234"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 1)
        self.assertEqual(data["issues"][0]["fields"]["cve_id"], "CVE-2024-1234")

    def test_search_by_cve_case_insensitive(self):
        """Test that CVE search is case-insensitive (normalized)."""
        url = reverse("search_issues")
        # Test lowercase
        response = self.web_client.get(url, {"query": "cve:cve-2024-1234"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 1)
        # Test with spaces
        response = self.web_client.get(url, {"query": "cve:  CVE-2024-1234  "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 1)

    def test_search_by_cve_no_match(self):
        """Test searching for non-existent CVE returns empty results."""
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:CVE-2024-0000"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 0)

    def test_search_by_cve_empty_query(self):
        """Test that empty CVE query returns no results."""
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 0)

    def test_search_by_cve_whitespace_only(self):
        """Test that whitespace-only CVE query returns no results."""
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:   "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 0)

    def test_search_by_cve_respects_hidden_issues(self):
        """Test that CVE search respects hidden issue visibility rules."""
        # Create a hidden issue with CVE
        hidden_issue = Issue.objects.create(
            url="https://example.com/hidden",
            description="Hidden vulnerability",
            cve_id="CVE-2024-9999",
            cve_score=Decimal("7.0"),
            domain=self.issue1.domain,
            user=self.test_user,
            is_hidden=True,
        )
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:CVE-2024-9999"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        issue_ids = [str(issue["pk"]) for issue in data["issues"]]
        # Hidden issue should not appear in results
        self.assertNotIn(str(hidden_issue.id), issue_ids)
        # But the visible issue with this CVE from setUp should still be present
        visible_ids = {str(issue.id) for issue in [self.issue3] if issue.cve_id == "CVE-2024-9999"}
        self.assertTrue(visible_ids & set(issue_ids), "Visible issues with this CVE should still be returned")

    def test_search_by_cve_orders_by_created_desc(self):
        """Test that CVE search results are ordered by creation date descending."""
        # Create another issue with same CVE ID but newer
        newer_issue = Issue.objects.create(
            url="https://example.com/newer",
            description="Newer issue",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        url = reverse("search_issues")
        response = self.web_client.get(url, {"query": "cve:CVE-2024-1234"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["issues"]), 2)
        # Newer issue should appear first (ordered by -created)
        # JSON serialization returns pk as integer
        self.assertEqual(int(data["issues"][0]["pk"]), newer_issue.id)


class TestCveAutocomplete(TestCase):
    """Test CVE autocomplete endpoint functionality."""

    def setUp(self):
        """Set up test data."""
        self.web_client = Client()
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.test_domain = Domain.objects.create(url="https://example.com", name="example.com")
        # Create issues with different CVE IDs for testing
        self.issue1 = Issue.objects.create(
            url="https://example.com/vuln1",
            description="Issue 1",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        self.issue2 = Issue.objects.create(
            url="https://example.com/vuln2",
            description="Issue 2",
            cve_id="CVE-2024-5678",
            cve_score=Decimal("8.5"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        self.issue3 = Issue.objects.create(
            url="https://example.com/vuln3",
            description="Issue 3",
            cve_id="CVE-2024-9999",
            cve_score=Decimal("3.2"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        self.issue4 = Issue.objects.create(
            url="https://example.com/vuln4",
            description="Issue 4",
            cve_id="CVE-2023-1111",
            cve_score=Decimal("7.0"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )

    def test_autocomplete_partial_query_cve_prefix(self):
        """Test autocomplete with partial query 'CVE-'."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should return all CVE IDs starting with "CVE-"
        cve_ids = [item["id"] for item in data["results"]]
        self.assertGreaterEqual(len(cve_ids), 4)
        self.assertIn("CVE-2024-1234", cve_ids)
        self.assertIn("CVE-2024-5678", cve_ids)
        self.assertIn("CVE-2024-9999", cve_ids)
        self.assertIn("CVE-2023-1111", cve_ids)

    def test_autocomplete_partial_query_year(self):
        """Test autocomplete with partial query 'CVE-2024-'."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        cve_ids = [item["id"] for item in data["results"]]
        # Should return only 2024 CVE IDs
        self.assertGreaterEqual(len(cve_ids), 3)
        self.assertIn("CVE-2024-1234", cve_ids)
        self.assertIn("CVE-2024-5678", cve_ids)
        self.assertIn("CVE-2024-9999", cve_ids)
        self.assertNotIn("CVE-2023-1111", cve_ids)

    def test_autocomplete_partial_query_specific_cve(self):
        """Test autocomplete with partial query matching specific CVE."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-12"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        cve_ids = [item["id"] for item in data["results"]]
        self.assertIn("CVE-2024-1234", cve_ids)

    def test_autocomplete_query_too_short(self):
        """Test that queries shorter than 3 characters return empty results."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CV"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])

    def test_autocomplete_query_not_cve_prefix(self):
        """Test that queries not starting with 'CVE-' return empty results."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "INVALID"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])

    def test_autocomplete_excludes_hunt_issues(self):
        """Test that hunt issues are excluded from autocomplete results."""
        from website.models import Hunt

        # Create a hunt (Hunt model requires domain, name, url, and plan)
        hunt = Hunt.objects.create(
            name="Test Hunt",
            domain=self.test_domain,
            url="https://example.com/hunt",
            plan="basic",
        )
        # Create an issue with CVE ID that belongs to a hunt
        hunt_issue = Issue.objects.create(
            url="https://example.com/hunt-vuln",
            description="Hunt issue",
            cve_id="CVE-2024-1001",
            cve_score=Decimal("9.0"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
            hunt=hunt,
        )
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # Hunt issue CVE should not appear in results
        self.assertNotIn("CVE-2024-1001", cve_ids)

    def test_autocomplete_excludes_hidden_issues_for_anonymous(self):
        """Test that anonymous users cannot see hidden issues in autocomplete."""
        # Create a hidden issue with CVE
        hidden_issue = Issue.objects.create(
            url="https://example.com/hidden",
            description="Hidden issue",
            cve_id="CVE-2024-1002",
            cve_score=Decimal("8.0"),
            domain=self.test_domain,
            user=self.other_user,
            is_hidden=True,
        )
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # Hidden issue CVE should not appear for anonymous users
        self.assertNotIn("CVE-2024-1002", cve_ids)

    def test_autocomplete_authenticated_user_sees_own_hidden_issues(self):
        """Test that authenticated users can see their own hidden issues in autocomplete."""
        # Create a hidden issue owned by test_user
        hidden_issue = Issue.objects.create(
            url="https://example.com/my-hidden",
            description="My hidden issue",
            cve_id="CVE-2024-1003",
            cve_score=Decimal("7.5"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=True,
        )
        # Login as test_user
        self.web_client.force_login(self.test_user)
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # User should see their own hidden issue
        self.assertIn("CVE-2024-1003", cve_ids)

    def test_autocomplete_authenticated_user_excludes_others_hidden_issues(self):
        """Test that authenticated users cannot see other users' hidden issues."""
        # Create a hidden issue owned by other_user
        hidden_issue = Issue.objects.create(
            url="https://example.com/other-hidden",
            description="Other user's hidden issue",
            cve_id="CVE-2024-1004",
            cve_score=Decimal("6.5"),
            domain=self.test_domain,
            user=self.other_user,
            is_hidden=True,
        )
        # Login as test_user
        self.web_client.force_login(self.test_user)
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # User should not see other user's hidden issue
        self.assertNotIn("CVE-2024-1004", cve_ids)

    def test_autocomplete_orders_by_latest_created(self):
        """Test that autocomplete results are ordered by most recent usage (latest_created)."""
        # Create multiple issues with the same CVE ID at different times
        # First issue with CVE-2024-1234 (older)
        older_issue = Issue.objects.create(
            url="https://example.com/older",
            description="Older issue",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Update created timestamp to be older (if possible)
        # Note: We'll create a newer issue with same CVE to test ordering

        # Create a newer issue with same CVE ID
        newer_issue = Issue.objects.create(
            url="https://example.com/newer",
            description="Newer issue",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        # Create another CVE ID that was used more recently
        recent_issue = Issue.objects.create(
            url="https://example.com/recent",
            description="Recent issue",
            cve_id="CVE-2024-1005",
            cve_score=Decimal("8.0"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # Explicitly assert that results are non-empty
        self.assertGreater(len(cve_ids), 0, "Autocomplete should return results for CVE-2024- prefix")
        # CVE-2024-1005 should appear first (most recent)
        # CVE-2024-1234 should appear after (has older issue)
        self.assertIn("CVE-2024-1005", cve_ids)
        self.assertIn("CVE-2024-1234", cve_ids)
        # Most recent CVE should be first
        self.assertEqual(cve_ids[0], "CVE-2024-1005", "Most recently used CVE should appear first")

    def test_autocomplete_deduplicates_cve_ids(self):
        """Test that autocomplete returns distinct CVE IDs (no duplicates)."""
        # Create multiple issues with the same CVE ID
        Issue.objects.create(
            url="https://example.com/dup1",
            description="Duplicate 1",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        Issue.objects.create(
            url="https://example.com/dup2",
            description="Duplicate 2",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        Issue.objects.create(
            url="https://example.com/dup3",
            description="Duplicate 3",
            cve_id="CVE-2024-1234",
            cve_score=Decimal("9.8"),
            domain=self.test_domain,
            user=self.test_user,
            is_hidden=False,
        )
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-1234"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # Should only return one instance of CVE-2024-1234
        self.assertEqual(cve_ids.count("CVE-2024-1234"), 1)

    def test_autocomplete_returns_max_10_results(self):
        """Test that autocomplete returns at most 10 distinct CVE IDs."""
        # Create 15 issues with different CVE IDs
        for i in range(15):
            Issue.objects.create(
                url=f"https://example.com/vuln{i}",
                description=f"Issue {i}",
                cve_id=f"CVE-2024-{i:04d}",
                cve_score=Decimal("7.0"),
                domain=self.test_domain,
                user=self.test_user,
                is_hidden=False,
            )
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids = [item["id"] for item in data["results"]]
        # Should return at most 10 results
        self.assertLessEqual(len(cve_ids), 10)
        # All results should be distinct
        self.assertEqual(len(cve_ids), len(set(cve_ids)))

    def test_autocomplete_case_insensitive(self):
        """Test that autocomplete is case-insensitive."""
        url = reverse("cve_autocomplete")
        # Test lowercase query
        response = self.web_client.get(url, {"q": "cve-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids_lower = [item["id"] for item in data["results"]]
        # Test uppercase query
        response = self.web_client.get(url, {"q": "CVE-2024-"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cve_ids_upper = [item["id"] for item in data["results"]]
        # Results should be the same
        self.assertEqual(set(cve_ids_lower), set(cve_ids_upper))

    def test_autocomplete_empty_query(self):
        """Test that empty query returns empty results."""
        url = reverse("cve_autocomplete")
        response = self.web_client.get(url, {"q": ""})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])

    def test_autocomplete_whitespace_handling(self):
        """Test that whitespace in query is handled correctly."""
        url = reverse("cve_autocomplete")
        # Query with leading/trailing whitespace
        response = self.web_client.get(url, {"q": "  CVE-2024-  "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should still return results (whitespace is stripped)
        self.assertIn("results", data)
