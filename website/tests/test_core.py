import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from website.models import Domain, GitHubIssue, Repo, UserProfile


class TopEarnersTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test users
        self.user1 = User.objects.create_user(username="earner1", password="testpass")
        self.user2 = User.objects.create_user(username="earner2", password="testpass")
        self.user3 = User.objects.create_user(username="earner3", password="testpass")

        # Create user profiles
        self.profile1 = UserProfile.objects.get(user=self.user1)
        self.profile2 = UserProfile.objects.get(user=self.user2)
        self.profile3 = UserProfile.objects.get(user=self.user3)

        # Create a test repository
        self.repo = Repo.objects.create(name="TestRepo", repo_url="https://github.com/test/repo")

    def _get_top_earners_queryset(self):
        """Helper method that executes the same query as in the home view"""
        from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
        from django.db.models.functions import Coalesce

        return (
            UserProfile.objects.annotate(
                github_earnings=Coalesce(
                    Sum("github_issues__p2p_amount_usd", filter=Q(github_issues__p2p_amount_usd__isnull=False)),
                    Value(0),
                    output_field=DecimalField(),
                ),
                has_github_issues=Count("github_issues", filter=Q(github_issues__p2p_amount_usd__isnull=False)),
                total_earnings=Case(
                    # If user has GitHub issues with payments, use those
                    When(has_github_issues__gt=0, then=F("github_earnings")),
                    # Otherwise fall back to the existing winnings field
                    default=Coalesce(F("winnings"), Value(0), output_field=DecimalField()),
                    output_field=DecimalField(),
                ),
            )
            .filter(total_earnings__gt=0)
            .select_related("user")
            .order_by("-total_earnings")[:5]
        )

    def test_top_earners_queryset_from_github_issues(self):
        """Test that top earners queryset calculation uses GitHub issue payments when available"""
        # Create GitHub issues with payments for user1
        GitHubIssue.objects.create(
            issue_id=1,
            title="Issue 1",
            state="closed",
            url="https://github.com/test/repo/issues/1",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("50.00"),
        )
        GitHubIssue.objects.create(
            issue_id=2,
            title="Issue 2",
            state="closed",
            url="https://github.com/test/repo/issues/2",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("30.00"),
        )

        # Set winnings for user2 (fallback case)
        self.profile2.winnings = Decimal("60.00")
        self.profile2.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # Verify user1's total is calculated from GitHub issues (50 + 30 = 80)
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("80.00"))

        # Verify user2's total comes from winnings field
        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("60.00"))

        # Verify correct ordering (user1 with 80 should be before user2 with 60)
        self.assertEqual(top_earners_list[0].user, self.user1)
        self.assertEqual(top_earners_list[1].user, self.user2)

    def test_top_earners_queryset_fallback_to_winnings(self):
        """Test that winnings field is used when no GitHub issues with payments exist"""
        # Set winnings for user profiles without GitHub issues
        self.profile1.winnings = Decimal("100.00")
        self.profile1.save()

        self.profile2.winnings = Decimal("50.00")
        self.profile2.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # All earnings should come from winnings field
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("100.00"))

        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("50.00"))

    def test_top_earners_queryset_mixed_sources(self):
        """Test that the calculation works correctly with mixed payment sources"""
        # User1: Has GitHub issues with payments
        GitHubIssue.objects.create(
            issue_id=10,
            title="Paid Issue",
            state="closed",
            url="https://github.com/test/repo/issues/10",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("75.00"),
        )
        # Set winnings for user1 - should be ignored since GitHub issues exist
        self.profile1.winnings = Decimal("10.00")
        self.profile1.save()

        # User2: Only has winnings, no GitHub issues
        self.profile2.winnings = Decimal("50.00")
        self.profile2.save()

        # User3: Has GitHub issues but no payments (p2p_amount_usd is None)
        GitHubIssue.objects.create(
            issue_id=20,
            title="Unpaid Issue",
            state="open",
            url="https://github.com/test/repo/issues/20",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile3,
            p2p_amount_usd=None,
        )
        self.profile3.winnings = Decimal("40.00")
        self.profile3.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # User1 should use GitHub issue payment (75.00), not winnings (10.00)
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("75.00"))

        # User2 should use winnings
        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("50.00"))

        # User3 should use winnings since GitHub issue has no payment
        user3_earner = next((e for e in top_earners_list if e.user == self.user3), None)
        self.assertIsNotNone(user3_earner)
        self.assertEqual(user3_earner.total_earnings, Decimal("40.00"))


class DarkModeTests(TestCase):
    """Test suite for dark mode functionality"""

    def setUp(self):
        self.client = Client()

    def test_set_theme_endpoint_accepts_dark(self):
        """Test that the set-theme endpoint accepts and saves dark theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "dark"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "dark")

    def test_set_theme_endpoint_accepts_light(self):
        """Test that the set-theme endpoint accepts and saves light theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "light"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "light")

    def test_set_theme_invalid_method(self):
        """Test that GET request to set-theme endpoint returns 405"""
        response = self.client.get(reverse("set_theme"))
        self.assertEqual(response.status_code, 405)

    def test_dark_mode_toggle_in_base_template(self):
        """Test that dark mode toggle is present in base template"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode JS and CSS references (may be hashed in production)
        self.assertTrue(
            "darkMode" in response.content.decode() or "dark-mode" in response.content.decode(),
            "Dark mode script reference not found in response",
        )
        self.assertContains(response, "custom-scrollbar")

    def test_dark_mode_script_loads(self):
        """Test that dark mode JS script is included in pages"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode related content (script tag with darkMode reference)
        content = response.content.decode()
        self.assertTrue("darkMode.js" in content or "darkMode" in content, "Dark mode script not found in response")


class StatusPageTests(TestCase):
    """Test suite for status page functionality"""

    def setUp(self):
        self.client = Client()

    def test_status_page_loads(self):
        """Test that the status page loads without errors"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.context)

    def test_status_page_has_required_context(self):
        """Test that status page provides expected context data"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        status = response.context["status"]

        # Check for essential status data keys
        self.assertIn("management_commands", status)
        self.assertIn("available_commands", status)


class SitemapTests(TestCase):
    """Test suite for sitemap functionality"""

    def setUp(self):
        self.client = Client()
        # Create test user and domain for sitemap
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.domain = Domain.objects.create(name="test.example.com", url="https://test.example.com")

    def test_sitemap_loads(self):
        """Test that the sitemap page loads without errors"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)

    def test_sitemap_context_has_username(self):
        """Test that sitemap provides random_username in context"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("random_username", response.context)
        # Should be a string, not a User object
        self.assertIsInstance(response.context["random_username"], str)

    def test_sitemap_context_has_domain(self):
        """Test that sitemap provides random_domain in context"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("random_domain", response.context)
        # Should be a string, not a Domain object
        self.assertIsInstance(response.context["random_domain"], str)

    def test_sitemap_with_no_users(self):
        """Test that sitemap handles case when no users exist"""
        User.objects.all().delete()
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        # Should have fallback value
        self.assertEqual(response.context["random_username"], "user")

    def test_sitemap_with_no_domains(self):
        """Test that sitemap handles case when no domains exist"""
        Domain.objects.all().delete()
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        # Should have fallback value
        self.assertEqual(response.context["random_domain"], "example.com")

    def test_sitemap_template_renders_urls(self):
        """Test that sitemap template contains profile and domain URLs"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check that profile URL is present
        self.assertIn("profile", content)
        # Check that domain URL is present
        self.assertIn("domain", content)
        # Check that follow_user URL is present
        self.assertIn("follow", content)


_SIMPLE_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_SIMPLE_STORAGES)
class HomeCachingTests(TestCase):
    """Tests for homepage full-page caching behaviour."""

    def setUp(self):
        from django.core.cache import cache

        self.client = Client()
        cache.clear()

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_anonymous_response_is_cached_by_session(self):
        """First anonymous request populates the per-session cache entry."""
        from django.core.cache import cache

        self.client.get(reverse("home"))

        session_key = self.client.session.session_key
        cache_key = f"home_page_session_{session_key}"
        self.assertIsNotNone(cache.get(cache_key), "Home page should be cached after first request")

    def test_different_sessions_have_separate_cache_entries(self):
        """Two anonymous clients (different sessions) must not share a cache entry."""
        from django.core.cache import cache

        client_a = Client()
        client_b = Client()

        client_a.get(reverse("home"))
        client_b.get(reverse("home"))

        key_a = f"home_page_session_{client_a.session.session_key}"
        key_b = f"home_page_session_{client_b.session.session_key}"

        self.assertNotEqual(key_a, key_b, "Different sessions must produce different cache keys")
        self.assertIsNotNone(cache.get(key_a))
        self.assertIsNotNone(cache.get(key_b))

    def test_cache_bypassed_when_messages_present(self):
        """Response with pending flash messages must not be served from or written to cache."""
        from unittest.mock import MagicMock, patch

        from django.core.cache import cache

        user = User.objects.create_user(username="msguser", password="testpass")
        self.client.login(username="msguser", password="testpass")

        # Prime the session and manually populate cache with stale sentinel content.
        self.client.get(reverse("home"))
        session_key = self.client.session.session_key
        cache_key = f"home_page_session_{session_key}"
        cache.set(cache_key, "<html>stale</html>", timeout=300)

        # Simulate one pending flash message.
        mock_storage = MagicMock()
        mock_storage.__len__ = MagicMock(return_value=1)

        with patch("website.views.core.get_messages", return_value=mock_storage):
            response = self.client.get(reverse("home"))

        # Should return a fresh response, not the stale cached content.
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"stale", response.content)
        # And the stale cache entry must not have been overwritten with message-bearing content.
        self.assertEqual(cache.get(cache_key), "<html>stale</html>")

    def test_authenticated_user_cache_key_uses_session(self):
        """Authenticated user cache key must be session-based, not user-id-based."""
        from django.core.cache import cache

        user = User.objects.create_user(username="cacheuser", password="testpass")
        self.client.login(username="cacheuser", password="testpass")

        self.client.get(reverse("home"))
        session_key = self.client.session.session_key
        cache_key = f"home_page_session_{session_key}"

        self.assertIsNone(
            cache.get(f"home_page_user_{user.id}"),
            "Cache must NOT use user-id as key",
        )
        self.assertIsNotNone(cache.get(cache_key), "Cache must use session key")
