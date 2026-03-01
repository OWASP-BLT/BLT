import json
from unittest.mock import patch

from django.core.cache import cache
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Tag
from website.views.ossh import rate_limit  # Import the decorator itself
from website.views.ossh import (
    article_recommender,
    community_recommender,
    discussion_channel_recommender,
    is_valid_github_username,
    repo_recommender,
)


class OSSHRecommenderTests(TestCase):
    """Minimal tests covering all recommenders."""

    def setUp(self):
        """Set up test data for all recommenders"""
        # Create tags
        self.tag_python = Tag.objects.create(name="python")
        self.tag_security = Tag.objects.create(name="security")
        self.tag_api = Tag.objects.create(name="api")

        # Create discussion channel
        self.channel = OsshDiscussionChannel.objects.create(
            name="Test Channel",
            source="Discord",
            external_id="ch_123",
        )
        self.channel.tags.add(self.tag_python, self.tag_security)

        # Create community with metadata
        self.community = OsshCommunity.objects.create(
            name="Test Community",
            source="GitHub",
            external_id="com_456",
            metadata={"primary_language": "Python"},
            website="https://example.com/communities/test-community",
        )
        self.community.tags.add(self.tag_python)

        # Create article with all required fields
        self.article = OsshArticle.objects.create(
            title="Test Article",
            author="Test Author",
            description="Test article description",
            publication_date=timezone.now(),
            url="https://example.com/article",
            source="Medium",
            external_id="art_789",
        )
        self.article.tags.add(self.tag_api)

    def test_discussion_channel_recommender_weighted_scoring(self):
        """Test discussion channel recommender uses weighted tag scoring"""
        user_tags = [("python", 10), ("security", 5)]
        recommended = discussion_channel_recommender(user_tags, {}, top_n=5)

        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["channel"].id, self.channel.id)
        self.assertEqual(recommended[0]["relevance_score"], 15)  # 10 + 5
        self.assertIn("Matching tags:", recommended[0]["reasoning"])

    def test_community_recommender_with_language(self):
        """Test community recommender uses tags and language metadata"""
        user_tags = [("python", 8)]
        language_weights = {"Python": 12}
        recommended = community_recommender(user_tags, language_weights)

        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["community"].id, self.community.id)
        self.assertEqual(recommended[0]["relevance_score"], 20)  # 8 + 12

    def test_article_recommender_tag_only(self):
        """Test article recommender (no metadata field)"""
        user_tags = [("api", 7)]
        recommended = article_recommender(user_tags, {}, top_n=5)

        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["article"].id, self.article.id)
        self.assertEqual(recommended[0]["relevance_score"], 7)

    def test_repo_recommender_basic(self):
        """Test repo recommender returns list"""
        user_tags = [("python", 10)]
        language_weights = {"Python": 5}
        recommended = repo_recommender(user_tags, language_weights)

        # Just verify it returns a list (repo data is external)
        self.assertIsInstance(recommended, list)

    def test_no_matches_returns_empty(self):
        """Test recommenders return empty list when no tags match"""
        user_tags = [("rust", 10)]
        language_weights = {}

        channels = discussion_channel_recommender(user_tags, language_weights)
        communities = community_recommender(user_tags, language_weights)
        articles = article_recommender(user_tags, language_weights)

        self.assertEqual(len(channels), 0)
        self.assertEqual(len(communities), 0)
        self.assertEqual(len(articles), 0)

    def test_top_n_limits_results(self):
        """Test top_n parameter limits results"""
        # Create multiple channels
        for i in range(5):
            ch = OsshDiscussionChannel.objects.create(
                name=f"Channel {i}",
                source="Discord",
                external_id=f"ch_{i}",
            )
            ch.tags.add(self.tag_python)

        user_tags = [("python", 10)]
        recommended = discussion_channel_recommender(user_tags, {}, top_n=2)

        self.assertEqual(len(recommended), 2)


class GitHubUsernameValidationTests(TestCase):
    """Test GitHub username validation"""

    def test_valid_usernames(self):
        """Test valid GitHub usernames"""
        valid = ["user", "user123", "user-name", "a", "a1b2c3d4"]
        for username in valid:
            with self.subTest(username=username):
                self.assertTrue(is_valid_github_username(username))

    def test_invalid_usernames(self):
        """Test invalid GitHub usernames"""
        invalid = [
            "",  # Empty
            "a" * 40,  # Too long (max 39)
            "-user",  # Starts with hyphen
            "user-",  # Ends with hyphen
            "user@name",  # Invalid character
            "user.name",  # Invalid character
            "user name",  # Space
        ]
        for username in invalid:
            with self.subTest(username=username):
                self.assertFalse(is_valid_github_username(username))


class RateLimiterTests(TestCase):
    """Test rate limiter decorator without external network calls"""

    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_rate_limit_allows_under_limit(self):
        """Test rate limiter allows requests under the limit"""

        # Create a minimal stub view for testing the decorator
        @rate_limit(max_requests=5, window_sec=60, methods=("POST",))
        def dummy_view(request):
            return JsonResponse({"status": "ok"})

        # Create POST request
        request = self.factory.post("/test/", data=json.dumps({}), content_type="application/json")
        request.META["REMOTE_ADDR"] = "1.2.3.4"

        # Make 5 requests (at the limit)
        for i in range(5):
            response = dummy_view(request)
            self.assertEqual(response.status_code, 200)
            self.assertIn("X-RateLimit-Limit", response)
            self.assertEqual(response["X-RateLimit-Limit"], "5")

    def test_rate_limit_blocks_over_limit(self):
        """Test rate limiter blocks requests over the limit"""

        # Create a minimal stub view
        @rate_limit(max_requests=3, window_sec=60, methods=("POST",))
        def dummy_view(request):
            return JsonResponse({"status": "ok"})

        request = self.factory.post("/test/", data=json.dumps({}), content_type="application/json")
        request.META["REMOTE_ADDR"] = "5.6.7.8"

        # Make requests up to the limit
        for i in range(3):
            response = dummy_view(request)
            self.assertEqual(response.status_code, 200)

        # Next request should be rate limited
        response = dummy_view(request)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["X-RateLimit-Limit"], "3")
        self.assertEqual(response["X-RateLimit-Remaining"], "0")
        self.assertIn("Retry-After", response)

    def test_rate_limit_respects_method(self):
        """Test rate limiter only applies to specified methods"""

        @rate_limit(max_requests=3, window_sec=60, methods=("POST",))
        def dummy_view(request):
            return JsonResponse({"status": "ok"})

        # GET requests should not be rate limited
        get_request = self.factory.get("/test/")
        get_request.META["REMOTE_ADDR"] = "9.10.11.12"

        # Make many GET requests - none should be rate limited
        for i in range(10):
            response = dummy_view(get_request)
            self.assertEqual(response.status_code, 200)

    def test_rate_limit_per_ip_isolation(self):
        """Test rate limiter tracks different IPs independently"""

        @rate_limit(max_requests=2, window_sec=60, methods=("POST",))
        def dummy_view(request):
            return JsonResponse({"status": "ok"})

        # IP 1: Use up the limit
        request1 = self.factory.post("/test/", data=json.dumps({}), content_type="application/json")
        request1.META["REMOTE_ADDR"] = "10.0.0.1"

        for i in range(2):
            response = dummy_view(request1)
            self.assertEqual(response.status_code, 200)

        # IP 1 should now be blocked
        response = dummy_view(request1)
        self.assertEqual(response.status_code, 429)

        # IP 2 should still be allowed
        request2 = self.factory.post("/test/", data=json.dumps({}), content_type="application/json")
        request2.META["REMOTE_ADDR"] = "10.0.0.2"

        response = dummy_view(request2)
        self.assertEqual(response.status_code, 200)

    def test_rate_limit_fallback_handles_non_dict_cache_values(self):
        """Test rate limiter fallback correctly handles integer cache values"""

        @rate_limit(max_requests=5, window_sec=60, methods=("POST",))
        def dummy_view(request):
            return JsonResponse({"status": "ok"})

        request = self.factory.post("/test/", data=json.dumps({}), content_type="application/json")
        request.META["REMOTE_ADDR"] = "11.12.13.14"

        # Manually set an integer value in cache (simulating happy path)
        from website.utils import get_client_ip

        key = f"rl:{get_client_ip(request)}:{request.path}"
        cache.set(key, 2, timeout=60)  # Integer, not dict

        # Mock cache.incr to fail and trigger fallback
        with patch("django.core.cache.cache.incr", side_effect=Exception("incr failed")):
            # Should not crash, should handle integer gracefully
            response = dummy_view(request)
            self.assertEqual(response.status_code, 200)

    @patch("website.views.ossh.fetch_github_user_data")
    def test_get_github_data_with_rate_limiting_mocked(self, mock_fetch):
        """Test get_github_data endpoint with mocked GitHub API (integration test)"""
        from website.views.ossh import get_github_data

        # Mock the external API call
        mock_fetch.return_value = {
            "repositories": [],
            "top_languages": [("Python", 1000)],
            "top_topics": [],
        }

        request = self.factory.post(
            "/api/ossh/github/", data=json.dumps({"github_username": "testuser"}), content_type="application/json"
        )
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Should succeed without hitting real GitHub API
        response = get_github_data(request)
        self.assertEqual(response.status_code, 200)

        # Verify mock was called (or not, depending on cache)
        # This confirms no real network call was made
