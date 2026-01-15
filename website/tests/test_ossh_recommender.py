import json

from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.utils import timezone

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Tag
from website.views.ossh import (
    article_recommender,
    community_recommender,
    discussion_channel_recommender,
    get_github_data,
    is_valid_github_username,
    repo_recommender,
)


class OSSHRecommenderTests(TestCase):
    """Minimal tests covering all recommenders, rate limiter, and GitHub username validation."""

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
        )
        self.community.tags.add(self.tag_python)

        # Create article with all required fields
        self.article = OsshArticle.objects.create(
            title="Test Article",
            author="Test Author",  # ✅ Required field
            description="Test article description",  # ✅ Required field
            publication_date=timezone.now(),  # ✅ Required field (the missing one!)
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
    """Test rate limiter decorator"""

    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_rate_limit_allows_under_limit(self):
        """Test rate limiter allows requests under the limit"""
        request = self.factory.post(
            "/api/ossh/github/",
            data=json.dumps({"github_username": "validuser123"}),
            content_type="application/json",
        )
        request.META["REMOTE_ADDR"] = "1.2.3.4"

        # Make 5 requests (under default limit of 10)
        for i in range(5):
            response = get_github_data(request)
            # Should not be 429
            self.assertNotEqual(response.status_code, 429)

    def test_rate_limit_blocks_over_limit(self):
        """Test rate limiter blocks requests over the limit"""
        request = self.factory.post(
            "/api/ossh/github/", data=json.dumps({"github_username": "test"}), content_type="application/json"
        )
        request.META["REMOTE_ADDR"] = "5.6.7.8"

        # Make 15 requests; limit is 10, so requests 11+ should be rate limited
        got_429 = False
        for i in range(15):
            response = get_github_data(request)
            if response.status_code == 429:
                got_429 = True
                break

        self.assertTrue(got_429, "Expected at least one 429 response after exceeding rate limit")

    def test_rate_limit_respects_method(self):
        """Test rate limiter only applies to specified methods"""
        get_request = self.factory.get("/api/ossh/github/")
        get_request.META["REMOTE_ADDR"] = "9.10.11.12"

        # GET requests should not be rate limited (decorator specifies POST only)
        response = get_github_data(get_request)
        self.assertEqual(response.status_code, 405)  # Method not allowed, but not rate limited
